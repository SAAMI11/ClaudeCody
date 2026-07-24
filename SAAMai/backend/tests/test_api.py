"""
test_api.py
===========
Basic API tests covering the core flow: create a chat, send a message
(with the LLM backend mocked out so tests never require Ollama to be
installed), list/search chats, persist settings and export a chat.
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services import llm as llm_service


async def _fake_chat_stream(model, messages, images_b64=None):
    for token in ["Hallo", " ", "Welt"]:
        yield token


@pytest.fixture(autouse=True)
def fake_llm(monkeypatch):
    monkeypatch.setattr(llm_service, "chat_stream", _fake_chat_stream)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["name"] == "SAAMai"


def test_create_and_list_chat(client):
    resp = client.post("/api/chats", json={})
    assert resp.status_code == 201
    chat_id = resp.json()["id"]

    resp = client.get("/api/chats")
    assert resp.status_code == 200
    assert any(c["id"] == chat_id for c in resp.json())


def test_send_message_stream_persists_both_messages(client):
    chat_id = client.post("/api/chats", json={}).json()["id"]

    resp = client.post(f"/api/chats/{chat_id}/messages/stream", json={"content": "Hi"})
    assert resp.status_code == 200
    assert "Hallo" in resp.text

    detail = client.get(f"/api/chats/{chat_id}").json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]
    assert detail["messages"][1]["content"] == "Hallo Welt"


def test_chat_search(client):
    chat_id = client.post("/api/chats", json={}).json()["id"]
    client.post(f"/api/chats/{chat_id}/messages/stream", json={"content": "Erzaehl mir einen Witz"})

    resp = client.get("/api/chats", params={"q": "Witz"})
    assert resp.status_code == 200
    assert any(c["id"] == chat_id for c in resp.json())

    resp = client.get("/api/chats", params={"q": "nonexistent-xyz"})
    assert all(c["id"] != chat_id for c in resp.json())


def test_settings_roundtrip(client):
    resp = client.put("/api/settings", json={"key": "theme", "value": "light"})
    assert resp.status_code == 200

    resp = client.get("/api/settings")
    assert any(s["key"] == "theme" and s["value"] == "light" for s in resp.json())


def test_export_chat_json(client):
    chat_id = client.post("/api/chats", json={}).json()["id"]
    client.post(f"/api/chats/{chat_id}/messages/stream", json={"content": "Hi"})

    resp = client.get(f"/api/chats/{chat_id}/export", params={"format": "json"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")


def test_delete_chat(client):
    chat_id = client.post("/api/chats", json={}).json()["id"]
    resp = client.delete(f"/api/chats/{chat_id}")
    assert resp.status_code == 204

    resp = client.get(f"/api/chats/{chat_id}")
    assert resp.status_code == 404


def test_plugins_loaded(client):
    resp = client.get("/api/plugins")
    assert resp.status_code == 200
    names = [p["name"] for p in resp.json()]
    assert "example-plugin" in names
