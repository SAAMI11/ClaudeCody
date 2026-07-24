"""
main.py
=======
Application entry point: creates the FastAPI app, wires up every
router, initialises the local SQLite database and plugin registry on
startup, and serves the static frontend (frontend/) so the whole app -
API and UI - is a single process on a single port.

Run with:  uvicorn backend.app.main:app --reload
(or simply run scripts/setup.py / start.sh, see README.md)
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import BASE_DIR, settings
from .database import init_db
from .routers import auth, chats, documents, i18n, messages, models, plugins, settings as settings_router
from .services.plugin_loader import registry

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("saamai")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    registry.discover()
    logger.info("SAAMai gestartet - %d Plugin(s) geladen.", len(registry.plugins))
    yield


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

# CORS is only relevant if the frontend is ever served from a different
# origin (e.g. during development with a separate dev server). The
# packaged app serves frontend + API from the same origin, so this is a
# convenience, not a security boundary that's relied upon.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chats.router)
app.include_router(messages.router)
app.include_router(documents.router)
app.include_router(settings_router.router)
app.include_router(models.router)
app.include_router(plugins.router)
app.include_router(i18n.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "name": settings.app_name, "version": settings.app_version}


# Serve the frontend as static files, mounted last so it doesn't shadow
# the /api/* routes above. html=True makes "/" resolve to index.html.
frontend_dir = BASE_DIR / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
