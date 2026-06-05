"""
Tests du « Tout valider » (routers/chat._await_confirm + conteneur approve_all).
"""
import asyncio
import json

import pytest

from routers import chat


class FakeWS:
    def __init__(self):
        self.sent = []

    async def send_text(self, txt):
        self.sent.append(json.loads(txt))

    def types(self):
        return [m["type"] for m in self.sent]


@pytest.mark.asyncio
async def test_approve_all_skips_prompt_when_already_on():
    ws = FakeWS()
    q: asyncio.Queue = asyncio.Queue()
    approved = await chat._await_confirm("rm x", ws, q, {"on": True})
    assert approved is True
    # aucune fenêtre de confirmation envoyée
    assert "confirm_exec" not in ws.types()


@pytest.mark.asyncio
async def test_tout_valider_sets_flag_and_approves():
    ws = FakeWS()
    q: asyncio.Queue = asyncio.Queue()
    await q.put(json.dumps({"type": "exec_response", "approved": True, "all": True}))
    state = {"on": False}
    approved = await chat._await_confirm("rm a", ws, q, state)
    assert approved is True
    assert state["on"] is True          # mémorisé pour la suite du tour
    assert "confirm_exec" in ws.types()  # la 1re a bien demandé


@pytest.mark.asyncio
async def test_subsequent_command_auto_approved_after_tout_valider():
    ws = FakeWS()
    q: asyncio.Queue = asyncio.Queue()
    state = {"on": True}   # déjà activé par une commande précédente
    approved = await chat._await_confirm("rm b", ws, q, state)
    assert approved is True
    assert ws.types() == []   # plus aucune fenêtre


@pytest.mark.asyncio
async def test_simple_approve_does_not_set_flag():
    ws = FakeWS()
    q: asyncio.Queue = asyncio.Queue()
    await q.put(json.dumps({"type": "exec_response", "approved": True}))
    state = {"on": False}
    approved = await chat._await_confirm("rm c", ws, q, state)
    assert approved is True
    assert state["on"] is False   # « Exécuter » simple ne déclenche pas le tout-valider


@pytest.mark.asyncio
async def test_decline_returns_false():
    ws = FakeWS()
    q: asyncio.Queue = asyncio.Queue()
    await q.put(json.dumps({"type": "exec_response", "approved": False}))
    assert await chat._await_confirm("rm d", ws, q, {"on": False}) is False
