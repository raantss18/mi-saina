"""
Carte de configuration (local, jamais versionné) : ~/.config/mi-saina/config-map.md

Scan DÉTERMINISTE (zéro LLM) et SECRET-SAFE de l'environnement applicatif de
l'utilisateur, pour que l'agent connaisse déjà le terrain (apps configurées, applis
par défaut, scripts perso, thème, éditeur…) au lieu de le redécouvrir par des
commandes — moins d'hallucinations, moins d'erreurs, moins de tokens.

Principe de sûreté : on ne lit que
  - des NOMS (dossiers de ~/.config, fichiers de ~/.local/bin, lanceurs .desktop) ;
  - une ALLOWLIST de clés NON sensibles dans quelques fichiers de config connus.
On n'ouvre JAMAIS un fichier au hasard pour en extraire des valeurs, et toute clé
ressemblant à un secret (token/clé/mot de passe…) est ignorée.

Deux sorties :
  - index COMPACT (entre marqueurs) injecté au system prompt (borné) ;
  - DÉTAIL complet dans le même fichier, lu à la demande par l'agent ([READ: …]).
"""
import configparser
import os
import shutil
import subprocess
import time
from datetime import date
from pathlib import Path

HOME = Path.home()
CONFIG_HOME = Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config")) / "mi-saina"
MAP_FILE = CONFIG_HOME / "config-map.md"

_INDEX_START = "<!-- INDEX -->"
_INDEX_END = "<!-- /INDEX -->"

# Clés/fichiers ressemblant à un secret → jamais lus/stockés.
_SECRET_HINT = ("secret", "token", "password", "passwd", "passphrase", "apikey",
                "api_key", "client_secret", "private", "credential", "cookie",
                "auth", "session", "bearer", ".key", ".pem", "id_rsa", "id_ed25519")

# Dossiers ~/.config à ignorer (bruit ou nous-mêmes).
_CFG_IGNORE = {"mi-saina", "pulse", "dconf", "ibus", "menus", "autostart"}


def _is_secretish(name: str) -> bool:
    n = name.lower()
    return any(h in n for h in _SECRET_HINT)


def _run(cmd: list[str], timeout: float = 3.0) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except Exception:
        return ""


def _ini_get(path: Path, section: str, keys: list[str]) -> dict:
    """Lit une allowlist de clés NON sensibles dans un fichier .ini. Tolérant."""
    out = {}
    if not path.is_file():
        return out
    cp = configparser.ConfigParser(strict=False, interpolation=None)
    try:
        cp.read(path, encoding="utf-8")
    except Exception:
        return out
    if not cp.has_section(section):
        return out
    for k in keys:
        if _is_secretish(k):
            continue
        try:
            v = cp.get(section, k, fallback="").strip()
        except Exception:
            v = ""
        if v and not _is_secretish(v):
            out[k] = v[:120]
    return out


# ── Collecte ───────────────────────────────────────────────────────────────────

