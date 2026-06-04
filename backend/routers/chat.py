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
from services.planner import should_plan, plan_task, fit_budget

router = APIRouter()

EXEC_RE = re.compile(r'\[EXEC:\s*(.*?)\]', re.DOTALL)
CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
SYSTEM_PROMPT_FILE = CONFIG_DIR / "system_prompt.txt"

_DEFAULT_SYSTEM = "Tu es mi-saina, un assistant IA local expert avec accès complet à la machine Linux."


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
                          sudo_password: str | None = None) -> tuple[str, int]:
    """Lance cmd en PTY, stream la sortie via WS, route stdin depuis ws_queue.

    Retourne (sortie_capturée, returncode) pour permettre à la boucle agentique
    de renvoyer le résultat au modèle (find → ouvrir, etc.).
    """

    if not cmd.strip():
        return "", 0

    captured: list[str] = []
    returncode = -1

    await websocket.send_text(json.dumps({"type": "shell_start", "command": cmd}))

    # Queues dédiées : stdin interactif du PTY et réponse au prompt sudo.
    # Séparer la réponse sudo évite que _route_stdin "mange" le mot de passe.
    stdin_q: asyncio.Queue[str] = asyncio.Queue()
    sudo_q: asyncio.Queue[dict] = asyncio.Queue()

    # Tâche qui draine ws_queue pour router shell_stdin / sudo_response pendant l'exécution
    async def _route_stdin():
        while True:
            try:
                raw = await asyncio.wait_for(ws_queue.get(), timeout=0.2)
                if raw is None:
                    return
                p = json.loads(raw)
                if p.get("type") == "shell_stdin":
                    await stdin_q.put(p.get("text", ""))
                elif p.get("type") == "sudo_response":
                    await sudo_q.put(p)
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
        async for event in stream_pty(cmd, sudo_password=sudo_password, stdin_queue=stdin_q):

            if event["type"] == "needs_sudo":
                # Demander le mot de passe au frontend.
                # La réponse arrive via sudo_q, alimentée par _route_stdin (pas de race).
                await websocket.send_text(json.dumps({"type": "needs_sudo", "command": cmd}))
                try:
                    p = await asyncio.wait_for(sudo_q.get(), timeout=120.0)
                    # Relancer avec le mot de passe (le routing actuel est arrêté
                    # puis recréé par l'appel récursif).
                    routing_task.cancel()
                    return await _exec_streaming(cmd, websocket, ws_queue, p.get("password"))
                except asyncio.TimeoutError:
                    await websocket.send_text(json.dumps({
                        "type": "shell_done", "command": cmd, "returncode": -1,
                        "error": "Timeout — mot de passe non fourni"
                    }))
                return "", -1

            elif event["type"] == "chunk":
                captured.append(event["text"])
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
                returncode = event["returncode"]
                await websocket.send_text(json.dumps({
                    "type": "shell_done",
                    "command": cmd,
                    "returncode": event["returncode"],
                }))

            elif event["type"] == "error":
                returncode = -1
                captured.append(event.get("message", "Erreur"))
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

    return "".join(captured), returncode


_MAX_FEEDBACK_CHARS = 4000  # tronquage de la sortie renvoyée au modèle


async def _await_confirm(cmd: str, websocket: WebSocket, queue: asyncio.Queue) -> bool:
    """Demande à l'utilisateur d'approuver une commande avant de l'exécuter.

    Retourne True si approuvée, False si refusée / déconnecté / stop.
    """
    await websocket.send_text(json.dumps({"type": "confirm_exec", "command": cmd}))
    while True:
        raw = await queue.get()
        if raw is None:
            return False
        try:
            p = json.loads(raw)
        except Exception:
            continue
        t = p.get("type")
        if t == "exec_response":
            return bool(p.get("approved"))
        if t == "stop":
            return False
        # autres messages ignorés pendant l'attente de confirmation


def _format_exec_feedback(results: list[tuple[str, str, int]]) -> str:
    """Met en forme la sortie des commandes pour la renvoyer au modèle."""
    parts = []
    for cmd, out, rc in results:
        out = out.strip()
        if len(out) > _MAX_FEEDBACK_CHARS:
            out = out[:_MAX_FEEDBACK_CHARS] + "\n[…sortie tronquée…]"
        parts.append(f"$ {cmd}\n(code retour: {rc})\n{out or '(aucune sortie)'}")
    body = "\n\n".join(parts)
    return (
        "[RÉSULTAT DES COMMANDES EXÉCUTÉES]\n" + body +
        "\n\n[INSTRUCTION] Au vu de ces résultats, poursuis la tâche. S'il reste une "
        "action à faire (par ex. ouvrir le fichier trouvé : [EXEC: xdg-open \"chemin complet\"]), "
        "fais-la maintenant. Si la tâche est terminée, donne ta réponse finale à l'utilisateur "
        "SANS nouvelle commande."
    )


