"""
Exécution shell en PTY (pseudo-terminal) avec streaming temps réel.
Le processus croit être dans un vrai terminal → pas de buffering,
prompts [Y/n] visibles, barres de progression fonctionnelles.
"""

import asyncio
import fcntl
import os
import pty
import re
import struct
import termios

ANSI_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

DANGEROUS_PATTERNS = [
    r"rm\s+-rf\s+/[^/]",
    r"dd\s+if=",
    r"mkfs\.",
    r":\(\)\s*\{.*\}",
    r">\s+/dev/sd",
]


def _is_dangerous(cmd: str) -> bool:
    return any(re.search(p, cmd) for p in DANGEROUS_PATTERNS)


def _needs_sudo(cmd: str) -> bool:
    return cmd.strip().startswith("sudo") or any(
        kw in cmd for kw in [
            "pacman -S", "pacman -R", "pacman -U", "pacman -D",
            "systemctl enable", "systemctl disable",
            "chmod 777", "chown root",
        ]
    )


async def stream_pty(
    cmd: str,
    sudo_password: str | None = None,
    timeout: int = 600,
    cols: int = 120,
    rows: int = 40,
    stdin_queue: asyncio.Queue | None = None,
):
    """
    Exécute cmd dans un PTY et yield des événements :
      {"type": "chunk",     "text": str}
      {"type": "waiting"}                  — process semble attendre input
      {"type": "done",      "returncode": int}
      {"type": "error",     "message": str}
      {"type": "needs_sudo","command": str}
    """
    if _is_dangerous(cmd):
        yield {"type": "error", "message": "⛔ Commande bloquée : pattern dangereux."}
        return

    if _needs_sudo(cmd) and not sudo_password:
        yield {"type": "needs_sudo", "command": cmd}
        return

    # Construire la commande
    actual_cmd = cmd
    if sudo_password and _needs_sudo(cmd):
        clean = re.sub(r'^sudo\s+', '', cmd).strip()
        actual_cmd = f"sudo -S {clean}"

    _stdin_q = stdin_queue if stdin_queue is not None else asyncio.Queue()

    master, slave = pty.openpty()
    try:
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', rows, cols, 0, 0))
    except Exception:
        pass

    env = os.environ.copy()
    env.update({
        "TERM": "xterm-256color",
        "COLUMNS": str(cols),
        "LINES": str(rows),
        "HOME": os.path.expanduser("~"),
        "LANG": "fr_FR.UTF-8",
    })

    proc = await asyncio.create_subprocess_shell(
        actual_cmd,
        stdin=slave,
        stdout=slave,
        stderr=slave,
        env=env,
        start_new_session=True,
    )
    os.close(slave)

    # Rendre le master non-bloquant
    flags = fcntl.fcntl(master, fcntl.F_GETFL)
    fcntl.fcntl(master, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    # Envoyer le mot de passe sudo (~0.3s après le démarrage)
    if sudo_password and _needs_sudo(cmd):
        await asyncio.sleep(0.4)
        try:
            os.write(master, (sudo_password + "\n").encode())
        except OSError:
            pass

    elapsed = 0.0
    last_output_at = asyncio.get_event_loop().time()
    idle_warned = False

    try:
        while True:
            await asyncio.sleep(0.04)
            elapsed += 0.04

            if elapsed > timeout:
                try:
                    proc.kill()
                except Exception:
                    pass
                yield {"type": "chunk", "text": f"\n[⏱ Timeout après {timeout}s]\n"}
                break

            # ── Lire la sortie du PTY ──────────────────────────────────
            got_data = False
            try:
                data = os.read(master, 8192)
                if data:
                    text = ANSI_RE.sub("", data.decode("utf-8", errors="replace"))
                    yield {"type": "chunk", "text": text}
                    last_output_at = asyncio.get_event_loop().time()
                    idle_warned = False
                    got_data = True
            except BlockingIOError:
                pass
            except OSError:
                # Master fermé → processus terminé
                break

            # ── Détecter attente input (1.5s sans sortie) ─────────────
            now = asyncio.get_event_loop().time()
            if (not got_data
                    and (now - last_output_at) > 1.5
                    and not idle_warned
                    and proc.returncode is None):
                idle_warned = True
                yield {"type": "waiting"}

            # ── Injecter stdin depuis la queue ────────────────────────
            try:
                user_input = _stdin_q.get_nowait()
                os.write(master, (user_input + "\n").encode())
                yield {"type": "chunk", "text": f"{user_input}\n"}
                last_output_at = asyncio.get_event_loop().time()
                idle_warned = False
            except asyncio.QueueEmpty:
                pass

            # ── Processus terminé ? ────────────────────────────────────
            if proc.returncode is not None:
                await asyncio.sleep(0.15)
                try:
                    rest = os.read(master, 8192)
                    if rest:
                        yield {"type": "chunk",
                               "text": ANSI_RE.sub("", rest.decode("utf-8", errors="replace"))}
                except (OSError, BlockingIOError):
                    pass
                break

    finally:
        try:
            os.close(master)
        except OSError:
            pass

    try:
        await asyncio.wait_for(proc.wait(), timeout=5)
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except Exception:
            pass

    rc = proc.returncode if proc.returncode is not None else -1
    yield {"type": "done", "returncode": rc}
