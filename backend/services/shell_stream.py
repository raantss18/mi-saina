"""
Exécution shell en PTY (pseudo-terminal) avec streaming temps réel.
Le processus croit être dans un vrai terminal → pas de buffering,
prompts [Y/n] visibles, barres de progression fonctionnelles.

Gestion root (EndeavourOS / Arch) :
  - Détection des commandes nécessitant root : `sudo ...`, `pacman -S/-R/-U/-D`,
    aides AUR (`paru`, `yay`, ...), `systemctl enable/start/...`.
  - Le mot de passe est demandé à l'UI puis injecté quand sudo l'affiche
    (détection du prompt `[sudo] password for ...`). Fonctionne aussi bien
    pour `sudo pacman` que pour `paru` (qui escalade lui-même via sudo).
  - Les aides AUR ne doivent JAMAIS être lancées avec sudo → un `sudo` en
    préfixe est retiré.
  - Le flag `--noconfirm` est retiré : l'utilisateur garde la main sur le [Y/n].
"""

import asyncio
import difflib
import fcntl
import os
import pty
import re
import shlex
import struct
import termios

from services import apps

ANSI_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

# ── Applications graphiques (GUI) ─────────────────────────────────────────────
# Lancées détachées (setsid -f) pour rendre la main immédiatement : sinon la
# commande [EXEC:] resterait bloquée tant que la fenêtre est ouverte.
GUI_APPS = {
    # gestionnaires de fichiers
    "dolphin", "nautilus", "thunar", "nemo", "pcmanfm", "pcmanfm-qt", "caja", "krusader",
    # éditeurs / IDE
    "kate", "kwrite", "gedit", "gnome-text-editor", "code", "codium", "subl", "geany",
    # terminaux
    "konsole", "gnome-terminal", "alacritty", "kitty", "xterm", "foot",
    # navigateurs
    "firefox", "firefox-developer-edition", "chromium", "google-chrome",
    "google-chrome-stable", "brave", "brave-browser", "vivaldi-stable", "librewolf",
    # visionneuses / média
    "gwenview", "eog", "loupe", "okular", "evince", "vlc", "mpv", "celluloid", "spectacle",
    # bureautique / création
    "libreoffice", "soffice", "gimp", "inkscape", "krita", "blender", "obs",
    # divers
    "obsidian", "discord", "telegram-desktop", "spotify", "steam",
    "systemsettings", "plasma-systemmonitor", "ksysguard", "qbittorrent",
}
# Lanceurs génériques : ouvrent un chemin/URL dans l'appli associée
GUI_LAUNCHERS = {"xdg-open", "kde-open", "kde-open5", "gtk-launch", "kioclient",
                 "kioclient5", "exo-open", "gio"}

# Détection du prompt mot de passe de sudo (direct ou via paru/yay)
SUDO_PROMPT_RE = re.compile(r'\[sudo\] password for |\bpassword for .+?:|^\s*Password:\s*$', re.M)
# sudo signale un mauvais mot de passe → on autorise une nouvelle tentative
SUDO_RETRY_RE = re.compile(r'Sorry, try again|incorrect password attempt', re.I)

AUR_HELPERS = ("paru", "yay", "pikaur", "trizen", "pamac")

DANGEROUS_PATTERNS = [
    r"rm\s+-rf\s+/[^/]",
    r"dd\s+if=",
    r"mkfs\.",
    r":\(\)\s*\{.*\}",
    r">\s+/dev/sd",
]


def _is_dangerous(cmd: str) -> bool:
    return any(re.search(p, cmd) for p in DANGEROUS_PATTERNS)


def _strip_leading_sudo(cmd: str) -> str:
    return re.sub(r'^\s*sudo\s+', '', cmd.strip())


def _first_token(cmd: str) -> str:
    bare = _strip_leading_sudo(cmd)
    return bare.split()[0] if bare.split() else ""


def _is_aur_helper(cmd: str) -> bool:
    return _first_token(cmd) in AUR_HELPERS


def needs_root(cmd: str) -> bool:
    """La commande nécessite-t-elle des privilèges root ?"""
    s = cmd.strip()
    if s.startswith("sudo"):
        return True
    if _is_aur_helper(s):                       # paru/yay escaladent eux-mêmes
        return True
    if re.search(r'\bpacman\s+-{1,2}\w*[SRUD]', s):   # -S, -R, -U, -D, -Syu...
        return True
    if re.search(r'\bsystemctl\s+(?!--user\b)(enable|disable|start|stop|restart|reload|mask|unmask|daemon-reload)', s):
        return True
    if re.search(r'\b(chmod\s+777|chown\s+root|mkinitcpio|grub-mkconfig|usermod|useradd|timedatectl set)', s):
        return True
    return False


