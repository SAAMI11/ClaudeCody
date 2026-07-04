"""
motion — animate a single still into a short clip (the "video" step).

A real, GPU-hungry image-to-video model (Stable Video Diffusion, AnimateDiff,
CogVideoX ...) can be dropped in here on a capable PC. Offline we use the
classic, dependable *Ken Burns* effect: a slow zoom + pan across the still,
which gives still images convincing cinematic motion with zero dependencies.
"""

from __future__ import annotations

import numpy as np
from PIL import Image


def _ease(t: float) -> float:
    # smoothstep — gentle acceleration/deceleration
    return t * t * (3 - 2 * t)


def ken_burns(img: Image.Image, n_frames: int, motion: str,
              zoom: float = 0.12, pan: float = 0.10) -> np.ndarray:
    """Return an (n_frames, h, w, 3) uint8 array animating *img*."""
    w, h = img.size
    frames = np.empty((n_frames, h, w, 3), dtype=np.uint8)

    for i in range(n_frames):
        t = _ease(i / max(1, n_frames - 1))

        if motion == "zoom_in":
            s = 1.0 + zoom * t
            fx = fy = 0.5
        elif motion == "zoom_out":
            s = 1.0 + zoom * (1 - t)
            fx = fy = 0.5
        elif motion == "pan_left":
            s = 1.0 + zoom * 0.5
            fx = 0.5 + pan * (0.5 - t)      # right -> left
            fy = 0.5
        elif motion == "pan_right":
            s = 1.0 + zoom * 0.5
            fx = 0.5 + pan * (t - 0.5)      # left -> right
            fy = 0.5
        else:
            s, fx, fy = 1.0 + zoom * 0.5, 0.5, 0.5

        cw, ch = w / s, h / s
        left = (w - cw) * fx
        top = (h - ch) * fy
        left = min(max(left, 0.0), w - cw)
        top = min(max(top, 0.0), h - ch)

        crop = img.crop((round(left), round(top),
                         round(left + cw), round(top + ch)))
        crop = crop.resize((w, h), Image.LANCZOS)
        frames[i] = np.asarray(crop, dtype=np.uint8)

    return frames
