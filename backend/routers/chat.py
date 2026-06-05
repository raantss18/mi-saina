import asyncio
import re
import shlex
from pathlib import Path
import json

import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from config import settings
from services.llm import stream_response, select_model
from services.memory import (
    add_message, get_session_messages, build_context_prefix, create_session,
    update_session_title, session_message_count,
)
from services.shell_stream import stream_pty, is_destructive
from services.planner import should_plan, plan_task, fit_budget, reference_hint
from services import diagnostics, userctx
from services.sysinfo import system_block

router = APIRouter()

EXEC_RE = re.compile(r'\[EXEC:\s*(.*?)\]', re.DOTALL)
REMEMBER_RE = re.compile(r'\[REMEMBER:\s*(.*?)\]', re.DOTALL)
CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
SYSTEM_PROMPT_FILE = CONFIG_DIR / "system_prompt.txt"

_DEFAULT_SYSTEM = "Tu es mi-saina, un assistant IA local expert avec accès complet à la machine Linux."


def _load_system_prompt() -> str:
    base = SYSTEM_PROMPT_FILE.read_text() if SYSTEM_PROMPT_FILE.exists() else _DEFAULT_SYSTEM
    # Infos matériel/distribution détectées à l'exécution (jamais versionnées)
    parts = [base, system_block()]
    ctx = userctx.context_block()      # contexte global + projet + profil utilisateur
    if ctx:
        parts.append(ctx)
    return "\n\n".join(parts)


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
                          sudo_password: str | None = None,
                          _started: bool = False) -> tuple[str, int, bool, dict]:
    """Lance cmd en PTY, stream la sortie via WS, route stdin depuis ws_queue.

    Retourne (sortie_capturée, returncode, stoppé, outcome) pour permettre à la
    boucle agentique de renvoyer le résultat au modèle (find → ouvrir, etc.).
    `outcome` croise code retour ET sortie (cf. diagnostics.assess_outcome) afin
    de repérer les échecs logiques renvoyant pourtant 0.
    `_started` : interne — évite de recréer un bloc terminal lors du relancement sudo.
    """

    if not cmd.strip():
        return "", 0, False, {"status": "success", "rc": 0, "logical": False, "reason": None}

    captured: list[str] = []
    returncode = -1
    outcome: dict = {"status": "success", "rc": 0, "logical": False, "reason": None}
    stopped = False
    diag_buffer = ""           # fenêtre glissante pour la vigilance temps réel
    diag_seen: set[str] = set()

    # Un seul bloc terminal, même après saisie du mot de passe sudo (pas de doublon)
    if not _started:
        await websocket.send_text(json.dumps({"type": "shell_start", "command": cmd}))

    # Queues dédiées : stdin interactif du PTY et réponse au prompt sudo.
    # Séparer la réponse sudo évite que _route_stdin "mange" le mot de passe.
    stdin_q: asyncio.Queue[str] = asyncio.Queue()
    sudo_q: asyncio.Queue[dict] = asyncio.Queue()
    choice_q: asyncio.Queue[dict] = asyncio.Queue()   # réponse au choix d'ouverture
    stop_event = asyncio.Event()   # « stop » → tue le processus du terminal

    # Tâche qui draine ws_queue pour router shell_stdin / sudo_response pendant l'exécution
    async def _route_stdin():
        while True:
            try:
                raw = await asyncio.wait_for(ws_queue.get(), timeout=0.2)
                if raw is None:
                    stop_event.set()
                    return
                p = json.loads(raw)
                if p.get("type") == "shell_stdin":
                    await stdin_q.put(p.get("text", ""))
                elif p.get("type") == "sudo_response":
                    await sudo_q.put(p)
                elif p.get("type") == "open_choice_response":
                    await choice_q.put(p)
                elif p.get("type") == "stop":
                    stop_event.set()    # signale stream_pty pour tuer le process
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
        async for event in stream_pty(cmd, sudo_password=sudo_password,
                                      stdin_queue=stdin_q, stop_event=stop_event):

            if event["type"] == "needs_sudo":
                # Demander le mot de passe au frontend.
                # La réponse arrive via sudo_q, alimentée par _route_stdin (pas de race).
                await websocket.send_text(json.dumps({"type": "needs_sudo", "command": cmd}))
                # Le PTY a rendu la main (générateur terminé) : on attend le mot de
                # passe MAIS on doit aussi pouvoir être interrompu par un « stop »
                # ou une déconnexion. _route_stdin met stop_event dans les deux cas.
                get_pw = asyncio.create_task(sudo_q.get())
                on_stop = asyncio.create_task(stop_event.wait())
                done_set, _ = await asyncio.wait(
                    {get_pw, on_stop}, timeout=120.0,
                    return_when=asyncio.FIRST_COMPLETED)
                for t in (get_pw, on_stop):
                    if not t.done():
                        t.cancel()

                if on_stop in done_set:
                    # Stop / déconnexion pendant l'attente du mot de passe.
                    await websocket.send_text(json.dumps({
                        "type": "shell_done", "command": cmd, "returncode": -1,
                        "status": "stopped", "logical_failure": False,
                        "status_reason": "Arrêté pendant l'attente du mot de passe",
                    }))
                    return "", -1, True, {"status": "failure", "rc": -1,
                                          "logical": False,
                                          "reason": "Arrêté pendant l'attente du mot de passe"}

                if get_pw in done_set:
                    p = get_pw.result()
                    # Relancer avec le mot de passe (le routing actuel est arrêté
                    # puis recréé par l'appel récursif).
                    routing_task.cancel()
                    return await _exec_streaming(cmd, websocket, ws_queue,
                                                 p.get("password"), _started=True)

                # Ni stop ni mot de passe → timeout.
                await websocket.send_text(json.dumps({
                    "type": "shell_done", "command": cmd, "returncode": -1,
                    "status": "failure", "logical_failure": False,
                    "status_reason": "Timeout — mot de passe non fourni",
                    "error": "Timeout — mot de passe non fourni"
                }))
                return "", -1, False, {"status": "failure", "rc": -1,
                                       "logical": False,
                                       "reason": "Timeout — mot de passe non fourni"}

            elif event["type"] == "open_choices":
                # Ouverture ambiguë : proposer une liste cliquable plutôt que choisir.
                await websocket.send_text(json.dumps({
                    "type": "open_choices", "command": cmd,
                    "candidates": event["candidates"],
                }))
                get_choice = asyncio.create_task(choice_q.get())
                on_stop = asyncio.create_task(stop_event.wait())
                done_set, _ = await asyncio.wait(
                    {get_choice, on_stop}, timeout=120.0,
                    return_when=asyncio.FIRST_COMPLETED)
                for t in (get_choice, on_stop):
                    if not t.done():
                        t.cancel()

                chosen = get_choice.result().get("path") if get_choice in done_set else None
                if not chosen:
                    # Stop / annulation / timeout → ne rien ouvrir.
                    reason = ("Arrêté" if on_stop in done_set
                              else "Aucun fichier choisi")
                    await websocket.send_text(json.dumps({
                        "type": "shell_done", "command": cmd, "returncode": -1,
                        "status": "stopped", "logical_failure": False,
                        "status_reason": reason,
                    }))
                    return "", -1, (on_stop in done_set), {
                        "status": "failure", "rc": -1, "logical": False, "reason": reason}

                # Relancer l'ouverture sur le fichier choisi (chemin existant).
                routing_task.cancel()
                new_cmd = f"xdg-open {shlex.quote(chosen)}"
                return await _exec_streaming(new_cmd, websocket, ws_queue, _started=True)

            elif event["type"] == "chunk":
                captured.append(event["text"])
                await websocket.send_text(json.dumps({
                    "type": "shell_chunk",
                    "command": cmd,
                    "text": event["text"],
                }))
                # ── Vigilance temps réel : détecter un problème connu dans la sortie ──
                diag_buffer = (diag_buffer + event["text"])[-1000:]
                for d in diagnostics.diagnose(diag_buffer):
                    if d["label"] in diag_seen:
                        continue
                    diag_seen.add(d["label"])
                    await websocket.send_text(json.dumps({
                        "type": "diagnostic", "command": cmd,
                        "label": d["label"], "message": d["message"], "fix": d["fix"],
                    }))

            elif event["type"] == "waiting":
                # Le processus attend une entrée — signaler au frontend
                await websocket.send_text(json.dumps({
                    "type": "shell_waiting",
                    "command": cmd,
                }))

            elif event["type"] == "done":
                returncode = event["returncode"]
                # Statut fin : croiser code retour ET sortie (échec logique malgré rc=0)
                outcome = diagnostics.assess_outcome("".join(captured), returncode)
                await websocket.send_text(json.dumps({
                    "type": "shell_done",
                    "command": cmd,
                    "returncode": event["returncode"],
                    "status": outcome["status"],
                    "logical_failure": outcome["logical"],
                    "status_reason": outcome["reason"],
                }))

            elif event["type"] == "error":
                returncode = -1
                captured.append(event.get("message", "Erreur"))
                outcome = {"status": "failure", "rc": -1, "logical": False,
                           "reason": event.get("message", "Erreur")}
                await websocket.send_text(json.dumps({
                    "type": "shell_done",
                    "command": cmd,
                    "returncode": -1,
                    "status": "failure",
                    "logical_failure": False,
                    "status_reason": event.get("message", "Erreur"),
                    "error": event.get("message", "Erreur"),
                }))

    finally:
        routing_task.cancel()
        try:
            await routing_task
        except asyncio.CancelledError:
            pass

    return "".join(captured), returncode, stop_event.is_set(), outcome