# Compat. avec l'ancien nom
_needs_sudo = needs_root


def _command_head(cmd: str) -> str:
    """Premier vrai token : retire sudo et les assignations d'env (FOO=bar cmd)."""
    toks = _strip_leading_sudo(cmd).strip().split()
    i = 0
    while i < len(toks) and re.match(r'^\w+=', toks[i]):
        i += 1
    return os.path.basename(toks[i]) if i < len(toks) else ""


def is_gui_command(cmd: str) -> bool:
    """La commande lance-t-elle une application graphique ?"""
    head = _command_head(cmd)
    if head in GUI_APPS:
        return True
    if head in GUI_LAUNCHERS:
        # `gio` n'est GUI que pour la sous-commande `open`
        if head == "gio":
            toks = _strip_leading_sudo(cmd).split()
            return "open" in toks[1:2]
        return True
    # Binaire d'une application graphique installée (catalogue .desktop)
    if apps.is_gui_binary(head):
        return True
    return False


def _norm_name(s: str) -> str:
    """Normalise un nom de fichier pour comparaison floue (apostrophes typo, espaces)."""
    for a, b in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'), ("–", "-"), ("—", "-")):
        s = s.replace(a, b)
    return re.sub(r'\s+', ' ', s).strip().casefold()


def _resolve_file(path: str) -> str | None:
    """Retrouve le vrai fichier quand le chemin fourni n'existe pas (ex. apostrophe
    typographique mal retapée par le modèle). Cherche le nom le plus proche dans le
    dossier indiqué. Retourne le chemin corrigé existant, ou None."""
    p = os.path.expanduser(path)
    if os.path.exists(p):
        return p
    if "://" in path:           # URL → pas un fichier local
        return None
    d = os.path.dirname(p)
    if not os.path.isdir(d):
        d = os.path.expanduser("~/Documents") if "Documents" in p else os.path.expanduser("~")
    name = _norm_name(os.path.basename(p))
    if not name:
        return None
    try:
        entries = os.listdir(d)
    except OSError:
        return None
    best, best_ratio = None, 0.0
    for e in entries:
        r = difflib.SequenceMatcher(None, name, _norm_name(e)).ratio()
        if r > best_ratio:
            best, best_ratio = e, r
    if best and best_ratio >= 0.85:
        return os.path.join(d, best)
    return None


def _repair_open_command(inner: str) -> tuple[str, str | None]:
    """Pour un lanceur de fichier (xdg-open/kde-open/gio open), corrige le chemin
    s'il n'existe pas. Retourne (commande_éventuellement_corrigée, chemin_corrigé|None)."""
    head = _command_head(inner)
    if head not in ("xdg-open", "kde-open", "kde-open5", "gio"):
        return inner, None
    try:
        toks = shlex.split(inner)
    except ValueError:
        return inner, None
    if len(toks) < 2:
        return inner, None
    arg = toks[-1]
    if not (arg.startswith("/") or arg.startswith("~") or arg.startswith("./")):
        return inner, None
    if os.path.exists(os.path.expanduser(arg)):
        return inner, None
    fixed = _resolve_file(arg)
    if not fixed:
        return inner, None
    rebuilt = " ".join(shlex.quote(t) for t in toks[:-1] + [fixed])
    return rebuilt, fixed


# Codes de sortie xdg-open (utiles pour un message clair)
XDG_OPEN_CODES = {
    1: "erreur dans la commande",
    2: "le fichier ou dossier n'existe pas",
    3: "l'application requise est introuvable",
    4: "l'ouverture a échoué (aucune application associée ?)",
}


async def _reap(proc):
    """Évite un zombie pour une appli GUI restée ouverte."""
    try:
        await proc.wait()
    except Exception:
        pass


