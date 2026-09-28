"""Rendert chat.html als 1080x1920 PNG (9:16)."""
import pathlib

from playwright.sync_api import sync_playwright

here = pathlib.Path(__file__).parent
with sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 540, "height": 960}, device_scale_factor=2)
    page.goto((here / "chat.html").resolve().as_uri())
    page.screenshot(path=str(here / "whatsapp-blinker.png"))
    browser.close()
