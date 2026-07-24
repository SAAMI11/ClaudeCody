@echo off
REM SAAMai setup & start script for Windows.
REM Creates a virtual environment, installs dependencies, downloads the
REM default free/open-source AI models via Ollama, then starts the app.

cd /d "%~dp0\.."

if not exist .venv (
    echo Erstelle virtuelle Python-Umgebung ^(.venv^) ...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo Installiere Abhaengigkeiten ...
pip install --upgrade pip -q
pip install -r requirements.txt -q

python scripts\setup.py

echo.
echo Starte SAAMai unter http://127.0.0.1:8000 ...
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
