import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path

import httpx
import numpy as np
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, relationship

from config import settings

DB_PATH = Path(__file__).parent.parent / "data" / "sessions.db"
DB_PATH.parent.mkdir(exist_ok=True)
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)


async def _get_embedding_async(text: str) -> list[float] | None:
    """Embedding via Ollama /api/embeddings — async, non-bloquant."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/embeddings",
                json={"model": settings.FAST_MODEL, "prompt": text},
            )
            if resp.status_code == 200:
                return resp.json().get("embedding")
    except Exception:
        pass
    return None


class Base(DeclarativeBase):
    pass


class ChatSession(Base):
    __tablename__ = "sessions"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    session = relationship("ChatSession", back_populates="messages")


Base.metadata.create_all(engine)


# ── CRUD sessions ─────────────────────────────────────────────────────────────

def create_session(title: str | None = None) -> ChatSession:
    with Session(engine) as db:
        s = ChatSession(title=title)
        db.add(s)
        db.commit()
        db.refresh(s)
        return s


def update_session_title(session_id: str, title: str) -> None:
    with Session(engine) as db:
        s = db.query(ChatSession).filter_by(id=session_id).first()
        if s:
            s.title = title
            db.commit()


def session_message_count(session_id: str) -> int:
    with Session(engine) as db:
        return db.query(Message).filter_by(session_id=session_id).count()


def list_sessions() -> list[dict]:
    with Session(engine) as db:
        rows = db.query(ChatSession).order_by(ChatSession.updated_at.desc()).all()
        return [{"id": s.id, "title": s.title, "updated_at": s.updated_at.isoformat()} for s in rows]


def get_session_messages(session_id: str) -> list[dict]:
    with Session(engine) as db:
        msgs = (
            db.query(Message)
            .filter_by(session_id=session_id)
            .order_by(Message.created_at)
            .all()
        )
        return [{"role": m.role, "content": m.content} for m in msgs]


def delete_session(session_id: str) -> None:
    with Session(engine) as db:
        s = db.query(ChatSession).filter_by(id=session_id).first()
        if s:
            db.delete(s)
            db.commit()


# ── Messages + embeddings (fire-and-forget) ───────────────────────────────────

async def _update_embedding_bg(msg_id: str, content: str) -> None:
    """Calcule l'embedding en arrière-plan et met à jour la DB sans bloquer."""
    emb = await _get_embedding_async(content)
    if not emb:
        return
    with Session(engine) as db:
        msg = db.query(Message).filter_by(id=msg_id).first()
        if msg:
            msg.embedding = json.dumps(emb)
            db.commit()


async def add_message(session_id: str, role: str, content: str) -> None:
    """Sauvegarde le message immédiatement, calcule l'embedding en tâche de fond."""
    msg_id = str(uuid.uuid4())
    with Session(engine) as db:
        db.add(Message(id=msg_id, session_id=session_id, role=role, content=content))
        s = db.query(ChatSession).filter_by(id=session_id).first()
        if s:
            s.updated_at = datetime.utcnow()
        db.commit()
    # Fire-and-forget: ne bloque pas la réponse LLM
    asyncio.create_task(_update_embedding_bg(msg_id, content))


# ── Recherche sémantique ──────────────────────────────────────────────────────

async def search_memory(query: str, top_k: int = 5) -> list[dict]:
    q_emb_raw = await _get_embedding_async(query)
    if not q_emb_raw:
        return []
    q_emb = np.array(q_emb_raw)
    with Session(engine) as db:
        msgs = db.query(Message).filter(Message.embedding.isnot(None)).all()
        if not msgs:
            return []
        scored = []
        for m in msgs:
            emb = np.array(json.loads(m.embedding))
            score = float(np.dot(q_emb, emb) / (np.linalg.norm(q_emb) * np.linalg.norm(emb) + 1e-9))
            scored.append({"role": m.role, "content": m.content, "score": score})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]


async def build_context_prefix(query: str) -> str:
    results = await search_memory(query, top_k=4)
    if not results:
        return ""
    lines = ["[MÉMOIRE PERTINENTE — extraits de conversations précédentes]"]
    for r in results:
        lines.append(f"- [{r['role']}] {r['content'][:300]}")
    lines.append("[FIN MÉMOIRE]")
    return "\n".join(lines)
