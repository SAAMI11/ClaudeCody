"""
assemble — stitch the per-scene clips into one MP4.

Uses PyAV (bundled ffmpeg libraries) so no external ffmpeg binary is needed.
Clips are joined with streaming crossfade transitions: at most two clips are
held in memory at once, so long videos stay light on RAM. Output is H.264 video
+ AAC audio in an MP4 with ``+faststart`` — the combination every browser,
phone and desktop player handles natively.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Callable

import av
import numpy as np


def compute_timings(frame_counts: list[int], td: int, fps: int):
    """Per-scene (start, end) seconds on the crossfaded timeline.

    Captions switch cleanly at the next scene's start; the last runs to the end.
    """
    starts = []
    acc = 0
    for i, c in enumerate(frame_counts):
        starts.append(acc)
        acc += c - td            # next clip begins td frames early
    total_frames = sum(frame_counts) - td * (len(frame_counts) - 1)
    timings = []
    for i, s in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else total_frames
        timings.append((s / fps, end / fps))
    return timings, total_frames


def _crossfade(tail: np.ndarray, head: np.ndarray) -> np.ndarray:
    n = tail.shape[0]
    alpha = np.linspace(0.0, 1.0, n, dtype=np.float32)[:, None, None, None]
    out = tail.astype(np.float32) * (1 - alpha) + head.astype(np.float32) * alpha
    return np.clip(out, 0, 255).astype(np.uint8)


def _encode_audio(container, astream, pcm: np.ndarray, sr: int) -> None:
    """pcm: float32 stereo (n, 2) in [-1, 1] -> AAC packets."""
    planar = np.ascontiguousarray(pcm.T.astype(np.float32))       # (2, n)
    frame_size = astream.codec_context.frame_size or 1024
    pts = 0
    for start in range(0, planar.shape[1], frame_size):
        chunk = np.ascontiguousarray(planar[:, start:start + frame_size])
        af = av.AudioFrame.from_ndarray(chunk, format="fltp", layout="stereo")
        af.sample_rate = sr
        af.pts = pts
        af.time_base = Fraction(1, sr)
        pts += chunk.shape[1]
        for pkt in astream.encode(af):
            container.mux(pkt)
    for pkt in astream.encode():
        container.mux(pkt)


def encode(out_path: str,
           clip_thunks: list[Callable[[], np.ndarray]],
           fps: int,
           transition: float,
           audio: np.ndarray | None = None,
           sample_rate: int = 44100,
           crf: int = 20) -> None:
    td = max(1, round(transition * fps))
    container = av.open(out_path, mode="w", options={"movflags": "+faststart"})

    v = container.add_stream("libx264", rate=fps)
    # dimensions come from the first frame
    first = clip_thunks[0]()
    h, w = first.shape[1], first.shape[2]
    v.width, v.height = w, h
    v.pix_fmt = "yuv420p"
    v.codec_context.time_base = Fraction(1, fps)
    v.options = {"crf": str(crf), "preset": "medium"}

    a = None
    if audio is not None:
        a = container.add_stream("aac", rate=sample_rate)

    frame_index = 0

    def emit(frames: np.ndarray) -> None:
        nonlocal frame_index
        for f in frames:
            vf = av.VideoFrame.from_ndarray(np.ascontiguousarray(f), format="rgb24")
            vf = vf.reformat(format="yuv420p")
            vf.pts = frame_index
            vf.time_base = Fraction(1, fps)
            for pkt in v.encode(vf):
                container.mux(pkt)
            frame_index += 1

    n = len(clip_thunks)
    cur = first
    for i in range(n):
        nxt = clip_thunks[i + 1]() if i + 1 < n else None
        head = 0 if i == 0 else td          # first td frames already consumed by prev xfade
        if nxt is None:
            emit(cur[head:])
        else:
            emit(cur[head:len(cur) - td])
            blended = _crossfade(cur[len(cur) - td:], nxt[:td])
            emit(blended)
            cur = nxt

    for pkt in v.encode():                  # flush video
        container.mux(pkt)

    if a is not None:
        _encode_audio(container, a, audio, sample_rate)

    container.close()
