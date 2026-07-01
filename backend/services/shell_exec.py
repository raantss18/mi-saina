import asyncio
import contextlib
import os
import signal

from config import settings
# Détection root / nettoyage partagés avec le chemin streaming (PTY)
from services.shell_stream import (
    needs_root as needs_sudo,
    sanitize,
    _is_aur_helper,
    _strip_leading_sudo,
    _is_dangerous,
)


def is_dangerous(cmd: str) -> bool:
    # Source unique : même liste de patterns que le chemin streaming (PTY).
    return _is_dangerous(cmd)


def _kill_tree(proc) -> None:
    """Tue le groupe de processus (la commande ET ses enfants), sans zombie."""
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except Exception:
        with contextlib.suppress(Exception):
            proc.kill()


async def execute_command(cmd: str, sudo_password: str | None = None) -> dict:
    if is_dangerous(cmd):
        return {"status": "blocked", "output": "Commande bloquée : pattern dangereux détecté."}

    if needs_sudo(cmd) and not sudo_password:
        return {"status": "needs_sudo", "output": "Cette commande requiert le mot de passe root."}

    actual_cmd = sanitize(cmd)
    stdin_data: bytes | None = None
    if sudo_password and needs_sudo(cmd):
        # Le mot de passe ne doit JAMAIS apparaître dans la ligne de commande :
        # /proc/<pid>/cmdline est lisible par tous les processus locaux. Il est
        # écrit sur stdin et lu par `sudo -S` (-p '' : pas de prompt parasite).
        stdin_data = (sudo_password + "\n").encode()
        if _is_aur_helper(cmd):
            # Les aides AUR refusent sudo : amorcer le timestamp sudo puis lancer telle quelle.
            actual_cmd = f"sudo -S -p '' -v && {sanitize(cmd)}"
        else:
            clean = _strip_leading_sudo(sanitize(cmd))
            actual_cmd = f"sudo -S -p '' {clean}"

    try:
        proc = await asyncio.create_subprocess_shell(
            actual_cmd,
            stdin=asyncio.subprocess.PIPE if stdin_data else asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=os.environ.copy(),
            start_new_session=True,   # groupe dédié → tuable proprement au timeout
        )
    except Exception as e:
        return {"status": "error", "output": str(e)}

    try:
        stdout, _ = await asyncio.wait_for(
            proc.communicate(stdin_data), timeout=settings.SHELL_TIMEOUT)
        return {"status": "ok", "returncode": proc.returncode, "output": stdout.decode(errors="replace")}
    except asyncio.TimeoutError:
        # Sans kill, la commande continuait de tourner indéfiniment en arrière-plan.
        _kill_tree(proc)
        with contextlib.suppress(Exception):
            await proc.wait()
        return {"status": "timeout", "output": f"Timeout après {settings.SHELL_TIMEOUT}s"}
    except Exception as e:
        _kill_tree(proc)
        return {"status": "error", "output": str(e)}
