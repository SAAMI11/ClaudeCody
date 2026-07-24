"""
routers/models.py
==================
Lists locally installed Ollama models and lets the UI trigger a model
download (streamed progress), so getting a new open-source model onto
the machine never requires leaving SAAMai or touching a terminal.
"""

import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..schemas import ModelPullRequest
from ..services import llm

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("")
async def get_models():
    try:
        return await llm.list_models()
    except llm.LLMError as exc:
        return {"error": str(exc), "models": []}


@router.post("/pull")
async def pull_model(payload: ModelPullRequest):
    async def generate():
        async for event in llm.pull_model(payload.name):
            yield json.dumps(event) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")