_MAX_FEEDBACK_CHARS = 4000  # tronquage de la sortie renvoyée au modèle


def _slugify(text: str, max_words: int = 4) -> str:
    """Nom court (kebab-case) pour une compétence, dérivé de la demande."""
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())[:max_words]
    slug = "-".join(words)[:32].strip("-")
    return slug or "tache"


async def _await_confirm(cmd: str, websocket: WebSocket, queue: asyncio.Queue,
                         approve_all: dict | None = None) -> bool:
    """Demande à l'utilisateur d'approuver une commande avant de l'exécuter.

    `approve_all` : conteneur mutable partagé sur tout le tour. Si l'utilisateur a
    cliqué « Tout valider », `approve_all["on"]` passe à True et les commandes
    suivantes du tour sont approuvées sans nouvelle fenêtre.

    Retourne True si approuvée, False si refusée / déconnecté / stop.
    """
    if approve_all and approve_all.get("on"):
        return True
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
            approved = bool(p.get("approved"))
            # « Tout valider » → mémoriser pour les commandes suivantes du tour
            if approved and p.get("all") and approve_all is not None:
                approve_all["on"] = True
            return approved
        if t == "stop":
            return False
        # autres messages ignorés pendant l'attente de confirmation


def _format_exec_feedback(results: list[tuple[str, str, int]]) -> str:
    """Met en forme la sortie des commandes pour la renvoyer au modèle."""
    parts = []
    diags: list[dict] = []
    outcome_notes: list[str] = []
    for cmd, out, rc in results:
        out = out.strip()
        diags += diagnostics.diagnose(out)
        note = diagnostics.format_outcome_for_model(diagnostics.assess_outcome(out, rc))
        if note:
            outcome_notes.append(note)
        if len(out) > _MAX_FEEDBACK_CHARS:
            out = out[:_MAX_FEEDBACK_CHARS] + "\n[…sortie tronquée…]"
        parts.append(f"$ {cmd}\n(code retour: {rc})\n{out or '(aucune sortie)'}")
    body = "\n\n".join(parts)
    if outcome_notes:
        body += "\n\n" + "\n".join(outcome_notes)
    diag_text = diagnostics.format_for_model(diags)
    if diag_text:
        body += "\n\n" + diag_text
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