async def _stream_llm(messages: list, task_type: str, websocket: WebSocket,
                      queue: asyncio.Queue) -> tuple[str, bool]:
    """Stream la réponse du modèle vers le WS. Retourne (texte_complet, stoppé)."""
    full_response = ""
    stopped = False
    # Garde-fou : tronquer le contexte pour ne pas saturer le modèle (petite VRAM)
    call_messages = fit_budget(messages)
    async for token in stream_response(call_messages, task_type):
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
    return full_response, stopped


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


async def _run_agent_loop(messages: list, task_type: str, websocket: WebSocket,
                          queue: asyncio.Queue, session_id: str,
                          persist: bool = True) -> tuple[bool, str]:
    """Boucle agentique sur `messages` (modèle → commandes → résultat → modèle).

    Retourne (stoppé, dernière_réponse). `persist=False` pour un sous-agent à
    contexte éphémère (on n'enregistre pas ses réponses en base).
    """
    stopped = False
    last = ""
    for step in range(settings.MAX_AGENT_STEPS):
        full_response, stopped = await _stream_llm(messages, task_type, websocket, queue)
        last = full_response

        if stopped:
            await websocket.send_text(json.dumps({"type": "stopped"}))
            if persist and full_response:
                await add_message(session_id, "assistant", full_response + " [arrêté]")
            break

        if persist:
            await add_message(session_id, "assistant", full_response)
        messages.append({"role": "assistant", "content": full_response})

        cmds = [c.strip() for c in EXEC_RE.findall(full_response) if c.strip()]
        if not cmds:
            break

        results: list[tuple[str, str, int]] = []
        declined = False
        for cmd in cmds:
            if settings.CONFIRM_BEFORE_EXEC and not await _await_confirm(cmd, websocket, queue):
                await websocket.send_text(json.dumps({"type": "exec_declined", "command": cmd}))
                results.append((cmd, "(commande refusée par l'utilisateur)", -1))
                declined = True
                continue
            out, rc = await _exec_streaming(cmd, websocket, queue)
            results.append((cmd, out, rc))

        if step == settings.MAX_AGENT_STEPS - 1 or declined:
            break

        messages.append({"role": "user", "content": _format_exec_feedback(results)})

    return stopped, last


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
            if msg_type in ("stop", "ping", "shell_stdin", "sudo_response", "exec_response"):
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
            await add_message(session_id, "user", user_input)

            # Nommage automatique de la session (basé sur le message utilisateur)
            if is_new_session:
                is_new_session = False
                asyncio.create_task(
                    _auto_name_session(session_id, user_input, "", websocket)
                )

            # ── Tâche lourde → planifier puis exécuter en sous-agents (contexte frais) ──
            stopped = False
            if should_plan(user_input):
                await websocket.send_text(json.dumps({"type": "planning"}))
                subtasks = await plan_task(user_input)
            else:
                subtasks = [user_input]

            if len(subtasks) > 1:
                await websocket.send_text(json.dumps({"type": "plan", "subtasks": subtasks}))
                system_prompt = _load_system_prompt()
                scratch = ""   # mémoire partagée minuscule entre sous-tâches
                for i, sub in enumerate(subtasks):
                    await websocket.send_text(json.dumps({
                        "type": "subtask_start", "index": i + 1,
                        "total": len(subtasks), "text": sub,
                    }))
                    # Contexte NEUF et minimal pour chaque sous-agent (peu de tokens)
                    sub_msgs = [{"role": "system", "content": system_prompt}]
                    if scratch:
                        sub_msgs.append({"role": "user",
                                         "content": "[CONTEXTE DES ÉTAPES PRÉCÉDENTES]\n" + scratch})
                    sub_msgs.append({"role": "user",
                                     "content": f"[SOUS-TÂCHE {i + 1}/{len(subtasks)}] {sub}"})
                    stopped, last = await _run_agent_loop(
                        sub_msgs, task_type, websocket, queue, session_id, persist=True)
                    if stopped:
                        break
                    scratch = (scratch + f"- {sub} → {last.strip()[:300]}\n")[-1500:]
            else:
                # Chemin simple : contexte complet (avec mémoire), élagué au budget
                messages = _build_messages(history, subtasks[0], memory_context, attachments)
                stopped, _ = await _run_agent_loop(
                    messages, task_type, websocket, queue, session_id, persist=True)

            if not stopped:
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
