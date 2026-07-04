"""
subtitles — on-screen headline + caption overlays, and a real .srt file.

Text is rendered ONCE per scene into an RGBA overlay and alpha-composited onto
every (already motion-cropped) frame with a time-varying fade. That keeps text
crisp and static while the picture underneath moves.

On a real PC you can instead auto-generate captions from the voiceover with
openai-whisper / faster-whisper; the .srt written here is already in the
standard format such tools produce.
"""

from __future__ import annotations

import textwrap

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import config
from .brain import Scene, Storyboard


def _font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _wrap(draw, text, font, max_w):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def render_overlay(scene: Scene, w: int, h: int) -> np.ndarray:
    """Return an (h, w, 4) uint8 RGBA overlay for one scene."""
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    title_font = _font(config.FONT_TITLE, int(h * 0.10))
    body_font = _font(config.FONT_BODY, int(h * 0.042))
    accent = scene.palette[2]

    # readability scrim along the bottom (transparent at top -> dark at bottom)
    scrim_h = int(h * 0.42)
    scrim = Image.new("L", (w, scrim_h), 0)
    sd = ImageDraw.Draw(scrim)
    for y in range(scrim_h):
        sd.line([(0, y), (w, y)], fill=int(150 * (y / scrim_h) ** 1.5))
    black = Image.new("RGBA", (w, scrim_h), (0, 0, 0, 0))
    black.putalpha(scrim)
    layer.alpha_composite(black, (0, h - scrim_h))

    cx = w // 2
    caption_lines = _wrap(d, scene.caption, body_font, int(w * 0.8))

    # vertical layout: title then caption, anchored in lower third
    title_lines = _wrap(d, scene.title, title_font, int(w * 0.86))
    th = sum(title_font.getbbox(t)[3] - title_font.getbbox(t)[1] + 6 for t in title_lines)
    ch = sum(body_font.getbbox(t)[3] - body_font.getbbox(t)[1] + 8 for t in caption_lines)

    y = h - int(h * 0.30) - (th + ch) // 2
    y = max(y, int(h * 0.40))

    for line in title_lines:
        tw = d.textlength(line, font=title_font)
        x = cx - tw / 2
        for dx, dy in ((2, 3), (-2, 3)):
            d.text((x + dx, y + dy), line, font=title_font, fill=(0, 0, 0, 210))
        d.text((x, y), line, font=title_font, fill=(255, 250, 240, 255))
        y += title_font.getbbox(line)[3] - title_font.getbbox(line)[1] + 6

    # accent divider
    d.line([(cx - 40, y + 6), (cx + 40, y + 6)], fill=(*accent, 235), width=3)
    y += 20

    for line in caption_lines:
        tw = d.textlength(line, font=body_font)
        x = cx - tw / 2
        d.text((x + 1, y + 2), line, font=body_font, fill=(0, 0, 0, 200))
        d.text((x, y), line, font=body_font, fill=(235, 228, 220, 255))
        y += body_font.getbbox(line)[3] - body_font.getbbox(line)[1] + 8

    return np.asarray(layer, dtype=np.uint8)


def composite(frame: np.ndarray, overlay: np.ndarray, alpha: float) -> np.ndarray:
    """Alpha-blend an RGBA *overlay* onto an RGB *frame* with global *alpha*."""
    if alpha <= 0:
        return frame
    a = (overlay[:, :, 3:4].astype(np.float32) / 255.0) * float(alpha)
    rgb = overlay[:, :, :3].astype(np.float32)
    out = frame.astype(np.float32) * (1 - a) + rgb * a
    return np.clip(out, 0, 255).astype(np.uint8)


# --- .srt export --------------------------------------------------------------
def _ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(sb: Storyboard, timings: list[tuple[float, float]], path) -> None:
    """timings: list of (start, end) seconds per scene on the final timeline."""
    lines = []
    for i, (scene, (start, end)) in enumerate(zip(sb.scenes, timings), 1):
        text = "\n".join(textwrap.wrap(f"{scene.title} — {scene.caption}", 42))
        lines += [str(i), f"{_ts(start)} --> {_ts(end)}", text, ""]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