def scan(config_dir: Path | None = None, local_dir: Path | None = None) -> dict:
    """Collecte read-only et bornée. `config_dir`/`local_dir` paramétrables (tests)."""
    cfg = Path(config_dir) if config_dir else (HOME / ".config")
    loc = Path(local_dir) if local_dir else (HOME / ".local")

    # 1) Apps configurées = sous-dossiers de ~/.config (noms uniquement)
    apps = []
    try:
        with os.scandir(cfg) as it:
            for e in it:
                if e.name.startswith(".") or e.name in _CFG_IGNORE:
                    continue
                try:
                    if e.is_dir(follow_symlinks=False) and not _is_secretish(e.name):
                        apps.append(e.name)
                except OSError:
                    continue
    except OSError:
        pass
    apps.sort(key=str.lower)

    # 2) Scripts/commandes perso dans ~/.local/bin (noms uniquement)
    scripts = []
    try:
        with os.scandir(loc / "bin") as it:
            for e in it:
                if e.name.startswith("."):
                    continue
                try:
                    if e.is_file(follow_symlinks=True) and os.access(e.path, os.X_OK):
                        scripts.append(e.name)
                except OSError:
                    continue
    except OSError:
        pass
    scripts.sort(key=str.lower)

    # 3) Lanceurs personnalisés ~/.local/share/applications (Name + binaire)
    launchers = []
    try:
        appdir = loc / "share" / "applications"
        with os.scandir(appdir) as it:
            for e in it:
                if not e.name.endswith(".desktop"):
                    continue
                d = _ini_get(Path(e.path), "Desktop Entry", ["Name", "Exec"])
                name = d.get("Name", e.name[:-8])
                exe = (d.get("Exec", "").split() or [""])[0]
                exe = os.path.basename(exe) if exe else ""
                launchers.append((name, exe))
    except OSError:
        pass
    launchers = launchers[:40]

    # 4) Réglages clés NON sensibles (fichiers connus + commandes sûres)
    settings_facts = {}

    # Shell + framework
    settings_facts["shell"] = os.path.basename(os.environ.get("SHELL", "")) or "?"
    if (HOME / ".oh-my-zsh").is_dir():
        settings_facts["shell_framework"] = "oh-my-zsh"
    if (cfg / "starship.toml").is_file():
        settings_facts["prompt"] = "starship"

    # Éditeur / terminal préférés (env + détection de config présente)
    for var in ("EDITOR", "VISUAL"):
        if os.environ.get(var):
            settings_facts["editor"] = os.path.basename(os.environ[var])
            break
    for term in ("kitty", "alacritty", "wezterm", "foot"):
        if (cfg / term).is_dir():
            settings_facts.setdefault("terminal_configuré", term)

    # Navigateur par défaut (xdg-settings, sûr)
    if shutil.which("xdg-settings"):
        b = _run(["xdg-settings", "get", "default-web-browser"], timeout=3)
        if b:
            settings_facts["navigateur_défaut"] = b.replace(".desktop", "")

    # Applis par défaut pour quelques types (mimeapps.list, [Default Applications])
    defaults = _ini_get(cfg / "mimeapps.list", "Default Applications",
                        ["text/plain", "application/pdf", "image/png",
                         "video/mp4", "inode/directory", "text/html"])
    defaults = {k: v.replace(".desktop", "") for k, v in defaults.items()}

    # Thème (GTK puis KDE)
    gtk = _ini_get(cfg / "gtk-3.0" / "settings.ini", "Settings",
                  ["gtk-theme-name", "gtk-icon-theme-name"])
    if gtk.get("gtk-theme-name"):
        settings_facts["thème_gtk"] = gtk["gtk-theme-name"]
    if gtk.get("gtk-icon-theme-name"):
        settings_facts["icônes"] = gtk["gtk-icon-theme-name"]
    kde = _ini_get(cfg / "kdeglobals", "KDE", ["widgetStyle", "LookAndFeelPackage"])
    if kde.get("LookAndFeelPackage"):
        settings_facts["thème_kde"] = kde["LookAndFeelPackage"]

    # Git (via git config — ne renvoie que ce qu'on demande, pas de secret)
    if shutil.which("git"):
        name = _run(["git", "config", "--global", "user.name"], timeout=3)
        editor = _run(["git", "config", "--global", "core.editor"], timeout=3)
        branch = _run(["git", "config", "--global", "init.defaultBranch"], timeout=3)
        if name:
            settings_facts["git_user"] = name[:60]
        if editor:
            settings_facts["git_editor"] = editor[:40]
        if branch:
            settings_facts["git_branche_défaut"] = branch[:30]

    return {"apps": apps, "scripts": scripts, "launchers": launchers,
            "settings": settings_facts, "defaults": defaults}


# ── Rendu ──────────────────────────────────────────────────────────────────────

