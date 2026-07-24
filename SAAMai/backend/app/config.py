"""
config.py
=========
Central configuration for SAAMai. All settings can be overridden with
environment variables (or a local ``.env`` file) so the app never needs
code changes to run on a different machine.

No paid service is configured anywhere in this file. The default LLM
backend is Ollama (https://ollama.com), a free and open-source local
model runner. Users can point SAAMAI_LLM_BASE_URL at any other
OpenAI-API-compatible *local* server (e.g. LM Studio, llama.cpp server)
without touching the code.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SAAMAI_", env_file=".env", extra="ignore")

    app_name: str = "SAAMai"
    app_version: str = "1.0.0"

    # SQLite by default - a real local database file, no external server required.
    database_url: str = f"sqlite:///{(DATA_DIR / 'saamai.db').as_posix()}"

    # Ollama (or any OpenAI-compatible local server) endpoint.
    llm_base_url: str = "http://127.0.0.1:11434"
    default_text_model: str = "llama3.1"
    default_vision_model: str = "llava"

    # Auth (local accounts only, no third-party identity provider).
    secret_key: str = "change-this-secret-in-production-please"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Uploads
    max_upload_mb: int = 25

    # Default UI language
    default_language: str = "de"

    def ensure_dirs(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
