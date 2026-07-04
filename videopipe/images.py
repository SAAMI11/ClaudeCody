"""
images — one still image per scene.

Two providers:

* ``local``        : fully offline, procedural cinematic frames drawn with
                     Pillow + numpy (gradients, glow, vignette, film grain,
                     stylised motifs). Always available.
* ``pollinations`` : free, key-less text-to-image web service
                     (https://image.pollinations.ai). Needs open internet, so
                     it works on your own PC but not inside a locked-down
                     sandbox. Falls back to ``local`` on any failure.

Both return a Pillow ``Image`` (RGB) at the requested size.
"""

from __future__ import annotations

import math
import random
from urllib.parse import quote

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import config
from .brain import Scene


# --------------------------------------------------------------------------- #
# low-level drawing helpers
# --------------------------------------------------------------------------- #
def _vertical_gradient(w: int, h: int, top, bottom) -> Image.Image:
    top = np.array(top, dtype=np.float32)
    bottom = np.array(bottom, dtype=np.float32)
    t = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None]
    col = top[None, :] * (1 - t) + bottom[None, :] * t     # (h, 3)
    arr = np.repeat(col[:, None, :], w, axis=1)            # (h, w, 3)
    return Image.fromarray(arr.astype(np.uint8), "RGB")


def _radial_glow(w: int, h: int, cx, cy, radius, color, strength=1.0) -> np.ndarray:
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    falloff = np.clip(1.0 - d / radius, 0.0, 1.0) ** 2
    glow = falloff[..., None] * (np.array(color, np.float32)[None, None, :] * strength)
    return glow  # additive light (h, w, 3) float


def _apply_vignette(arr: np.ndarray, strength=0.55) -> np.ndarray:
    h, w = arr.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy = w / 2, h / 2
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    d /= d.max()
    mask = 1.0 - strength * (d ** 2.2)
    return arr * mask[..., None]


def _film_grain(arr: np.ndarray, amount=6.0, seed=0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    noise = rng.normal(0.0, amount, arr.shape[:2])[..., None]
    return arr + noise


def _load_font(path: str | None, size: int) -> ImageFont.FreeTypeFont:
    if path:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def _text_center(draw, cx, y, text, font, fill, shadow=(0, 0, 0)):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    x = cx - tw / 2
    for dx, dy in ((2, 3), (-2, 3), (0, 4)):
        draw.text((x + dx, y + dy), text, font=font, fill=shadow)
    draw.text((x, y), text, font=font, fill=fill)
    return bbox[3] - bbox[1]


# --------------------------------------------------------------------------- #
# stylised motifs (drawn on an RGBA overlay so glow can be added underneath)
# --------------------------------------------------------------------------- #
def _draw_pizza(base: Image.Image, cx, cy, r, accent, seed=0):
    rng = random.Random(seed)
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    # crust
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(206, 148, 74, 255))
    # cheese
    ri = int(r * 0.86)
    d.ellipse([cx - ri, cy - ri, cx + ri, cy + ri], fill=(240, 202, 120, 255))
    # sauce blush
    rs = int(r * 0.8)
    d.ellipse([cx - rs, cy - rs, cx + rs, cy + rs], fill=(214, 128, 74, 90))
    # toppings: pepperoni + basil
    for _ in range(11):
        ang = rng.uniform(0, 2 * math.pi)
        rad = rng.uniform(0, ri * 0.82)
        px, py = cx + rad * math.cos(ang), cy + rad * math.sin(ang)
        pr = rng.uniform(r * 0.06, r * 0.1)
        d.ellipse([px - pr, py - pr, px + pr, py + pr], fill=(176, 44, 34, 255))
    for _ in range(9):
        ang = rng.uniform(0, 2 * math.pi)
        rad = rng.uniform(0, ri * 0.8)
        px, py = cx + rad * math.cos(ang), cy + rad * math.sin(ang)
        pr = rng.uniform(r * 0.05, r * 0.08)
        d.ellipse([px - pr, py - pr, px + pr * 0.6, py + pr], fill=(72, 128, 52, 235))
    # slice lines
    for k in range(8):
        a = k * math.pi / 4
        d.line([cx, cy, cx + ri * math.cos(a), cy + ri * math.sin(a)],
               fill=(150, 96, 50, 120), width=2)
    layer = layer.filter(ImageFilter.GaussianBlur(0.6))
    base.alpha_composite(layer)


