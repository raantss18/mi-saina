"""
Profil machine persistant (local, jamais versionné) : ~/.config/mi-saina/machine.md

Collecté au 1er démarrage et via le bouton « Rafraîchir » (Config). Injecté dans le
system prompt pour que l'agent connaisse les VRAIS chemins de l'utilisateur (résout
p.ex. « Téléchargements » vs « Downloads »), la structure de son dossier personnel et
les outils installés — sans deviner ni halluciner.

Tout est read-only, borné et tolérant aux erreurs (jamais bloquant).
"""
import os
import shutil
import subprocess
from datetime import date
from pathlib import Path

CONFIG_HOME = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "mi-saina"
MACHINE_FILE = CONFIG_HOME / "machine.md"
HOME = Path.home()

# Dossiers utilisateur XDG à résoudre (gère les noms localisés : Téléchargements…).
_XDG = [
    ("DOWNLOAD", "Téléchargements"), ("DOCUMENTS", "Documents"), ("DESKTOP", "Bureau"),
    ("PICTURES", "Images"), ("VIDEOS", "Vidéos"), ("MUSIC", "Musique"),
]

# Outils dont on note seulement la PRÉSENCE (aide l'agent à savoir quoi utiliser).
_TOOLS = [
    "git", "docker", "podman", "code", "nvim", "vim", "emacs", "python3", "node",
    "npm", "pnpm", "cargo", "rustc", "go", "java", "gcc", "make", "cmake",
    "flatpak", "snap", "jupyter", "latexmk", "ffmpeg", "rsync",
]

