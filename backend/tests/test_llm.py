"""
Tests for services/llm.py.
The Ollama client is mocked — no real model required.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from services.llm import select_model


# ── select_model ──────────────────────────────────────────────────────────────

class TestSelectModel:
    def test_classify_uses_fast_model(self, monkeypatch):
        from config import settings
        monkeypatch.setattr(settings, "FAST_MODEL", "fast-model")
        monkeypatch.setattr(settings, "REASONING_MODEL", "reason-model")
        assert select_model("classify") == "fast-model"

    def test_summarize_short_uses_fast_model(self, monkeypatch):
        from config import settings
        monkeypatch.setattr(settings, "FAST_MODEL", "fast-model")
        assert select_model("summarize_short") == "fast-model"

    def test_autocomplete_uses_fast_model(self, monkeypatch):
        from config import settings
        monkeypatch.setattr(settings, "FAST_MODEL", "fast-model")
        assert select_model("autocomplete") == "fast-model"

    def test_quick_answer_uses_fast_model(self, monkeypatch):
        from config import settings
        monkeypatch.setattr(settings, "FAST_MODEL", "fast-model")
        assert select_model("quick_answer") == "fast-model"

    def test_reason_uses_reasoning_model(self, monkeypatch):
        from config import settings
        monkeypatch.setattr(settings, "FAST_MODEL", "fast-model")
        monkeypatch.setattr(settings, "REASONING_MODEL", "reason-model")
        assert select_model("reason") == "reason-model"

    def test_unknown_task_uses_reasoning_model(self, monkeypatch):
        from config import settings
        monkeypatch.setattr(settings, "REASONING_MODEL", "reason-model")
        assert select_model("unknown_task_type") == "reason-model"

    def test_empty_task_type_uses_reasoning_model(self, monkeypatch):
        from config import settings
        monkeypatch.setattr(settings, "REASONING_MODEL", "reason-model")
        assert select_model("") == "reason-model"


# ── stream_response (mocked Ollama) ───────────────────────────────────────────

class TestStreamResponse:
    @pytest.mark.asyncio
    async def test_yields_tokens(self, monkeypatch):
        from services import llm

        # ollama client.chat(stream=True) returns an awaitable async iterable:
        # await client.chat(...) → async generator. Use AsyncMock(return_value=gen()).
        async def _gen():
            for token in ["Hello", " ", "world"]:
                yield {"message": {"content": token}}

        mock_client = MagicMock()
        mock_client.chat = AsyncMock(return_value=_gen())
        monkeypatch.setattr(llm.ollama, "AsyncClient", lambda host: mock_client)

        tokens = []
        async for t in llm.stream_response([{"role": "user", "content": "hi"}]):
            tokens.append(t)

        assert tokens == ["Hello", " ", "world"]

    @pytest.mark.asyncio
    async def test_uses_correct_model_for_task(self, monkeypatch):
        from services import llm
        from config import settings
        monkeypatch.setattr(settings, "FAST_MODEL", "my-fast")
        monkeypatch.setattr(settings, "REASONING_MODEL", "my-reason")

        called_with_model = []

        async def _gen():
            yield {"message": {"content": "ok"}}

        async def fake_chat(*args, **kwargs):
            called_with_model.append(kwargs.get("model"))
            return _gen()

        mock_client = MagicMock()
        mock_client.chat = fake_chat
        monkeypatch.setattr(llm.ollama, "AsyncClient", lambda host: mock_client)

        async for _ in llm.stream_response([], task_type="classify"):
            pass

        assert called_with_model[0] == "my-fast"


# ── complete (mocked Ollama) ──────────────────────────────────────────────────

class TestComplete:
    @pytest.mark.asyncio
    async def test_returns_response_content(self, monkeypatch):
        from services import llm

        async def fake_chat(*args, **kwargs):
            return {"message": {"content": "planned response"}}

        mock_client = MagicMock()
        mock_client.chat = AsyncMock(return_value={"message": {"content": "planned response"}})
        monkeypatch.setattr(llm.ollama, "AsyncClient", lambda host: mock_client)

        result = await llm.complete([{"role": "user", "content": "plan this"}])
        assert result == "planned response"

    @pytest.mark.asyncio
    async def test_uses_default_model_when_none(self, monkeypatch):
        from services import llm
        from config import settings
        monkeypatch.setattr(settings, "REASONING_MODEL", "default-model")

        captured = {}

        mock_client = MagicMock()
        async def fake_chat(*args, **kwargs):
            captured["model"] = kwargs.get("model")
            return {"message": {"content": "ok"}}

        mock_client.chat = fake_chat
        monkeypatch.setattr(llm.ollama, "AsyncClient", lambda host: mock_client)

        await llm.complete([], model=None)
        assert captured["model"] == "default-model"
