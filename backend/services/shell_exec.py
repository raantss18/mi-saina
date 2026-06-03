import asyncio
import os
import re

from config import settings

DANGEROUS_PATTERNS = [
    r"rm\s+-rf\s+/",
    r"dd\s+if=",
    r"mkfs\.",
    r":\(\)\s*\{.*\}",  # fork bomb
    r">\s+/dev/sd",
]


def is_dangerous(cmd: str) -> bool:
    return any(re.search(p, cmd) for p in DANGEROUS_PATTERNS)


def needs_sudo(cmd: str) -> bool:
    return cmd.strip().startswith("sudo") or any(
        kw in cmd for kw in ["pacman -S", "systemctl enable", "chmod 777", "chown root"]
    )


async def execute_command(cmd: str, sudo_password: str | None = None) -> dict:
    if is_dangerous(cmd):
        return {"status": "blocked", "output": "Commande bloquée : pattern dangereux détecté."}

    if needs_sudo(cmd) and not sudo_password:
        return {"status": "needs_sudo", "output": "Cette commande requiert le mot de passe root."}

    env = os.environ.copy()
    actual_cmd = cmd
    if sudo_password and needs_sudo(cmd):
        clean = cmd.lstrip("sudo").strip()
        actual_cmd = f"echo {repr(sudo_password)} | sudo -S {clean}"

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
