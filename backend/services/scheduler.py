"""
Planificateur de tâches local (cron léger, 100 % local).

- Jobs persistés dans ~/.config/mi-saina/schedules.json.
- Une boucle de fond vérifie chaque minute les tâches dues et les exécute
  en mode HEADLESS (sans interface) : seules les commandes SÛRES sont lancées
  (ni root, ni destructrices — personne n'est là pour valider). Le résultat
  est enregistré comme une session « ⏰ <nom> » consultable plus tard.

Format de planification (champ `schedule`) :
  - "every:N"          → toutes les N minutes
  - "daily:HH:MM"      → chaque jour à HH:MM
  - "weekly:DOW:HH:MM" → chaque semaine (DOW : 0=lundi … 6=dimanche)
"""

import asyncio
import json
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from config import settings
from services.llm import complete
from services.shell_stream import stream_pty, needs_root, is_destructive
from services.memory import create_session, add_message, update_session_title

CONFIG_HOME = Path.home() / ".config" / "mi-saina"
JOBS_FILE = CONFIG_HOME / "schedules.json"

_EXEC_RE = re.compile(r"\[EXEC:\s*(.*?)\]", re.DOTALL)


# ── Persistance ────────────────────────────────────────────────────────────────
def load_jobs() -> list[dict]:
    try:
        return json.loads(JOBS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_jobs(jobs: list[dict]) -> None:
    CONFIG_HOME.mkdir(parents=True, exist_ok=True)
    JOBS_FILE.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")


def add_job(name: str, prompt: str, schedule: str) -> dict:
    jobs = load_jobs()
    job = {"id": str(uuid.uuid4())[:8], "name": name, "prompt": prompt,
           "schedule": schedule, "enabled": True, "last_run": None, "last_result": ""}
    jobs.append(job)
    save_jobs(jobs)
    return job


def delete_job(job_id: str) -> None:
    save_jobs([j for j in load_jobs() if j["id"] != job_id])


def toggle_job(job_id: str) -> None:
    jobs = load_jobs()
    for j in jobs:
        if j["id"] == job_id:
            j["enabled"] = not j.get("enabled", True)
    save_jobs(jobs)


# ── Calcul d'échéance ────────────────────────────────────────────────────────────
def _is_due(job: dict, now: datetime) -> bool:
    sched = job.get("schedule", "")
    last = job.get("last_run")
    last_dt = datetime.fromisoformat(last) if last else None
    try:
        if sched.startswith("every:"):
            n = int(sched.split(":", 1)[1])
            return last_dt is None or (now - last_dt) >= timedelta(minutes=n)
        if sched.startswith("daily:"):
            hh, mm = map(int, sched.split(":")[1:3])
            target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
            return now >= target and (last_dt is None or last_dt < target)
        if sched.startswith("weekly:"):
            _, dow, hh, mm = sched.split(":")
            dow, hh, mm = int(dow), int(hh), int(mm)
            if now.weekday() != dow:
                return False
            target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
            return now >= target and (last_dt is None or last_dt < target)
    except Exception:
        return False
    return False


# ── Exécution headless (sûre) ────────────────────────────────────────────────────
async def _run_safe_command(cmd: str) -> tuple[str, int]:
    out = []
    rc = -1
    async for ev in stream_pty(cmd, timeout=300):
        if ev["type"] == "chunk":
            out.append(ev["text"])
        elif ev["type"] == "done":
            rc = ev["returncode"]
        elif ev["type"] == "needs_sudo":
            return "(commande root ignorée en mode planifié)", -1
        elif ev["type"] == "error":
            out.append(ev.get("message", "")); rc = -1
    return "".join(out), rc


async def run_headless(prompt: str, max_steps: int = 4) -> str:
    """Exécute une tâche sans interface. Commandes root/destructrices ignorées."""
    from services.sysinfo import system_block
    system = ("Tu es mi-saina en mode planifié (sans interface). Exécute la tâche de "
              "façon autonome avec [EXEC: ...]. N'utilise que des commandes SÛRES (pas de "
              "sudo, pas de suppression). Termine par un court résumé.\n\n" + system_block())
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": prompt}]
    transcript = []
    for _ in range(max_steps):
        resp = await complete(messages, num_predict=600)
        transcript.append(resp)
        messages.append({"role": "assistant", "content": resp})
        cmds = [c.strip() for c in _EXEC_RE.findall(resp) if c.strip()]
        if not cmds:
            break
        feedback = []
        for cmd in cmds:
            if needs_root(cmd) or is_destructive(cmd):
                feedback.append(f"$ {cmd}\n(ignorée : nécessite une validation manuelle)")
                continue
            out, rc = await _run_safe_command(cmd)
            feedback.append(f"$ {cmd}\n(code {rc})\n{out.strip()[:1500]}")
        messages.append({"role": "user",
                         "content": "[RÉSULTATS]\n" + "\n\n".join(feedback) +
                                    "\n\nPoursuis ou conclus."})
    return "\n\n".join(t.strip() for t in transcript if t.strip())


async def _execute_job(job: dict) -> None:
    result = await run_headless(job["prompt"])
    # Enregistrer dans une session dédiée consultable
    sess = create_session()
    update_session_title(sess.id, f"⏰ {job['name']}")
    await add_message(sess.id, "user", f"[Tâche planifiée] {job['prompt']}")
    await add_message(sess.id, "assistant", result or "(aucune sortie)")
    # Mettre à jour le job
    jobs = load_jobs()
    for j in jobs:
        if j["id"] == job["id"]:
            j["last_run"] = datetime.now().isoformat(timespec="seconds")
            j["last_result"] = (result or "")[:500]
            j["last_session"] = sess.id
    save_jobs(jobs)


async def scheduler_loop() -> None:
    """Boucle de fond : vérifie les tâches dues chaque minute."""
    await asyncio.sleep(10)   # laisser le serveur démarrer
    while True:
        try:
            now = datetime.now()
            for job in load_jobs():
                if job.get("enabled", True) and _is_due(job, now):
                    await _execute_job(job)
        except Exception:
            pass
        await asyncio.sleep(60)
