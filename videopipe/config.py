"""Central configuration and small shared helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# --- Output / render defaults -------------------------------------------------

WIDTH = 1280
HEIGHT = 720
FPS = 24

# Crossfade length between scenes, in seconds.
TRANSITION = 0.6

# Audio
SAMPLE_RATE = 44100

# Fonts that ship with the Debian/Ubuntu base image (no download needed).
_FONT_CANDIDATES_TITLE = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf",
]
_FONT_CANDIDATES_BODY = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
]


def _first_existing(paths: list[str]) -> str | None:
    for p in paths:
        if os.path.exists(p):
            return p
    return None


FONT_TITLE = _first_existing(_FONT_CANDIDATES_TITLE)
FONT_BODY = _first_existing(_FONT_CANDIDATES_BODY)


@dataclass
class RenderConfig:
    """Everything the pipeline needs to render one job."""

    prompt: str
    outdir: Path = field(default_factory=lambda: Path("output"))

    width: int = WIDTH
    height: int = HEIGHT
    fps: int = FPS
    transition: float = TRANSITION
    sample_rate: int = SAMPLE_RATE

    # Provider selection. "local" always works offline; the others need internet
    # and are meant for running on your own machine.
    #   image_provider:  "local" | "pollinations"
    #   tts_provider:    "none"  | "gtts" | "piper"
    #   music:           True/False  (procedural royalty-free bed)
    image_provider: str = "local"
    tts_provider: str = "none"
    music: bool = True

    # Kept work dir with intermediate PNG/WAV files (useful for debugging).
    keep_intermediate: bool = False

    def slug(self) -> str:
        keep = "".join(c if c.isalnum() or c in " -" else " " for c in self.prompt)
        words = keep.lower().split()
        return "-".join(words[:6]) or "video"
