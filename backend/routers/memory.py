from fastapi import APIRouter
from pydantic import BaseModel

from services.memory import create_session, list_sessions, get_session_messages, delete_session, search_memory

router = APIRouter()


class SessionCreate(BaseModel):
    title: str | None = None


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


@router.post("/search")
def semantic_search(body: SearchQuery):
    return search_memory(body.query, body.top_k)
