"""Secours OpenRouter : activation, chaîne de repli, balises <think>, zéro frais."""
import json

import httpx
import pytest

from config import settings
from services import openrouter


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setattr(settings, "LLM_BACKEND", "openrouter")
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "sk-test")
    monkeypatch.setattr(settings, "OPENROUTER_MODELS", "a:free,b:free")


def _mock(monkeypatch, handler):
    """Remplace le client httpx du module par un transport simulé."""
    real = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real(*args, **kwargs)

    monkeypatch.setattr(openrouter.httpx, "AsyncClient", factory)


def _sse(*deltas) -> bytes:
    lines = [f"data: {json.dumps({'choices': [{'delta': d}]})}" for d in deltas]
    return ("\n\n".join(lines + ["data: [DONE]"]) + "\n\n").encode()


async def _collect(messages=None):
    return [p async for p in openrouter.stream_response(messages or [])]


def test_disabled_by_default_or_without_key(monkeypatch):
    monkeypatch.setattr(settings, "LLM_BACKEND", "ollama")
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "sk-test")
    assert not openrouter.enabled()
    monkeypatch.setattr(settings, "LLM_BACKEND", "openrouter")
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "  ")
    assert not openrouter.enabled()


async def test_every_request_caps_price_at_zero(on, monkeypatch):
    bodies = []

    def handler(req):
        bodies.append(json.loads(req.content))
        return httpx.Response(200, content=_sse({"content": "ok"}))

    _mock(monkeypatch, handler)
    assert "".join(await _collect()) == "ok"
    assert all(v == 0 for v in bodies[0]["provider"]["max_price"].values())


async def test_falls_back_to_next_model_then_raises(on, monkeypatch):
    seen = []

    def handler(req):
        seen.append(json.loads(req.content)["model"])
        return httpx.Response(429, text="quota")

    _mock(monkeypatch, handler)
    with pytest.raises(openrouter.OpenRouterUnavailable):
        await _collect()
    assert seen == ["a:free", "b:free"]


async def test_reasoning_wrapped_in_think_tags(on, monkeypatch):
    _mock(monkeypatch, lambda req: httpx.Response(200, content=_sse(
        {"reasoning": "hmm"}, {"reasoning": "…"}, {"content": "réponse"},
        {"reasoning": "tard"}, {"content": "!"})))
    out = "".join(await _collect())
    assert out == "<think>hmm…</think>réponse<think>tard</think>!"


async def test_mid_stream_failure_closes_think_and_does_not_replay(on, monkeypatch):
    calls = []

    class Boom(httpx.ByteStream):
        def __init__(self):
            super().__init__(b"")

        async def __aiter__(self):
            yield _sse({"reasoning": "début"})[:-len(b"data: [DONE]\n\n")]
            raise httpx.ReadError("coupure")

    def handler(req):
        calls.append(1)
        return httpx.Response(200, stream=Boom())

    _mock(monkeypatch, handler)
    out = "".join(await _collect())
    assert out == "<think>début</think>"
    assert len(calls) == 1  # pas de bascule vers le modèle suivant


async def test_complete_skips_empty_answers(on, monkeypatch):
    answers = iter(["", "voilà"])

    def handler(req):
        return httpx.Response(200, json={"choices": [{"message": {"content": next(answers)}}]})

    _mock(monkeypatch, handler)
    assert await openrouter.complete([]) == "voilà"
