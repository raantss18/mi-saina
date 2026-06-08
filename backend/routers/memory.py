from fastapi import APIRouter
from pydantic import BaseModel

import os

from services.memory import (
    create_session, list_sessions, get_session_messages, delete_session,
    search_memory, search_history, set_session_working_dir, get_session_working_dir,
)

router = APIRouter()


class SessionCreate(BaseModel):
    title: str | None = None


class WorkingDir(BaseModel):
    path: str | None = None


class SearchQuery(BaseModel):
    query: str
    top_k: int = 5


@router.post("/sessions")
def new_session(body: SessionCreate):
    s = create_session(body.title)
    return {"id": s.id, "title": s.title}


@router.get("/sessions")
def sessions_list():
    return list_sessions()


@router.get("/sessions/{session_id}/messages")
def session_messages(session_id: str):
    return get_session_messages(session_id)


@router.delete("/sessions/{session_id}")
def remove_session(session_id: str):
    delete_session(session_id)
    return {"status": "deleted"}


@router.put("/sessions/{session_id}/working-dir")
def set_working_dir(session_id: str, body: WorkingDir):
    """Définit le dossier de travail d'une session (commandes + contexte)."""
    path = (body.path or "").strip()
    path = os.path.expanduser(path) if path else None
    if path and not os.path.isdir(path):
        return {"status": "error", "detail": "Dossier introuvable", "working_dir": get_session_working_dir(session_id)}
    set_session_working_dir(session_id, path)
    return {"status": "ok", "working_dir": path}


@router.post("/search")
def semantic_search(body: SearchQuery):
    return search_memory(body.query, body.top_k)


@router.get("/history-search")
def history_search(q: str):
    """Recherche plein-texte (FTS5) dans tout l'historique des conversations."""
    return search_history(q)