async def launch_gui(cmd: str):
    """
    Lance une application graphique détachée et REMONTE les erreurs.
    - exit 0 rapide (ex. xdg-open qui a délégué) → « lancée »
    - exit ≠ 0 rapide (chemin invalide, etc.)    → message d'erreur + code
    - toujours en cours après un court délai      → vraie fenêtre ouverte → « lancée »
    """
    inner = sanitize(cmd).rstrip("&").strip()        # le modèle ajoute parfois '&'
    # Auto-réparation : chemin inexistant (apostrophe typo, espaces) → vrai fichier
    inner, repaired = _repair_open_command(inner)
    head = _command_head(inner)
    if repaired:
        yield {"type": "chunk", "text": f"↳ chemin corrigé : {repaired}\n"}
    try:
        # `setsid -w` attend le programme → on récupère son vrai code de sortie
        # (xdg-open qui échoue ressort vite ; une fenêtre GUI qui reste ouverte
        #  fera expirer le court délai ci-dessous = succès).
        proc = await asyncio.create_subprocess_shell(
            f"setsid -w {inner}",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception as e:
        yield {"type": "error", "message": f"Lancement impossible : {e}"}
        return

    try:
        rc = await asyncio.wait_for(proc.wait(), timeout=2.5)
    except asyncio.TimeoutError:
        # Toujours en cours = fenêtre GUI restée ouverte → succès, on la laisse vivre.
        asyncio.create_task(_reap(proc))
        yield {"type": "chunk", "text": f"🪟 Application graphique lancée : {inner}\n"}
        yield {"type": "done", "returncode": 0}
        return

    if rc == 0:
        yield {"type": "chunk", "text": f"🪟 Application graphique lancée : {inner}\n"}
        yield {"type": "done", "returncode": 0}
        return

    # Échec : remonter une erreur explicite
    err = ""
    try:
        err = (await proc.stderr.read()).decode("utf-8", "replace").strip()
    except Exception:
        pass
    msg = f"❌ Échec d'ouverture (code {rc})"
    if head in ("xdg-open", "kde-open", "kde-open5", "gio") and rc in XDG_OPEN_CODES:
        msg += f" — {XDG_OPEN_CODES[rc]}"
    if err:
        msg += f"\n{err}"
    yield {"type": "chunk", "text": msg + "\n"}
    yield {"type": "done", "returncode": rc}


def sanitize(cmd: str) -> str:
    """Retire --noconfirm (garde le [Y/n]) et le sudo en trop sur les aides AUR."""
    out = re.sub(r'\s--no-?confirm\b', '', cmd)
    if _is_aur_helper(cmd) and cmd.strip().startswith("sudo"):
        out = _strip_leading_sudo(out)
    return out.strip()


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

    # ── Application graphique : lancer détaché + remonter les erreurs ──────
    if is_gui_command(cmd):
        async for ev in launch_gui(cmd):
            yield ev
        return

    requires_root = needs_root(cmd)
    if requires_root and not sudo_password:
        yield {"type": "needs_sudo", "command": cmd}
        return

    # ── Nom d'application approximatif (binaire introuvable) → résolution ──
    #   Ex. « mission-center » → appli « Mission Center » (binaire missioncenter).
    if not requires_root and apps.looks_like_app_launch(cmd):
        resolved = apps.resolve_app(cmd)
        if resolved:
            launch_cmd, app_name = resolved
            yield {"type": "chunk",
                   "text": f"🔎 Application reconnue : « {app_name} » → {launch_cmd}\n"}
            async for ev in launch_gui(launch_cmd):
                yield ev
            return

    actual_cmd = sanitize(cmd)

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

    elapsed = 0.0
    last_output_at = asyncio.get_event_loop().time()
    idle_warned = False
    pw_buffer = ""            # fenêtre glissante pour détecter le prompt sudo
    last_pw_inject = 0.0      # anti-spam d'injection du mot de passe

    def _maybe_inject_password(text: str):
        """Injecte le mot de passe sudo quand son prompt apparaît dans la sortie."""
        nonlocal pw_buffer, last_pw_inject
        if not (sudo_password and requires_root):
            return
        pw_buffer = (pw_buffer + text)[-400:]
        if SUDO_RETRY_RE.search(text):
            last_pw_inject = 0.0          # mauvais mdp → autoriser une relance
        now = asyncio.get_event_loop().time()
        if SUDO_PROMPT_RE.search(pw_buffer) and (now - last_pw_inject) > 1.0:
            try:
                os.write(master, (sudo_password + "\n").encode())
            except OSError:
                pass
            last_pw_inject = now
            pw_buffer = ""                # consommé

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
                    _maybe_inject_password(text)
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