def _render_index(data: dict) -> str:
    s = data["settings"]
    lines = ["## CONFIG CONNUE (résumé — détail complet via [READ: ~/.config/mi-saina/config-map.md])"]
    facts = []
    for label, key in (("navigateur", "navigateur_défaut"), ("éditeur", "editor"),
                       ("git_editor", "git_editor"), ("terminal", "terminal_configuré"),
                       ("shell", "shell")):
        if s.get(key):
            facts.append(f"{label}={s[key]}")
    if facts:
        lines.append("- Préférences : " + " · ".join(facts))
    if data["apps"]:
        shown = ", ".join(data["apps"][:30])
        extra = f" (+{len(data['apps']) - 30})" if len(data["apps"]) > 30 else ""
        lines.append(f"- Apps configurées ({len(data['apps'])}) : {shown}{extra}")
    if data["scripts"]:
        shown = ", ".join(data["scripts"][:20])
        extra = f" (+{len(data['scripts']) - 20})" if len(data["scripts"]) > 20 else ""
        lines.append(f"- Scripts perso ~/.local/bin ({len(data['scripts'])}) : {shown}{extra}")
    lines.append("- Avant de configurer une app ou supposer un réglage, CONSULTE le détail "
                 "(READ ci-dessus) au lieu de deviner. Ne traite cette carte que comme un INDICE.")
    return "\n".join(lines)


def _render_detail(data: dict) -> str:
    s = data["settings"]
    lines = [f"## CARTE DE CONFIGURATION — détail (scan du {date.today().isoformat()}, déterministe, sans secrets)"]

    if s:
        lines.append("\n### Préférences détectées")
        for k, v in s.items():
            lines.append(f"- {k} : {v}")

    if data["defaults"]:
        lines.append("\n### Applications par défaut (par type)")
        for k, v in data["defaults"].items():
            lines.append(f"- {k} → {v}")

    if data["apps"]:
        lines.append(f"\n### Applications configurées dans ~/.config ({len(data['apps'])})")
        lines.append("- " + ", ".join(data["apps"]))

    if data["scripts"]:
        lines.append(f"\n### Scripts/commandes perso dans ~/.local/bin ({len(data['scripts'])})")
        lines.append("- " + ", ".join(data["scripts"]))

    if data["launchers"]:
        lines.append(f"\n### Lanceurs personnalisés (~/.local/share/applications)")
        for name, exe in data["launchers"]:
            lines.append(f"- {name}" + (f" → `{exe}`" if exe else ""))

    lines.append("\n_Note : aucune valeur sensible (token, clé, mot de passe) n'est lue ni stockée._")
    return "\n".join(lines)


def _compose(data: dict) -> str:
    return (f"{_INDEX_START}\n{_render_index(data)}\n{_INDEX_END}\n\n{_render_detail(data)}\n")


# ── API ────────────────────────────────────────────────────────────────────────

def refresh() -> str:
    content = _compose(scan())
    CONFIG_HOME.mkdir(parents=True, exist_ok=True)
    MAP_FILE.write_text(content, encoding="utf-8")
    return content


def read() -> str:
    try:
        return MAP_FILE.read_text(encoding="utf-8") if MAP_FILE.exists() else ""
    except OSError:
        return ""


def index_block() -> str:
    """Index compact (entre marqueurs) à injecter dans le system prompt."""
    txt = read()
    if _INDEX_START in txt and _INDEX_END in txt:
        return txt.split(_INDEX_START, 1)[1].split(_INDEX_END, 1)[0].strip()
    return ""


def _age_hours() -> float:
    try:
        return (time.time() - MAP_FILE.stat().st_mtime) / 3600.0
    except OSError:
        return 1e9


def ensure_fresh(max_age_h: float = 24.0) -> None:
    """(Re)scanne si la carte est absente ou périmée (> max_age_h). Tolérant."""
    if not MAP_FILE.exists() or _age_hours() > max_age_h:
        try:
            refresh()
        except Exception:
            pass


async def config_map_loop() -> None:
    """Maintient la carte fraîche : 1er scan au démarrage si périmé, puis ~1×/jour.
    Respecte le réglage CONFIG_MAP à chaud. Léger (déterministe, pas de LLM)."""
    import asyncio
    from config import settings
    await asyncio.sleep(60)   # laisse le démarrage se faire
    while True:
        try:
            if getattr(settings, "CONFIG_MAP", True):
                await asyncio.to_thread(ensure_fresh, 24.0)
        except Exception:
            pass
        await asyncio.sleep(6 * 3600)   # revérifie toutes les 6 h (rescanne si > 24 h)
