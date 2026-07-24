#!/usr/bin/env python3
"""
scripts/setup.py
=================
Cross-platform (Windows / Linux / macOS) setup helper for SAAMai. This
script only handles the *AI model backend* part of setup - installing
Python dependencies and creating a virtual environment is done by
scripts/setup.sh (Linux/macOS) or scripts/setup.bat (Windows), since
that's simple, OS-native shell work.

What this script does:
  1. Checks whether Ollama (https://ollama.com, free & open-source) is
     installed. If not, prints download instructions and exits cleanly -
     SAAMai's UI will still start and explain the same thing.
  2. Checks whether the Ollama daemon is actually running.
  3. Downloads ("pulls") the default text and vision models so SAAMai
     works out of the box, unless they're already present.

No paid service is ever contacted by this script.
"""

import shutil
import subprocess
import sys
import urllib.request

OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_TEXT_MODEL = "llama3.1"
DEFAULT_VISION_MODEL = "llava"

INSTALL_HINTS = {
    "linux": "curl -fsSL https://ollama.com/install.sh | sh",
    "darwin": "brew install ollama   (oder Installer von https://ollama.com/download)",
    "win32": "Installer von https://ollama.com/download herunterladen und ausfuehren",
}


def ollama_installed() -> bool:
    return shutil.which("ollama") is not None


def ollama_running() -> bool:
    try:
        urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=2)
        return True
    except Exception:
        return False


def pull_model(name: str) -> None:
    print(f"-> Lade Modell '{name}' herunter (das kann je nach Groesse einige Minuten dauern) ...")
    subprocess.run(["ollama", "pull", name], check=False)


def main() -> int:
    print("SAAMai Setup - pruefe lokalen KI-Modell-Server (Ollama) ...\n")

    if not ollama_installed():
        hint = INSTALL_HINTS.get(sys.platform, "https://ollama.com/download")
        print(
            "Ollama wurde nicht gefunden. SAAMai nutzt Ollama, um KI-Modelle "
            "komplett kostenlos und lokal auszufuehren.\n"
            f"Installationsbefehl fuer dein System:\n  {hint}\n\n"
            "Fuehre dieses Setup danach erneut aus, um automatisch die "
            "Standardmodelle herunterzuladen. SAAMai startet auch ohne "
            "Ollama, kann dann aber keine Antworten generieren."
        )
        return 0

    print("Ollama gefunden.")

    if not ollama_running():
        print(
            "Ollama laeuft aktuell nicht. Starte es in einem separaten Terminal mit:\n"
            "  ollama serve\n"
            "und fuehre dieses Setup danach erneut aus, um die Standardmodelle zu laden."
        )
        return 0

    print("Ollama laeuft. Lade Standardmodelle (falls noch nicht vorhanden) ...")
    pull_model(DEFAULT_TEXT_MODEL)
    pull_model(DEFAULT_VISION_MODEL)
    print("\nFertig! SAAMai ist bereit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
