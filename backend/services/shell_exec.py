import asyncio
import os
import re
import shlex

from config import settings
# Détection root / nettoyage partagés avec le chemin streaming (PTY)
from services.shell_stream import (
    needs_root as needs_sudo,
    sanitize,
    _is_aur_helper,
    _strip_leading_sudo,
)

DANGEROUS_PATTERNS = [
    r"rm\s+-rf\s+/",
    r"dd\s+if=",
    r"mkfs\.",
    r":\(\)\s*\{.*\}",  # fork bomb
    r">\s+/dev/sd",
]


def is_dangerous(cmd: str) -> bool:
    return any(re.search(p, cmd) for p in DANGEROUS_PATTERNS)


async def execute_command(cmd: str, sudo_password: str | None = None) -> dict:
    if is_dangerous(cmd):
        return {"status": "blocked", "output": "Commande bloquée : pattern dangereux détecté."}

    if needs_sudo(cmd) and not sudo_password:
        return {"status": "needs_sudo", "output": "Cette commande requiert le mot de passe root."}

    env = os.environ.copy()
    actual_cmd = sanitize(cmd)
    if sudo_password and needs_sudo(cmd):
        pw = shlex.quote(sudo_password)
        if _is_aur_helper(cmd):
            # Les aides AUR refusent sudo : amorcer le timestamp sudo puis lancer telle quelle.
            actual_cmd = f"echo {pw} | sudo -S -v && {sanitize(cmd)}"
        else:
            clean = _strip_leading_sudo(sanitize(cmd))
            actual_cmd = f"echo {pw} | sudo -S {clean}"

    try:
        proc = await asyncio.create_subprocess_shell(
            actual_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=settings.SHELL_TIMEOUT)
        return {"status": "ok", "returncode": proc.returncode, "output": stdout.decode(errors="replace")}
    except asyncio.TimeoutError:
        return {"status": "timeout", "output": f"Timeout après {settings.SHELL_TIMEOUT}s"}
    except Exception as e:
        return {"status": "error", "output": str(e)}
