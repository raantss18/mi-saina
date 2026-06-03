import asyncio
import re
from pathlib import Path
import json

import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from config import settings
from services.llm import stream_response, select_model
from services.memory import (
    add_message, get_session_messages, build_context_prefix, create_session,
    update_session_title, session_message_count,
)
from services.shell_exec import execute_command
from services.shell_stream import stream_pty

router = APIRouter()

EXEC_RE = re.compile(r'\[EXEC:\s*(.*?)\]', re.DOTALL)
CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
SYSTEM_PROMPT_FILE = CONFIG_DIR / "system_prompt.txt"

_DEFAULT_SYSTEM = "Tu es LocalMind, un assistant IA local expert avec accès complet à la machine Linux."


def _load_system_prompt() -> str:
    if SYSTEM_PROMPT_FILE.exists():
        return SYSTEM_PROMPT_FILE.read_text()
    return _DEFAULT_SYSTEM


def _build_messages(history, user_input, memory_context, attachments=None):
    system = _load_system_prompt()
    if memory_context:
        system += f"\n\n{memory_context}"
    msgs = [{"role": "system", "content": system}]
    msgs += history
    if attachments:
        images = [a["data"] for a in attachments if a.get("type") == "image"]
        text_parts = [
            f"[Fichier: {a['name']}]\n```\n{a['content']}\n```"
            for a in attachments if a.get("type") == "text"
        ]
        content = ("\n\n".join(text_parts) + "\n\n" + user_input).strip() if text_parts else user_input
        msg: dict = {"role": "user", "content": content}
        if images:
            msg["images"] = images
        msgs.append(msg)
    else:
        msgs.append({"role": "user", "content": user_input})
    return msgs


async def _generate_title(user_msg: str, assistant_msg: str) -> str:
    """Génère un titre court pour la session via Ollama."""
    # Prompt conçu pour obtenir uniquement un titre court en 1 ligne
    prompt = (
        "/no_think\n"
        f"Résume en 4 mots maximum (français, pas de ponctuation finale): {user_msg[:120]}\n"
        "Titre:"
    )
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": settings.FAST_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "think": False,
                    "options": {"num_predict": 25, "temperature": 0.1},
                },
            )
            if resp.status_code == 200:
                raw = resp.json().get("response", "").strip()
                # Strip think tags en fallback
                title = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
                title = title.replace('"', "").replace("'", "").strip(" :-")
                for line in title.splitlines():
                    line = line.strip(" :-")
                    if line and len(line) > 2:
                        return line[:60]
    except Exception:
        pass
    return ""


async def _ws_reader(websocket: WebSocket, queue: asyncio.Queue):
    try:
        while True:
            msg = await websocket.receive_text()
            await queue.put(msg)
    except Exception:
        await queue.put(None)


async def _exec_streaming(cmd: str, websocket: WebSocket, ws_queue: asyncio.Queue,
                          sudo_password: str | None = None):
    """Lance cmd en PTY, stream la sortie via WS, route stdin depuis ws_queue."""

    if not cmd.strip():
        return

    await websocket.send_text(json.dumps({"type": "shell_start", "command": cmd}))

    # Queue dédiée pour les entrées PTY (stdin)
    stdin_q: asyncio.Queue[str] = asyncio.Queue()

    # Tâche qui draine ws_queue pour trouver des shell_stdin pendant l'exécution
    async def _route_stdin():
        while True:
            try:
                raw = await asyncio.wait_for(ws_queue.get(), timeout=0.2)
                if raw is None:
                    return
                p = json.loads(raw)
                if p.get("type") == "shell_stdin":
                    await stdin_q.put(p.get("text", ""))
                elif p.get("type") == "stop":
                    return
                # Les autres messages (chat normal) sont ignorés pendant l'exécution
                # (ils seront redemandés par l'utilisateur après)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                return
            except Exception:
                continue

    routing_task = asyncio.create_task(_route_stdin())

    try:
        needs_sudo_retry = False
        async for event in stream_pty(cmd, sudo_password=sudo_password, stdin_queue=stdin_q):

            if event["type"] == "needs_sudo":
                # Demander le mot de passe au frontend
                await websocket.send_text(json.dumps({"type": "needs_sudo", "command": cmd}))
                # Attendre la réponse (via ws_queue, routée par _route_stdin — mais ici
                # on attend directement depuis ws_queue car on est hors du générateur)
                try:
                    raw = await asyncio.wait_for(ws_queue.get(), timeout=60.0)
                    if raw:
                        p = json.loads(raw)
                        if p.get("type") == "sudo_response":
                            needs_sudo_retry = True
                            await websocket.send_text(json.dumps({
                                "type": "shell_done", "command": cmd, "returncode": -1,
                                "error": "Relancement avec sudo..."
                            }))
                            # Relancer avec le mot de passe
                            routing_task.cancel()
                            await _exec_streaming(cmd, websocket, ws_queue, p.get("password"))
                            return
                except asyncio.TimeoutError:
                    await websocket.send_text(json.dumps({
                        "type": "shell_done", "command": cmd, "returncode": -1,
                        "error": "Timeout — mot de passe non fourni"
                    }))
                return

            elif event["type"] == "chunk":
                await websocket.send_text(json.dumps({
                    "type": "shell_chunk",
                    "command": cmd,
                    "text": event["text"],
                }))

            elif event["type"] == "waiting":
                # Le processus attend une entrée — signaler au frontend
                await websocket.send_text(json.dumps({
                    "type": "shell_waiting",
                    "command": cmd,
                }))

            elif event["type"] == "done":
                await websocket.send_text(json.dumps({
                    "type": "shell_done",
                    "command": cmd,
                    "returncode": event["returncode"],
                }))

            elif event["type"] == "error":
                await websocket.send_text(json.dumps({
                    "type": "shell_done",
                    "command": cmd,
                    "returncode": -1,
                    "error": event.get("message", "Erreur"),
                }))

    finally:
        routing_task.cancel()
        try:
            await routing_task
        except asyncio.CancelledError:
            pass


