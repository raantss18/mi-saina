import json
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import EDITABLE_SETTINGS, current_settings, update_settings

router = APIRouter()

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
SYSTEM_PROMPT_FILE = CONFIG_DIR / "system_prompt.txt"
SKILLS_DIR = CONFIG_DIR / "skills"


def _default_prompt() -> str:
    return "Tu es mi-saina, un assistant IA local créé par Antsa, expert avec accès complet à la machine Linux."


# ── System prompt ─────────────────────────────────────────────────────────────

@router.get("/system-prompt")
def get_system_prompt():
    if SYSTEM_PROMPT_FILE.exists():
        return {"content": SYSTEM_PROMPT_FILE.read_text()}
    return {"content": _default_prompt()}


class SystemPromptBody(BaseModel):
    content: str


@router.put("/system-prompt")
def put_system_prompt(body: SystemPromptBody):
    CONFIG_DIR.mkdir(exist_ok=True)
    SYSTEM_PROMPT_FILE.write_text(body.content)
    return {"status": "ok"}


# ── Contexte utilisateur & profil (locaux, ~/.config/mi-saina) ─────────────────
from services import userctx, machine_profile  # noqa: E402


class TextBody(BaseModel):
    content: str


@router.get("/context")
def get_context():
    return {"content": userctx.read_context()}


@router.put("/context")
def put_context(body: TextBody):
    userctx.write_context(body.content)
    return {"status": "ok"}


@router.get("/profile")
def get_profile():
    return {"content": userctx.read_profile()}


@router.put("/profile")
def put_profile(body: TextBody):
    userctx.write_profile(body.content)
    return {"status": "ok"}


# ── Profil machine (chemins réels, structure du home, outils) ──────────────────

@router.get("/machine")
def get_machine():
    """Profil machine collecté (vide s'il n'a pas encore été généré)."""
    return {"content": machine_profile.read()}


@router.post("/machine/refresh")
def refresh_machine():
    """(Re)collecte le profil machine maintenant (read-only, borné)."""
    try:
        return {"status": "ok", "content": machine_profile.refresh()}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


# ── Réglages modifiables à chaud ───────────────────────────────────────────────

@router.get("/settings")
def get_settings():
    """Schéma (libellés/bornes) + valeurs courantes des réglages éditables."""
    return {"schema": EDITABLE_SETTINGS, "values": current_settings()}


class SettingsBody(BaseModel):
    values: dict


@router.put("/settings")
def put_settings(body: SettingsBody):
    try:
        values = update_settings(body.values)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "ok", "values": values}


# ── Skills ────────────────────────────────────────────────────────────────────

@router.get("/skills")
def list_skills():
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    skills = []
    for f in sorted(SKILLS_DIR.glob("*.json")):
        try:
            skills.append(json.loads(f.read_text()))
        except Exception:
            pass
    return skills


class Skill(BaseModel):
    name: str
    trigger: str
    description: str
    icon: str = "⚡"
    prompt: str


@router.post("/skills")
def create_skill(skill: Skill):
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    safe = "".join(c for c in skill.name if c.isalnum() or c in "-_")
    path = SKILLS_DIR / f"{safe}.json"
    path.write_text(skill.model_dump_json(indent=2))
    return {"status": "ok", "name": skill.name}


@router.delete("/skills/{name}")
def delete_skill(name: str):
    safe = "".join(c for c in name if c.isalnum() or c in "-_")
    path = SKILLS_DIR / f"{safe}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Skill not found")
    path.unlink()
    return {"status": "deleted"}
