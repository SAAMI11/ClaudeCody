"""
routers/i18n.py
================
Exposes the translation files under an API path too (in addition to
being served as static files), and lists which languages are available
so the settings menu's language dropdown can build itself dynamically -
adding a new language never requires a code change, just a new JSON
file in frontend/locales/.
"""

from fastapi import APIRouter

from ..i18n import available_languages, load_translations

router = APIRouter(prefix="/api/i18n", tags=["i18n"])


@router.get("/languages")
def get_languages():
    return available_languages()


@router.get("/{lang}")
def get_translations(lang: str):
    return load_translations(lang)