def _drain_redirects(queue: asyncio.Queue) -> list[str]:
    """Récupère sans bloquer les messages chat envoyés PENDANT la tâche (redirection).
    Les messages de contrôle (stop, etc.) sont remis dans la file."""
    texts, keep = [], []
    while True:
        try:
            raw = queue.get_nowait()
        except asyncio.QueueEmpty:
            break
        if raw is None:
            keep.append(raw)
            continue
        try:
            p = json.loads(raw)
        except Exception:
            continue
        if p.get("type", "chat") == "chat" and p.get("message", "").strip():
            texts.append(p["message"].strip())
        else:
            keep.append(raw)
    for r in keep:
        queue.put_nowait(r)
    return texts


async def _inject_redirects(redirects: list[str], messages: list, websocket: WebSocket,
                            session_id: str, persist: bool) -> None:
    """Injecte les redirections dans le contexte de la tâche en cours."""
    for tx in redirects:
        await websocket.send_text(json.dumps({"type": "redirect_ack", "text": tx}))
        if persist:
            await add_message(session_id, "user", tx)
        messages.append({"role": "user",
                         "content": f"[NOUVELLE INSTRUCTION DE L'UTILISATEUR — prends-la en compte maintenant] {tx}"})


async def _run_agent_loop(messages: list, task_type: str, websocket: WebSocket,
                          queue: asyncio.Queue, session_id: str,
                          persist: bool = True,
                          approve_all: dict | None = None) -> tuple[bool, str, list[tuple[str, int]]]:
    """Boucle agentique sur `messages` (modèle → commandes → résultat → modèle).

    Retourne (stoppé, dernière_réponse, commandes_exécutées[(cmd, rc)]).
    `persist=False` pour un sous-agent à contexte éphémère.
    `approve_all` : conteneur partagé pour le « Tout valider » du tour.
    """
    stopped = False
    last = ""
    executed: list[tuple[str, int]] = []
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

        # Mémorisation durable d'une préférence/fait → profil utilisateur
        for fact in REMEMBER_RE.findall(full_response):
            fact = fact.strip()
            if fact:
                userctx.append_profile(fact)
                await websocket.send_text(json.dumps({"type": "memory_saved", "fact": fact}))

        cmds = [c.strip() for c in EXEC_RE.findall(full_response) if c.strip()]
        if not cmds:
            # Pas de commande : si l'utilisateur a redirigé pendant la réponse, on continue
            redirects = _drain_redirects(queue)
            if redirects:
                await _inject_redirects(redirects, messages, websocket, session_id, persist)
                continue
            break

        results: list[tuple[str, str, int]] = []
        declined = False
        for cmd in cmds:
            # Confirmation selon le mode : jamais / tout / seulement les commandes risquées.
            # (Les commandes root sont de toute façon validées par le mot de passe sudo.)
            need_confirm = settings.CONFIRM_MODE == "all" or (
                settings.CONFIRM_MODE == "risky" and is_destructive(cmd))
            if need_confirm and not await _await_confirm(cmd, websocket, queue, approve_all):
                await websocket.send_text(json.dumps({"type": "exec_declined", "command": cmd}))
                results.append((cmd, "(commande refusée par l'utilisateur)", -1))
                declined = True
                continue
            out, rc, was_stopped, outcome = await _exec_streaming(cmd, websocket, queue)
            results.append((cmd, out, rc))
            # Statut effectif : un échec logique (rc=0 mais sortie en erreur) compte
            # comme un échec pour l'apprentissage de compétences et le statut de tâche.
            effective_rc = 0 if outcome["status"] == "success" else (rc or 1)
            executed.append((cmd, effective_rc))
            if was_stopped:
                # L'utilisateur a coupé l'exécution → on arrête toute la tâche
                stopped = True
                await websocket.send_text(json.dumps({"type": "stopped"}))
                break

        if stopped or step == settings.MAX_AGENT_STEPS - 1 or declined:
            break

        messages.append({"role": "user", "content": _format_exec_feedback(results)})
        # Redirection envoyée pendant l'exécution → prise en compte à l'étape suivante
        redirects = _drain_redirects(queue)
        if redirects:
            await _inject_redirects(redirects, messages, websocket, session_id, persist)

    return stopped, last, executed


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
            if msg_type in ("stop", "ping", "shell_stdin", "sudo_response", "exec_response", "open_choice_response"):
                continue

            user_input = payload.get("message", "")
            task_type = payload.get("task_type", "reason")
            attachments = payload.get("attachments")
            skill_name = payload.get("skill")   # compétence ayant déclenché ce message (si applicable)

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
            executed: list[tuple[str, int]] = []
            approve_all = {"on": False}   # « Tout valider » : partagé sur tout le tour
            if should_plan(user_input):
                await websocket.send_text(json.dumps({"type": "planning"}))
                subtasks = await plan_task(user_input)
            else:
                subtasks = [user_input]

            if len(subtasks) > 1:
                await websocket.send_text(json.dumps({"type": "plan", "subtasks": subtasks}))
                system_prompt = _load_system_prompt()
                scratch = ""           # mémoire partagée minuscule entre sous-tâches
                prev_cmds: list[str] = []   # commandes réussies (pour résoudre les référents)
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
                    # Référent pendant (« compile-le ») → pointer le dernier artefact
                    hint = reference_hint(sub, prev_cmds)
                    if hint:
                        sub_msgs.append({"role": "user", "content": hint})
                    sub_msgs.append({"role": "user",
                                     "content": f"[SOUS-TÂCHE {i + 1}/{len(subtasks)}] {sub}"})
                    stopped, last, ex = await _run_agent_loop(
                        sub_msgs, task_type, websocket, queue, session_id, persist=True,
                        approve_all=approve_all)
                    executed += ex
                    if stopped:
                        break
                    # Scratch enrichi : résumé textuel + commandes concrètes exécutées
                    # (ce sont elles qui portent les chemins/artefacts réutilisables).
                    done_cmds = [c for c, rc in ex if rc == 0]
                    prev_cmds += done_cmds
                    cmd_note = ("\n  ↳ commandes : " + " ; ".join(done_cmds[-3:])) if done_cmds else ""
                    scratch = (scratch + f"- {sub} → {last.strip()[:200]}{cmd_note}\n")[-1800:]
            else:
                # Chemin simple : contexte complet (avec mémoire), élagué au budget
                messages = _build_messages(history, subtasks[0], memory_context, attachments)
                stopped, _, executed = await _run_agent_loop(
                    messages, task_type, websocket, queue, session_id, persist=True,
                    approve_all=approve_all)

            # ── Auto-correction d'une compétence : la compétence a échoué puis été corrigée ──
            if (skill_name and not stopped and executed
                    and any(rc != 0 for _, rc in executed)
                    and any(rc == 0 for _, rc in executed)):
                await websocket.send_text(json.dumps({
                    "type": "skill_update_suggestion",
                    "name": skill_name,
                    "description": user_input[:80],
                    "commands": [c for c, rc in executed if rc == 0],
                }))
            # ── Compétence apprise : proposer d'enregistrer une nouvelle tâche réussie ──
            elif not skill_name and not stopped and len(executed) >= 2 and all(rc == 0 for _, rc in executed):
                await websocket.send_text(json.dumps({
                    "type": "skill_suggestion",
                    "name": _slugify(user_input),
                    "description": user_input[:80],
                    "commands": [c for c, _ in executed],
                }))

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
