"""
routers/plugins.py
===================
Read-only listing of currently loaded plugins, so the settings menu can
show users what extensions are active. Installing a plugin is just
copying a .py file into backend/app/plugins/ and restarting the server -
see services/plugin_loader.py for the interface.
"""

from fastapi import APIRouter

from ..services.plugin_loader import registry

router = APIRouter(prefix="/api/plugins", tags=["plugins"])


@router.get("")
def list_plugins():
    return [{"name": p.name, "description": p.description} for p in registry.plugins]
