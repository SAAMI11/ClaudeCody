#!/usr/bin/env python3
"""
Single-prompt AI video pipeline — CLI entry point.

    python run.py "Erstelle ein 20-sekündiges Werbevideo für eine Pizzeria im
                   modernen, cineastischen Stil."

Options:
    --out DIR            output folder (default: output/)
    --images PROVIDER    local | pollinations           (default: local)
    --tts PROVIDER       none  | gtts | piper            (default: none)
    --no-music           disable the music bed
    --seconds N          target length override

The finished MP4 path is printed at the end as a clickable file:// link.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from videopipe.config import RenderConfig
from videopipe.render import generate


def main() -> None:
    ap = argparse.ArgumentParser(description="Free single-prompt AI video pipeline")
    ap.add_argument("prompt", help="what the video should be about")
    ap.add_argument("--out", default="output", help="output directory")
    ap.add_argument("--images", default="local", choices=["local", "pollinations"])
    ap.add_argument("--tts", default="none", choices=["none", "gtts", "piper"])
    ap.add_argument("--no-music", action="store_true")
    ap.add_argument("--seconds", type=float, default=None)
    args = ap.parse_args()

    cfg = RenderConfig(
        prompt=args.prompt,
        outdir=Path(args.out),
        image_provider=args.images,
        tts_provider=args.tts,
        music=not args.no_music,
    )
    if args.seconds:
        # override the length parsed from the prompt
        import videopipe.brain as brain
        _orig = brain.build_storyboard
        brain.build_storyboard = lambda p, target_seconds=args.seconds: _orig(p, target_seconds)

    path = generate(cfg)

    print("\n" + "=" * 60)
    print("🎬  VIDEO FERTIG")
    print(f"📁  Datei : {path}")
    print(f"🔗  Link  : file://{path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
