"""
brain — turn one free-text prompt into a structured storyboard.

Offline this uses lightweight heuristics + copy templates so the whole pipeline
runs without any API. On your own PC you can swap `build_storyboard` for a call
to a free LLM (Pollinations text endpoint, a local Ollama model, ...) that
returns the same `Storyboard` shape — everything downstream stays the same.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Scene:
    index: int
    kind: str            # hook | hero | atmosphere | offer | cta
    title: str           # short big on-screen headline
    caption: str         # subtitle / narration line for this scene
    palette: tuple       # (top_rgb, bottom_rgb, accent_rgb)
    motion: str          # zoom_in | zoom_out | pan_left | pan_right
    duration: float      # seconds (before transition overlap)
    image_prompt: str    # prompt handed to the image provider


@dataclass
class Storyboard:
    title: str
    subject: str
    style: str
    scenes: list[Scene]
    narration: str
    total_seconds: float
    meta: dict = field(default_factory=dict)


# --- warm, cinematic palettes -------------------------------------------------
# (top color, bottom color, accent) — tuned for food / warm-light ads.
_PALETTES = {
    "hook":       ((28, 14, 10), (92, 30, 12), (255, 176, 74)),
    "hero":       ((40, 20, 12), (120, 52, 20), (255, 205, 110)),
    "atmosphere": ((22, 16, 26), (74, 40, 46), (255, 150, 120)),
    "offer":      ((60, 16, 14), (150, 40, 24), (255, 224, 140)),
    "cta":        ((14, 12, 16), (44, 30, 34), (255, 196, 96)),
}

_MOTIONS = ["zoom_in", "pan_left", "zoom_out", "pan_right", "zoom_in"]


def _parse_duration(prompt: str, default: float = 20.0) -> float:
    m = re.search(r"(\d+)\s*(?:sek|sec|s\b|second)", prompt, re.I)
    if m:
        return max(8.0, min(60.0, float(m.group(1))))
    return default


_STOP_WORDS = {"im", "in", "auf", "mit", "zum", "zur", "und", "for", "the",
               "a", "an", "of", "als", "der", "die", "das", "des", "eines"}


def _detect_subject(prompt: str) -> str:
    m = re.search(r"(?:für|for|about|über)\s+(?:eine?n?\s+|a\s+|the\s+)?"
                  r"([A-Za-zÄÖÜäöüß][\wÄÖÜäöüß\- ]{2,40})", prompt)
    if m:
        raw = m.group(1).strip().split(",")[0]
        # keep words up to the first connective/stop word (e.g. drop "im modernen ...")
        words: list[str] = []
        for w in raw.split():
            if w.lower() in _STOP_WORDS and words:
                break
            words.append(w)
        subject = " ".join(words).strip()
        if subject:
            return subject
    for kw in ("pizzeria", "pizza", "restaurant", "café", "cafe", "bakery",
               "bäckerei", "burger", "coffee"):
        if kw in prompt.lower():
            return kw.capitalize()
    return "Ihr Produkt"


def _detect_style(prompt: str) -> str:
    for kw in ("cineast", "cinemat", "modern", "vintage", "minimal",
               "elegant", "dramatisch", "dramatic"):
        if kw in prompt.lower():
            return kw
    return "cinematic"


def _is_food(subject: str, prompt: str) -> bool:
    blob = (subject + " " + prompt).lower()
    return any(k in blob for k in
               ("pizz", "restaurant", "food", "essen", "café", "cafe",
                "burger", "bäcker", "bakery", "coffee", "kaffee", "pasta"))


def build_storyboard(prompt: str, target_seconds: float | None = None) -> Storyboard:
    subject = _detect_subject(prompt)
    style = _detect_style(prompt)
    total = target_seconds or _parse_duration(prompt)
    food = _is_food(subject, prompt)

    # Ad beat sheet: hook -> hero shot -> atmosphere -> offer -> call to action.
    beats = ["hook", "hero", "atmosphere", "offer", "cta"]
    per = round(total / len(beats), 2)

    if food:
        copy = {
            "hook":       (f"{subject}", "Wo jeder Abend nach Ofen und Basilikum duftet."),
            "hero":       ("Frisch aus dem Ofen", "Knuspriger Boden, geschmolzener Käse, echte Zutaten."),
            "atmosphere": ("Zeit für Genuss", "Warmes Licht, gute Gesellschaft, ehrliche Küche."),
            "offer":      ("2 für 1 — heute", "Jeden Abend frisch für dich zubereitet."),
            "cta":        (f"{subject}", "Jetzt reservieren · Wir freuen uns auf dich."),
        }
        img = {
            "hook":       f"cinematic wide shot of a cozy pizzeria at night, glowing wood-fired oven, warm light, {style}",
            "hero":       f"top-down macro of a fresh margherita pizza, bubbling cheese, basil, steam, {style} food photography",
            "atmosphere": f"warm candle-lit restaurant table, bokeh lights, rustic wood, {style} mood",
            "offer":      f"elegant pizza slice pulled apart with cheese strings, dark warm background, {style}",
            "cta":        f"minimal elegant pizzeria logo on dark wood, warm rim light, {style}",
        }
    else:
        copy = {
            "hook":       (f"{subject}", "Eine Idee, die auffällt."),
            "hero":       ("Im Mittelpunkt", "Klar, hochwertig, unverwechselbar."),
            "atmosphere": ("Der richtige Moment", "Gemacht für Menschen wie dich."),
            "offer":      ("Jetzt entdecken", "Zeitlich begrenztes Angebot."),
            "cta":        (f"{subject}", "Mehr erfahren · Heute noch."),
        }
        img = {b: f"{subject}, {style} commercial, warm cinematic lighting" for b in beats}

    scenes: list[Scene] = []
    for i, b in enumerate(beats):
        title, caption = copy[b]
        scenes.append(Scene(
            index=i,
            kind=b,
            title=title,
            caption=caption,
            palette=_PALETTES[b],
            motion=_MOTIONS[i % len(_MOTIONS)],
            duration=per,
            image_prompt=img[b],
        ))

    narration = " ".join(s.caption for s in scenes)
    return Storyboard(
        title=subject,
        subject=subject,
        style=style,
        scenes=scenes,
        narration=narration,
        total_seconds=total,
        meta={"food": food, "beats": beats},
    )