# Catégorisation des fichiers par extension (agrégée — pas de noms exposés).
_CATEGORIES = {
    "documents": {".pdf", ".doc", ".docx", ".odt", ".txt", ".md", ".rtf", ".epub",
                  ".xls", ".xlsx", ".ods", ".ppt", ".pptx", ".csv"},
    "images": {".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".bmp", ".tiff", ".heic"},
    "vidéos": {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv"},
    "audio": {".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac"},
    "archives": {".zip", ".tar", ".gz", ".xz", ".bz2", ".7z", ".rar", ".iso", ".deb", ".rpm"},
    "code": {".py", ".js", ".ts", ".tsx", ".jsx", ".rs", ".go", ".c", ".cpp", ".h",
             ".java", ".sh", ".html", ".css", ".json", ".toml", ".yml", ".yaml", ".ipynb"},
}


def _run(cmd: list[str], timeout: float = 4.0) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except Exception:
        return ""


def categorize(ext: str) -> str:
    """Catégorie d'une extension de fichier (pure, testable)."""
    ext = ext.lower()
    for cat, exts in _CATEGORIES.items():
        if ext in exts:
            return cat
    return "autres"


def _xdg_dir(name: str) -> str:
    """Chemin XDG réel (localisé) via `xdg-user-dir`, sinon repli ~/<Anglais>."""
    if shutil.which("xdg-user-dir"):
        p = _run(["xdg-user-dir", name], timeout=2)
        if p and os.path.isdir(p) and p != str(HOME):
            return p
    # Repli : noms anglais standards
    fallback = {"DOWNLOAD": "Downloads", "DOCUMENTS": "Documents", "DESKTOP": "Desktop",
                "PICTURES": "Pictures", "VIDEOS": "Videos", "MUSIC": "Music"}.get(name, "")
    cand = HOME / fallback if fallback else None
    return str(cand) if cand and cand.is_dir() else ""


def _summarize_dir(path: str) -> dict:
    """Résumé agrégé d'un dossier (niveau 1 only) : compte par catégorie, sous-dossiers,
    taille. Pas de noms de fichiers (vie privée). Borné et tolérant."""
    out = {"files": 0, "subdirs": 0, "by_cat": {}, "size": ""}
    try:
        with os.scandir(path) as it:
            for e in it:
                try:
                    if e.is_dir(follow_symlinks=False):
                        out["subdirs"] += 1
                    elif e.is_file(follow_symlinks=False):
                        out["files"] += 1
                        cat = categorize(Path(e.name).suffix)
                        out["by_cat"][cat] = out["by_cat"].get(cat, 0) + 1
                except OSError:
                    continue
    except OSError:
        return out
    # Taille via du -sh (borné par timeout ; n/a si trop long)
    size = _run(["du", "-sh", path], timeout=6)
    if size:
        out["size"] = size.split("\t")[0].split()[0]
    return out


def collect() -> dict:
    """Collecte le profil machine (home + outils + environnement). Read-only, borné."""
    # 1) Chemins XDG réels
    xdg = []
    for key, label in _XDG:
        p = _xdg_dir(key)
        if p:
            xdg.append((label, p))

    # 2) Structure de ~ (niveau 1 : noms de dossiers non cachés)
    top_dirs, hidden = [], 0
    try:
        with os.scandir(HOME) as it:
            for e in it:
                if e.name.startswith("."):
                    hidden += 1
                    continue
                try:
                    if e.is_dir(follow_symlinks=False):
                        top_dirs.append(e.name)
                except OSError:
                    continue
    except OSError:
        pass
    top_dirs.sort()

    # 3) Aperçu des dossiers standards (agrégé)
    summaries = {}
    for label, p in xdg:
        summaries[label] = (p, _summarize_dir(p))

    # 4) Outils installés
    tools = [t for t in _TOOLS if shutil.which(t)]

    # 5) Environnement
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "") or os.environ.get("DESKTOP_SESSION", "")
    session_type = os.environ.get("XDG_SESSION_TYPE", "")
    locale = os.environ.get("LANG", "")

    return {
        "xdg": xdg, "top_dirs": top_dirs, "hidden": hidden,
        "summaries": summaries, "tools": tools,
        "desktop": desktop, "session_type": session_type, "locale": locale,
    }


def _render(data: dict) -> str:
    lines = [f"## PROFIL MACHINE (collecté le {date.today().isoformat()} — chemins et dossiers RÉELS de l'utilisateur)"]
    lines.append("Utilise ces chemins EXACTS. Ne devine jamais un nom de dossier (ex. ne suppose pas « Downloads » si le dossier réel est « Téléchargements »).")

    if data["xdg"]:
        lines.append("\n### Dossiers utilisateur (chemins XDG réels)")
        for label, p in data["xdg"]:
            lines.append(f"- {label} : `{p}`")

    if data["top_dirs"]:
        shown = ", ".join(data["top_dirs"][:40])
        extra = f" (+{len(data['top_dirs']) - 40} autres)" if len(data["top_dirs"]) > 40 else ""
        lines.append(f"\n### Dossier personnel (~ = `{HOME}`) — sous-dossiers (niveau 1)")
        lines.append(f"- {shown}{extra}")
        if data["hidden"]:
            lines.append(f"- (+ {data['hidden']} éléments cachés)")

    if data["summaries"]:
        lines.append("\n### Aperçu des dossiers standards (agrégé)")
        for label, (p, s) in data["summaries"].items():
            cats = ", ".join(f"{k} {v}" for k, v in sorted(s["by_cat"].items(), key=lambda x: -x[1]) if v)
            size = f", ~{s['size']}" if s.get("size") else ""
            sub = f", {s['subdirs']} sous-dossiers" if s["subdirs"] else ""
            detail = f" — {cats}" if cats else " — vide"
            lines.append(f"- {label} : {s['files']} fichier(s){sub}{size}{detail}")

    if data["tools"]:
        lines.append("\n### Outils détectés (disponibles sur cette machine)")
        lines.append("- " + ", ".join(data["tools"]))

    env_bits = []
    if data["desktop"]:
        env_bits.append(f"Bureau : {data['desktop']}" + (f" ({data['session_type']})" if data["session_type"] else ""))
    if data["locale"]:
        env_bits.append(f"Locale : {data['locale']}")
    if env_bits:
        lines.append("\n### Environnement")
        for b in env_bits:
            lines.append(f"- {b}")

    return "\n".join(lines) + "\n"


def refresh() -> str:
    """(Re)collecte et écrit machine.md. Retourne le contenu rendu."""
    content = _render(collect())
    CONFIG_HOME.mkdir(parents=True, exist_ok=True)
    MACHINE_FILE.write_text(content, encoding="utf-8")
    return content


def read() -> str:
    try:
        return MACHINE_FILE.read_text(encoding="utf-8") if MACHINE_FILE.exists() else ""
    except OSError:
        return ""


def machine_block() -> str:
    """Bloc à injecter dans le system prompt (vide si non collecté)."""
    return read().strip()


def ensure_collected() -> None:
    """Collecte au 1er démarrage si machine.md absent (appelé en tâche de fond)."""
    if not MACHINE_FILE.exists():
        try:
            refresh()
        except Exception:
            pass
