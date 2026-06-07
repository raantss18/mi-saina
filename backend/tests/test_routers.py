"""
Integration tests for FastAPI routers using TestClient.

For memory routes: the in-memory SQLite engine is patched via the mem_engine fixture.
For config routes: filesystem paths are patched to a tmp_path.
For models routes: httpx calls are mocked.
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
import services.memory as memory_module
from services.memory import Base


# ── Shared test client fixture ─────────────────────────────────────────────────

@pytest.fixture
def client(monkeypatch, tmp_path):
    """TestClient with file-based SQLite (needed for cross-thread access) and isolated config."""
    # Use a file-based DB so TestClient's thread can access the same tables
    test_engine = create_engine(f"sqlite:///{tmp_path}/test.db", echo=False)
    Base.metadata.create_all(test_engine)
    monkeypatch.setattr(memory_module, "engine", test_engine)

    # Patch config paths to tmp_path
    import routers.config_router as cfg_router
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    skills_dir = config_dir / "skills"
    skills_dir.mkdir()
    monkeypatch.setattr(cfg_router, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(cfg_router, "SYSTEM_PROMPT_FILE", config_dir / "system_prompt.txt")
    monkeypatch.setattr(cfg_router, "SKILLS_DIR", skills_dir)

    from main import app
    with TestClient(app) as c:
        yield c


# ── /health ───────────────────────────────────────────────────────────────────

def test_health_returns_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ── /memory/sessions ──────────────────────────────────────────────────────────

def test_create_session_no_title(client):
    resp = client.post("/memory/sessions", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert data["title"] is None


def test_create_session_with_title(client):
    resp = client.post("/memory/sessions", json={"title": "My Session"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "My Session"


def test_list_sessions_empty(client):
    resp = client.get("/memory/sessions")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_sessions_after_create(client):
    client.post("/memory/sessions", json={"title": "Alpha"})
    client.post("/memory/sessions", json={"title": "Beta"})
    resp = client.get("/memory/sessions")
    assert resp.status_code == 200
    titles = {s["title"] for s in resp.json()}
    assert titles == {"Alpha", "Beta"}


def test_get_session_messages_empty(client):
    create_resp = client.post("/memory/sessions", json={})
    sid = create_resp.json()["id"]
    resp = client.get(f"/memory/sessions/{sid}/messages")
    assert resp.status_code == 200
    assert resp.json() == []


def test_delete_session(client):
    create_resp = client.post("/memory/sessions", json={"title": "To Delete"})
    sid = create_resp.json()["id"]
    resp = client.delete(f"/memory/sessions/{sid}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"
    sessions = client.get("/memory/sessions").json()
    assert all(s["id"] != sid for s in sessions)


# ── /config/system-prompt ─────────────────────────────────────────────────────

def test_get_system_prompt_default(client):
    resp = client.get("/config/system-prompt")
    assert resp.status_code == 200
    assert "mi-saina" in resp.json()["content"]


def test_put_and_get_system_prompt(client):
    new_prompt = "You are a custom AI assistant."
    resp = client.put("/config/system-prompt", json={"content": new_prompt})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    resp = client.get("/config/system-prompt")
    assert resp.json()["content"] == new_prompt


def test_put_system_prompt_persists(client):
    client.put("/config/system-prompt", json={"content": "Test prompt"})
    # Second GET should still return the persisted value
    resp = client.get("/config/system-prompt")
    assert resp.json()["content"] == "Test prompt"


# ── /config/skills ────────────────────────────────────────────────────────────

def test_list_skills_empty(client):
    resp = client.get("/config/skills")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_skill(client):
    skill = {
        "name": "git-status",
        "trigger": "/git",
        "description": "Show git status",
        "icon": "🔧",
        "prompt": "Run git status and summarize",
    }
    resp = client.post("/config/skills", json=skill)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_list_skills_after_create(client):
    skill = {
        "name": "my-skill",
        "trigger": "/skill",
        "description": "A test skill",
        "icon": "⚡",
        "prompt": "Do something",
    }
    client.post("/config/skills", json=skill)
    resp = client.get("/config/skills")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["name"] == "my-skill"


def test_delete_skill(client):
    skill = {
        "name": "to-delete",
        "trigger": "/del",
        "description": "Will be deleted",
        "icon": "🗑",
        "prompt": "temp",
    }
    client.post("/config/skills", json=skill)
    resp = client.delete("/config/skills/to-delete")
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"
    assert client.get("/config/skills").json() == []


def test_delete_nonexistent_skill_returns_404(client):
    resp = client.delete("/config/skills/nonexistent")
    assert resp.status_code == 404


def test_skill_name_sanitized_in_filename(client):
    skill = {
        "name": "my skill with spaces!",
        "trigger": "/test",
        "description": "sanitization test",
        "icon": "⚡",
        "prompt": "prompt",
    }
    resp = client.post("/config/skills", json=skill)
    assert resp.status_code == 200


# ── /models ───────────────────────────────────────────────────────────────────

def test_list_models_returns_list(client):
    mock_models = {
        "models": [
            {"name": "qwen3.5:9b", "size": 5_200_000_000, "modified_at": "2024-01-01"},
        ]
    }

    async def mock_get(*args, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        resp.json = MagicMock(return_value=mock_models)
        return resp

    with patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.get = AsyncMock(return_value=MagicMock(
            status_code=200,
            json=MagicMock(return_value=mock_models)
        ))
        MockClient.return_value = instance

        resp = client.get("/models/list")

    assert resp.status_code == 200


def test_select_model_updates_settings(client, monkeypatch, tmp_path):
    # Isolation : ne JAMAIS écrire le vrai .env du dépôt depuis les tests.
    from config import settings
    monkeypatch.setattr("routers.models._ENV_FILE", str(tmp_path / ".env"))
    monkeypatch.setattr(settings, "REASONING_MODEL", "before:0b")
    monkeypatch.setattr(settings, "FAST_MODEL", "before:0b")

    resp = client.post("/models/select", json={"model": "my-model:7b"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["active_model"] == "my-model:7b"
    assert settings.REASONING_MODEL == "my-model:7b"


def test_delete_active_model_returns_400(client, monkeypatch):
    from config import settings
    monkeypatch.setattr(settings, "REASONING_MODEL", "active-model:9b")
    resp = client.delete("/models/delete/active-model:9b")
    assert resp.status_code == 400


def test_delete_inactive_model(client, monkeypatch):
    from config import settings
    monkeypatch.setattr(settings, "REASONING_MODEL", "other-model:9b")

    async def mock_delete(*args, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        return resp

    with patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.delete = AsyncMock(return_value=MagicMock(status_code=200))
        MockClient.return_value = instance

        resp = client.delete("/models/delete/inactive-model:7b")

    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"
