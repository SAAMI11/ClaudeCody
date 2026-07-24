#!/usr/bin/env bash
# SAAMai setup & start script for Linux and macOS.
# Creates a virtual environment, installs dependencies, downloads the
# default free/open-source AI models via Ollama, then starts the app.
set -e

cd "$(dirname "$0")/.."

if [ ! -d ".venv" ]; then
  echo "Erstelle virtuelle Python-Umgebung (.venv) ..."
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "Installiere Abhaengigkeiten ..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

python3 scripts/setup.py

echo ""
echo "Starte SAAMai unter http://127.0.0.1:8000 ..."
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
