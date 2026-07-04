"""
audio — a royalty-free music bed and an optional TTS voiceover.

The music is *generated* here from sine partials, so it is licence-clean by
construction (no download, no attribution). On a real PC you can instead drop a
Creative-Commons track into ``assets/music`` or point ``tts`` at a free engine.

Voiceover providers (used on a real PC, need internet or a local binary):
    * gtts   — Google Translate TTS via the free ``gTTS`` package
    * piper  — offline neural TTS (rhasspy/piper), great quality, no cloud
Offline in a sandbox we return silence and rely on the music bed + subtitles.
"""

from __future__ import annotations

import numpy as np

from . import config


def _adsr(n: int, sr: int, a=0.6, r=1.2) -> np.ndarray:
    env = np.ones(n, dtype=np.float32)
    na, nr = int(a * sr), int(r * sr)
    if na:
        env[:na] = np.linspace(0, 1, na)
    if nr:
        env[-nr:] = np.linspace(1, 0, nr)
    return env


def music_bed(duration: float, sr: int = config.SAMPLE_RATE, seed: int = 7) -> np.ndarray:
    """Return a gentle warm pad as float32 stereo array shape (n, 2) in [-1, 1]."""
    n = int(duration * sr)
    t = np.arange(n, dtype=np.float32) / sr

    # slow 4-chord progression (Am - F - C - G), one bar per ~quarter of the video
    chords = [
        [220.00, 261.63, 329.63],   # Am
        [174.61, 220.00, 261.63],   # F
        [261.63, 329.63, 392.00],   # C
        [196.00, 246.94, 392.00],   # G
    ]
    seg = n // len(chords)
    left = np.zeros(n, dtype=np.float32)
    right = np.zeros(n, dtype=np.float32)
    rng = np.random.default_rng(seed)

    for ci, chord in enumerate(chords):
        s = ci * seg
        e = n if ci == len(chords) - 1 else (ci + 1) * seg
        m = e - s
        tt = t[s:e] - t[s]
        env = _adsr(m, sr, a=0.5, r=0.6)
        # subtle tremolo for movement
        trem = 0.85 + 0.15 * np.sin(2 * np.pi * 0.6 * tt)
        for k, f in enumerate(chord):
            phase = rng.uniform(0, 2 * np.pi)
            # partial with a soft second harmonic
            wave = (np.sin(2 * np.pi * f * tt + phase)
                    + 0.35 * np.sin(2 * np.pi * 2 * f * tt + phase))
            pan = 0.4 + 0.2 * k                      # spread voices across stereo
            amp = 0.16 * env * trem
            left[s:e] += amp * wave * (1 - pan)
            right[s:e] += amp * wave * pan

    # soft bass pulse on the root of each chord
    for ci, chord in enumerate(chords):
        s = ci * seg
        e = n if ci == len(chords) - 1 else (ci + 1) * seg
        tt = t[s:e] - t[s]
        bass = 0.12 * np.sin(2 * np.pi * (chord[0] / 2) * tt) * _adsr(e - s, sr, 0.05, 0.4)
        left[s:e] += bass
        right[s:e] += bass

    stereo = np.stack([left, right], axis=1)
    # gentle low-pass (vectorised moving-average FIR) to take the edge off
    k = max(3, int(sr * 0.0008))            # ~0.8 ms window
    kernel = np.ones(k, dtype=np.float32) / k
    for c in range(2):
        stereo[:, c] = np.convolve(stereo[:, c], kernel, mode="same")
    # normalise + master fade
    peak = np.max(np.abs(stereo)) or 1.0
    stereo = stereo / peak * 0.5
    fade = min(int(1.0 * sr), n // 2)
    stereo[:fade] *= np.linspace(0, 1, fade)[:, None]
    stereo[-fade:] *= np.linspace(1, 0, fade)[:, None]
    return stereo.astype(np.float32)


def tts(text: str, provider: str, duration_hint: float,
        sr: int = config.SAMPLE_RATE) -> np.ndarray | None:
    """Return a mono float32 voiceover, or None if unavailable/offline."""
    if provider == "none" or not text.strip():
        return None
    try:
        if provider == "gtts":
            from gtts import gTTS            # free, needs internet
            import io, wave                  # noqa
            from pydub import AudioSegment   # to decode mp3 -> pcm
            buf = io.BytesIO()
            gTTS(text=text, lang="de").write_to_fp(buf)
            buf.seek(0)
            seg = AudioSegment.from_file(buf, format="mp3").set_frame_rate(sr).set_channels(1)
            samples = np.array(seg.get_array_of_samples(), dtype=np.float32)
            return samples / (np.max(np.abs(samples)) or 1.0) * 0.9
        if provider == "piper":
            # expects a local `piper` binary + a downloaded voice model
            import subprocess, tempfile, wave, os
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                out = f.name
            subprocess.run(["piper", "--model", "de_DE-thorsten-medium.onnx",
                            "--output_file", out], input=text.encode(), check=True)
            with wave.open(out, "rb") as wf:
                raw = wf.readframes(wf.getnframes())
            os.unlink(out)
            samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            return samples
    except Exception as e:
        print(f"  [audio] tts provider '{provider}' unavailable ({e}); music only")
    return None


def mix(music: np.ndarray, voice: np.ndarray | None) -> np.ndarray:
    """Combine a stereo music bed with an optional mono voice -> float32 (n, 2)."""
    n = music.shape[0]
    out = music.copy()
    if voice is not None:
        v = voice[:n] if len(voice) >= n else np.pad(voice, (0, n - len(voice)))
        out *= 0.55                      # duck the music under the voice
        out[:, 0] += v * 0.9
        out[:, 1] += v * 0.9
    return np.clip(out, -1.0, 1.0).astype(np.float32)
