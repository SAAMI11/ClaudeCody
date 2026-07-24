"""
llm.py
======
Thin async client around Ollama (https://ollama.com) - a free,
open-source local model runner. This is the *only* place that talks to
an LLM backend, so swapping Ollama for another local, OpenAI-compatible
server (LM Studio, llama.cpp server, ...) only ever requires changes in
this one file.

Ollama exposes a plain local HTTP API (default http://127.0.0.1:11434):
  - GET  /api/tags            -> list downloaded models
  - POST /api/pull            -> download a model (streamed progress)
  - POST /api/chat            -> chat completion (streamed token deltas)

Vision models (e.g. "llava") accept images as a list of base64 strings
attached to a chat message, which is how SAAMai implements image
analysis without any paid vision API.
"""

import base64
import json
from collections.abc import AsyncIterator

import httpx

from ..config import settings


class LLMError(RuntimeError):
    """Raised when the local model backend is unreachable or errors out."""


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=settings.llm_base_url, timeout=httpx.Timeout(120.0, connect=5.0))


async def list_models() -> list[dict]:
    try:
        async with _client() as client:
            resp = await client.get("/api/tags")
            resp.raise_for_status()
            return resp.json().get("models", [])
    except httpx.HTTPError as exc:
        raise LLMError(
            "Ollama ist nicht erreichbar. Bitte starte Ollama (https://ollama.com) "
            "und stelle sicher, dass es unter "
            f"{settings.llm_base_url} laeuft."
        ) from exc


async def pull_model(name: str) -> AsyncIterator[dict]:
    """Streams download progress events while Ollama pulls a model."""
    async with _client() as client:
        async with client.stream("POST", "/api/pull", json={"name": name}) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.strip():
                    yield json.loads(line)


def encode_image(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("ascii")


async def chat_stream(
    model: str,
    messages: list[dict],
    images_b64: list[str] | None = None,
) -> AsyncIterator[str]:
    """Streams the assistant's reply token-by-token.

    ``messages`` is the standard [{"role": ..., "content": ...}, ...]
    list. If ``images_b64`` is given it is attached to the last user
    message so a multimodal model (e.g. llava) can analyse the image(s).
    """
    payload_messages = [dict(m) for m in messages]
    if images_b64 and payload_messages:
        payload_messages[-1]["images"] = images_b64

    body = {"model": model, "messages": payload_messages, "stream": True}

    try:
        async with _client() as client:
            async with client.stream("POST", "/api/chat", json=body) as resp:
                if resp.status_code == 404:
                    raise LLMError(
                        f"Modell '{model}' ist nicht installiert. Lade es zuerst herunter, "
                        f"z. B. mit: ollama pull {model}"
                    )
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    chunk = json.loads(line)
                    if chunk.get("done"):
                        break
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        yield token
    except httpx.ConnectError as exc:
        raise LLMError(
            "Ollama ist nicht erreichbar. Bitte starte Ollama (https://ollama.com) "
            f"und stelle sicher, dass es unter {settings.llm_base_url} laeuft."
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise LLMError(f"Fehler vom Modell-Server: {exc}") from exc
