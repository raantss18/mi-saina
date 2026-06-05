"""
Tests de _exec_streaming sur le chemin sudo (routers/chat.py).

Couvre la correction du bug : un « stop » (ou une déconnexion) PENDANT l'attente
du mot de passe sudo doit interrompre immédiatement — avant, le code restait
bloqué sur sudo_q.get() jusqu'au timeout de 120 s car le PTY avait déjà rendu
la main et plus personne n'écoutait stop_event.
"""
import asyncio
import json

import pytest

from routers import chat


class FakeWS:
    """WebSocket minimal : capture les messages envoyés (décodés en dict)."""

    def __init__(self):
        self.sent = []

    async def send_text(self, txt):
        self.sent.append(json.loads(txt))

    def types(self):
        return [m["type"] for m in self.sent]


async def _fake_stream_pty(cmd, sudo_password=None, **kwargs):
    """Imite shell_stream.stream_pty : demande sudo tant qu'aucun mot de passe,
    puis exécute normalement une fois le mot de passe fourni."""
    if sudo_password is None:
        yield {"type": "needs_sudo", "command": cmd}
        return
    yield {"type": "chunk", "text": "ok\n"}
    yield {"type": "done", "returncode": 0}


@pytest.fixture(autouse=True)
def _patch_stream_pty(monkeypatch):
    monkeypatch.setattr(chat, "stream_pty", _fake_stream_pty)


@pytest.mark.asyncio
async def test_stop_during_sudo_wait_interrupts_immediately():
    ws = FakeWS()
    q: asyncio.Queue = asyncio.Queue()
    await q.put(json.dumps({"type": "stop"}))   # stop déjà en file

    out, rc, stopped, outcome = await asyncio.wait_for(
        chat._exec_streaming("sudo pacman -Syu", ws, q), timeout=5.0)

    assert stopped is True
    assert rc == -1
    assert outcome["status"] == "failure"
    assert "needs_sudo" in ws.types()
    done = [m for m in ws.sent if m["type"] == "shell_done"]
    assert done and done[-1]["status"] == "stopped"


@pytest.mark.asyncio
async def test_disconnect_during_sudo_wait_interrupts():
    """Une déconnexion (None dans la file) doit aussi débloquer l'attente sudo."""
    ws = FakeWS()
    q: asyncio.Queue = asyncio.Queue()
    await q.put(None)   # _ws_reader pousse None à la déconnexion

    out, rc, stopped, outcome = await asyncio.wait_for(
        chat._exec_streaming("sudo pacman -Syu", ws, q), timeout=5.0)

    assert stopped is True
    assert rc == -1


@pytest.mark.asyncio
async def test_password_resumes_execution():
    """Chemin nominal préservé : fournir le mot de passe relance la commande."""
    ws = FakeWS()
    q: asyncio.Queue = asyncio.Queue()
    await q.put(json.dumps({"type": "sudo_response", "password": "secret"}))

    out, rc, stopped, outcome = await asyncio.wait_for(
        chat._exec_streaming("sudo pacman -Syu", ws, q), timeout=5.0)

    assert stopped is False
    assert rc == 0
    assert outcome["status"] == "success"
    assert "ok" in out
    # un seul bloc terminal : shell_start n'est PAS renvoyé lors du relancement
    assert ws.types().count("shell_start") == 1