class ChatRequest(BaseModel):
    message: str
    task_type: str = "reason"
    session_id: str | None = None
    attachments: list | None = None


@router.post("/complete")
async def chat_complete(body: ChatRequest):
    session_id = body.session_id or create_session().id
    memory_context = await build_context_prefix(body.message)
    history = get_session_messages(session_id)
    messages = _build_messages(history, body.message, memory_context, body.attachments)
    await add_message(session_id, "user", body.message)

    full_response = ""
    async for token in stream_response(messages, body.task_type):
        full_response += token

    shell_results = []
    for cmd in EXEC_RE.findall(full_response):
        result = await execute_command(cmd.strip())
        shell_results.append({"command": cmd.strip(), "result": result})

    await add_message(session_id, "assistant", full_response)

    # Nommage auto si c'est le premier échange
    title = None
    if session_message_count(session_id) <= 2:
        title = await _generate_title(body.message, full_response)
        if title:
            update_session_title(session_id, title)

    return {
        "session_id": session_id,
        "model": select_model(body.task_type),
        "response": full_response,
        "shell_results": shell_results,
        "session_title": title,
    }


@router.websocket("/ws")
async def chat_ws(websocket: WebSocket):
    await websocket.accept()
    session_id = None
    is_new_session = True
    queue: asyncio.Queue = asyncio.Queue()
    reader = asyncio.create_task(_ws_reader(websocket, queue))

    try:
        while True:
            raw = await queue.get()
            if raw is None:
                break

            payload = json.loads(raw)
            msg_type = payload.get("type", "chat")

            # Messages de contrôle hors contexte
            if msg_type in ("stop", "ping", "shell_stdin", "sudo_response"):
                continue

            user_input = payload.get("message", "")
            task_type = payload.get("task_type", "reason")
            attachments = payload.get("attachments")

            if not user_input.strip() and not attachments:
                continue

            if not session_id:
                session_id = payload.get("session_id") or create_session().id
                is_new_session = True
                await websocket.send_text(json.dumps({"type": "session_id", "session_id": session_id}))
            elif payload.get("session_id") and payload["session_id"] != session_id:
                # Changement de session
                session_id = payload["session_id"]
                is_new_session = session_message_count(session_id) == 0

            memory_context = await build_context_prefix(user_input)
            history = get_session_messages(session_id)
            messages = _build_messages(history, user_input, memory_context, attachments)
            await add_message(session_id, "user", user_input)

            # ── Stream LLM ──────────────────────────────────────────────
            full_response = ""
            stopped = False

            async for token in stream_response(messages, task_type):
                try:
                    pending = queue.get_nowait()
                    if pending is None:
                        stopped = True
                        break
                    p = json.loads(pending)
                    if p.get("type") == "stop":
                        stopped = True
                        break
                    await queue.put(pending)
                except asyncio.QueueEmpty:
                    pass

                await websocket.send_text(json.dumps({"type": "token", "content": token}))
                full_response += token

            if stopped:
                await websocket.send_text(json.dumps({"type": "stopped"}))
                if full_response:
                    await add_message(session_id, "assistant", full_response + " [arrêté]")
                continue

            await add_message(session_id, "assistant", full_response)

            # ── Nommage automatique de la session (1er échange) ─────────
            if is_new_session and full_response:
                is_new_session = False
                asyncio.create_task(
                    _auto_name_session(session_id, user_input, full_response, websocket)
                )

            # ── Exécuter les [EXEC: ...] en streaming PTY ────────────────
            for cmd in EXEC_RE.findall(full_response):
                await _exec_streaming(cmd.strip(), websocket, queue)

            await websocket.send_text(json.dumps({"type": "done", "model": select_model(task_type)}))

    except WebSocketDisconnect:
        pass
    finally:
        reader.cancel()


async def _auto_name_session(session_id: str, user_msg: str, assistant_msg: str,
                              websocket: WebSocket):
    """Génère et applique un titre de session en arrière-plan."""
    title = await _generate_title(user_msg, assistant_msg)
    if title:
        update_session_title(session_id, title)
        try:
            await websocket.send_text(json.dumps({
                "type": "session_title",
                "session_id": session_id,
                "title": title,
            }))
        except Exception:
            pass