def _draw_oven_arch(base: Image.Image, cx, cy, r, accent):
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.pieslice([cx - r, cy - r, cx + r, cy + r], 180, 360, fill=(24, 12, 10, 255))
    d.rectangle([cx - r, cy, cx + r, cy + int(r * 0.5)], fill=(24, 12, 10, 255))
    inner = int(r * 0.66)
    d.pieslice([cx - inner, cy - inner, cx + inner, cy + inner], 180, 360,
               fill=(*accent, 255))
    d.rectangle([cx - inner, cy, cx + inner, cy + int(inner * 0.9)],
                fill=(255, 120, 40, 255))
    base.alpha_composite(layer.filter(ImageFilter.GaussianBlur(1.2)))


def _draw_bokeh(base: Image.Image, accent, seed=0, count=26):
    rng = random.Random(seed)
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    w, h = base.size
    for _ in range(count):
        x, y = rng.uniform(0, w), rng.uniform(0, h * 0.8)
        r = rng.uniform(6, 34)
        a = int(rng.uniform(20, 70))
        col = (min(255, accent[0] + 20), min(255, accent[1] + 10), accent[2], a)
        d.ellipse([x - r, y - r, x + r, y + r], fill=col)
    base.alpha_composite(layer.filter(ImageFilter.GaussianBlur(3)))


def _draw_slice(base: Image.Image, cx, cy, accent, seed=0):
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    pts = [(cx, cy - 150), (cx - 120, cy + 150), (cx + 120, cy + 150)]
    d.polygon(pts, fill=(240, 200, 120, 255))
    d.polygon([(cx, cy - 150), (cx - 120, cy + 150), (cx + 120, cy + 150)],
              outline=(206, 148, 74, 255))
    rng = random.Random(seed)
    for _ in range(7):
        px = rng.uniform(cx - 70, cx + 70)
        py = rng.uniform(cy - 60, cy + 110)
        pr = rng.uniform(9, 15)
        d.ellipse([px - pr, py - pr, px + pr, py + pr], fill=(176, 44, 34, 255))
    base.alpha_composite(layer.filter(ImageFilter.GaussianBlur(0.5)))


# --------------------------------------------------------------------------- #
# local (offline) provider
# --------------------------------------------------------------------------- #
def render_local(scene: Scene, w: int, h: int, food: bool, seed: int = 0) -> Image.Image:
    top, bottom, accent = scene.palette
    base = _vertical_gradient(w, h, top, bottom).convert("RGBA")

    # motif + key light per beat
    cx, cy = w // 2, int(h * 0.46)
    if scene.kind == "hook":
        if food:
            _draw_oven_arch(base, cx, int(h * 0.62), int(h * 0.34), accent)
        glow = _radial_glow(w, h, cx, int(h * 0.6), h * 0.7, accent, 0.9)
    elif scene.kind == "hero":
        if food:
            _draw_pizza(base, cx, cy, int(h * 0.3), accent, seed)
        glow = _radial_glow(w, h, cx, cy, h * 0.75, accent, 0.7)
    elif scene.kind == "atmosphere":
        _draw_bokeh(base, accent, seed)
        glow = _radial_glow(w, h, int(w * 0.7), int(h * 0.4), h * 0.8, accent, 0.5)
    elif scene.kind == "offer":
        if food:
            _draw_slice(base, cx, cy, accent, seed)
        glow = _radial_glow(w, h, cx, cy, h * 0.8, accent, 0.75)
    else:  # cta
        glow = _radial_glow(w, h, cx, int(h * 0.5), h * 0.9, accent, 0.55)

    arr = np.asarray(base.convert("RGB"), dtype=np.float32)
    arr = arr + glow
    arr = _apply_vignette(arr, 0.5)
    arr = _film_grain(arr, amount=5.0, seed=seed)
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, "RGB")


# --------------------------------------------------------------------------- #
# pollinations (online) provider — free, no key. Used on a real PC.
# --------------------------------------------------------------------------- #
def render_pollinations(scene: Scene, w: int, h: int, seed: int = 0):
    import requests  # local import: only needed for the online path

    url = ("https://image.pollinations.ai/prompt/"
           f"{quote(scene.image_prompt)}"
           f"?width={w}&height={h}&nologo=true&seed={seed}")
    resp = requests.get(url, timeout=90)
    resp.raise_for_status()
    from io import BytesIO
    img = Image.open(BytesIO(resp.content)).convert("RGB")
    if img.size != (w, h):
        img = img.resize((w, h), Image.LANCZOS)
    return img


# --------------------------------------------------------------------------- #
# dispatch
# --------------------------------------------------------------------------- #
def make_image(scene: Scene, cfg: config.RenderConfig, food: bool) -> Image.Image:
    seed = 1000 + scene.index * 37
    if cfg.image_provider == "pollinations":
        try:
            return render_pollinations(scene, cfg.width, cfg.height, seed)
        except Exception as e:  # graceful offline fallback
            print(f"  [images] pollinations failed ({e}); using local render")
    return render_local(scene, cfg.width, cfg.height, food, seed)
