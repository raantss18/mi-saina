import json
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
SYSTEM_PROMPT_FILE = CONFIG_DIR / "system_prompt.txt"
SKILLS_DIR = CONFIG_DIR / "skills"


def _default_prompt() -> str:
    return "Tu es mi-saina, un assistant IA local expert avec accès complet à la machine Linux."


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
