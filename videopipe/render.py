"""
render — the orchestrator. One prompt in, one finished MP4 out.

    from videopipe.config import RenderConfig
    from videopipe.render import generate
    path = generate(RenderConfig(prompt="..."))
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from . import assemble, audio, config
from .brain import build_storyboard
from .images import make_image
from .motion import ken_burns
from .subtitles import composite, render_overlay, write_srt


def generate(cfg: config.RenderConfig) -> Path:
    t0 = time.time()
    cfg.outdir.mkdir(parents=True, exist_ok=True)

    print(f"[1/6] Storyboard aus Prompt ...")
    sb = build_storyboard(cfg.prompt)
    food = sb.meta["food"]
    n = len(sb.scenes)
    w, h, fps = cfg.width, cfg.height, cfg.fps

    # frames per scene so the crossfaded result ≈ requested length
    pad = cfg.transition * (n - 1)
    per_frames = max(2 * round(cfg.transition * fps) + 6,
                     round((sb.total_seconds + pad) / n * fps))
    frame_counts = [per_frames] * n
    fade = int(0.35 * fps)

    print(f"      Thema: {sb.subject} · Stil: {sb.style} · {n} Szenen "
          f"· ~{sb.total_seconds:.0f}s · Bild-Provider: {cfg.image_provider}")

    def make_clip(scene):
        still = make_image(scene, cfg, food)
        frames = ken_burns(still, per_frames, scene.motion)
        overlay = render_overlay(scene, w, h)
        nf = frames.shape[0]
        for k in range(nf):
            if k < fade:
                al = k / fade
            elif k >= nf - fade:
                al = max(0.0, (nf - 1 - k) / fade)
            else:
                al = 1.0
            frames[k] = composite(frames[k], overlay, min(1.0, al))
        return frames

    print(f"[2/6] Bilder + [3/6] Animation (Ken Burns) + [4/6] Untertitel ...")
    thunks = [(lambda s=s: make_clip(s)) for s in sb.scenes]

    # timings + music need the final timeline length
    td = max(1, round(cfg.transition * fps))
    timings, total_frames = assemble.compute_timings(frame_counts, td, fps)
    total_seconds = total_frames / fps

    print(f"[5/6] Audio (Musik-Bett{' + TTS' if cfg.tts_provider != 'none' else ''}) ...")
    audio_mix = None
    if cfg.music or cfg.tts_provider != "none":
        music = audio.music_bed(total_seconds, cfg.sample_rate) if cfg.music \
            else np.zeros((int(total_seconds * cfg.sample_rate), 2), np.float32)
        voice = audio.tts(sb.narration, cfg.tts_provider, total_seconds, cfg.sample_rate)
        audio_mix = audio.mix(music, voice)

    slug = cfg.slug()
    out_path = cfg.outdir / f"{slug}.mp4"
    srt_path = cfg.outdir / f"{slug}.srt"
    write_srt(sb, timings, srt_path)

    print(f"[6/6] Encode H.264/AAC -> {out_path} ...")
    assemble.encode(str(out_path), thunks, fps, cfg.transition,
                    audio=audio_mix, sample_rate=cfg.sample_rate)

    # sidecar metadata (handy for the "give me a link" step)
    meta = {
        "prompt": cfg.prompt,
        "subject": sb.subject,
        "style": sb.style,
        "duration_s": round(total_seconds, 2),
        "scenes": [{"kind": s.kind, "title": s.title, "caption": s.caption,
                    "start": round(timings[i][0], 2), "end": round(timings[i][1], 2)}
                   for i, s in enumerate(sb.scenes)],
        "video": str(out_path.resolve()),
        "subtitles": str(srt_path.resolve()),
        "render_seconds": round(time.time() - t0, 1),
        "image_provider": cfg.image_provider,
        "tts_provider": cfg.tts_provider,
    }
    (cfg.outdir / f"{slug}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))

    print(f"\n✅ Fertig in {meta['render_seconds']}s · {meta['duration_s']}s Video")
    return out_path.resolve()
