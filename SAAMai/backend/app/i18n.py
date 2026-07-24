"""
i18n.py
=======
Tiny server-side helper that exposes the same translation files the
frontend uses (frontend/locales/*.json) over the API, so new languages
only ever need one new JSON file - no code changes on either side.
"""

import json
from functools import lru_cache

from .config import BASE_DIR

LOCALES_DIR = BASE_DIR / "frontend" / "locales"


@lru_cache
def available_languages() -> list[str]:
    if not LOCALES_DIR.exists():
        return ["de", "en"]
    return sorted(p.stem for p in LOCALES_DIR.glob("*.json"))


@lru_cache
def load_translations(lang: str) -> dict:
    path = LOCALES_DIR / f"{lang}.json"
    if not path.exists():
        path = LOCALES_DIR / "en.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)
