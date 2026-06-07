"""
Contexte utilisateur persistant (local, jamais versionné) :
- context.md : contexte/instructions globales écrites par l'utilisateur.
- profile.md : préférences/faits mémorisés (enrichi via [REMEMBER: ...]).
- MISAINA.md : contexte d'un projet (dossier configurable PROJECT_DIR).

Tout est rangé dans ~/.config/mi-saina/ et injecté automatiquement dans le prompt.
"""

import os
from datetime import date
from pathlib import Path

from config import settings

CONFIG_HOME = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "mi-saina"
CONTEXT_FILE = CONFIG_HOME / "context.md"
PROFILE_FILE = CONFIG_HOME / "profile.md"


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8") if path.exists() else ""
    except OSError:
        return ""


def _write(path: Path, text: str) -> None:
    CONFIG_HOME.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_context() -> str:
    return _read(CONTEXT_FILE)


def write_context(text: str) -> None:
    _write(CONTEXT_FILE, text)


def read_profile() -> str:
    return _read(PROFILE_FILE)


def write_profile(text: str) -> None:
    _write(PROFILE_FILE, text)


def append_profile(fact: str) -> None:
    """Ajoute un fait/préférence au profil (dédupliqué, daté)."""
    fact = fact.strip()
    if not fact:
        return
    existing = read_profile()
    if fact.lower() in existing.lower():
        return                       # déjà connu → pas de doublon
    line = f"- {fact}  _(mémorisé le {date.today().isoformat()})_\n"
    if not existing:
        existing = "# Profil utilisateur — préférences mémorisées\n\n"
    write_profile(existing.rstrip() + "\n" + line)


def ensure_files() -> None:
    """Crée des fichiers de mémoire vides à la 1re utilisation (jamais versionnés).
    Garantit qu'une nouvelle installation a bien context.md + profile.md."""
    CONFIG_HOME.mkdir(parents=True, exist_ok=True)
    # Fichiers vides (0 octet) : non injectés au prompt tant qu'ils sont vides,
    # mais présents/éditables dès la 1re installation.
    for f in (CONTEXT_FILE, PROFILE_FILE):
        if not f.exists():
            f.write_text("", encoding="utf-8")


def read_project_context() -> str:
    """Lit MISAINA.md (ou README.md) dans le dossier de projet configuré, si présent."""
    pdir = getattr(settings, "PROJECT_DIR", "") or ""
    if not pdir:
        return ""
    base = Path(os.path.expanduser(pdir))
    for name in ("MISAINA.md", "misaina.md", "README.md"):
        f = base / name
        if f.exists():
            return _read(f)[:4000]   # borne pour ne pas saturer le contexte
    return ""


def context_block() -> str:
    """Bloc combiné (contexte + profil + projet) à ajouter au system prompt."""
    parts = []
    ctx = read_context().strip()
    if ctx:
        parts.append("## CONTEXTE UTILISATEUR (context.md — instructions persistantes)\n" + ctx)
    proj = read_project_context().strip()
    if proj:
        parts.append("## CONTEXTE DU PROJET (fichier du dossier de travail)\n" + proj)
    prof = read_profile().strip()
    if prof:
        parts.append("## PROFIL UTILISATEUR (préférences mémorisées — tiens-en compte)\n" + prof)
    return "\n\n".join(parts)
