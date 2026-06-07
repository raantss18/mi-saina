import asyncio
import json
import re
import uuid
from datetime import datetime, timezone
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
                json={"model": settings.EMBED_MODEL, "prompt": text},
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


# ── Recherche plein-texte (SQLite FTS5) ────────────────────────────────────────
def _init_fts() -> None:
    """Crée l'index FTS5 sur le contenu des messages + triggers de synchro."""
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql(
                "CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts "
                "USING fts5(content, content='messages', content_rowid='rowid')")
            conn.exec_driver_sql(
                "CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN "
                "INSERT INTO messages_fts(rowid, content) VALUES (new.rowid, new.content); END")
            conn.exec_driver_sql(
                "CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN "
                "INSERT INTO messages_fts(messages_fts, rowid, content) "
                "VALUES('delete', old.rowid, old.content); END")
            conn.exec_driver_sql(
                "CREATE TRIGGER IF NOT EXISTS messages_au AFTER UPDATE ON messages BEGIN "
                "INSERT INTO messages_fts(messages_fts, rowid, content) "
                "VALUES('delete', old.rowid, old.content); "
                "INSERT INTO messages_fts(rowid, content) VALUES (new.rowid, new.content); END")
            # (Re)construction de l'index depuis la table source (table à contenu externe).
            # Idempotent et peu coûteux à notre échelle ; les triggers assurent ensuite la synchro.
            conn.exec_driver_sql("INSERT INTO messages_fts(messages_fts) VALUES('rebuild')")
    except Exception:
        pass   # FTS5 indisponible → la recherche plein-texte sera simplement vide


_init_fts()


def search_history(query: str, limit: int = 25) -> list[dict]:
    """Recherche plein-texte dans l'historique. Retourne des sessions + extraits."""
    terms = re.findall(r"\w+", query or "", flags=re.UNICODE)
    if not terms:
        return []
    fts_query = " ".join(f'"{t}"' for t in terms)   # littéral, évite la syntaxe FTS
    try:
        with engine.begin() as conn:
            rows = conn.exec_driver_sql(
                "SELECT m.session_id, s.title, m.role, "
                "snippet(messages_fts, 0, '«', '»', '…', 10) AS snip "
                "FROM messages_fts f "
                "JOIN messages m ON m.rowid = f.rowid "
                "LEFT JOIN sessions s ON s.id = m.session_id "
                "WHERE messages_fts MATCH ? ORDER BY rank LIMIT ?",
                (fts_query, limit)).fetchall()
    except Exception:
        return []
    out, seen = [], set()
    for session_id, title, role, snip in rows:
        out.append({"session_id": session_id, "title": title or "Sans titre",
                    "role": role, "snippet": snip})
        seen.add(session_id)
    return out


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


def _utc_iso(dt) -> str:
    """ISO 8601 marqué UTC. Les dates sont stockées en UTC naïf (utcnow) ; sans
    marqueur de fuseau, le navigateur les lisait comme heure LOCALE → décalage de
    plusieurs heures. On les marque UTC pour que `new Date()` convertisse bien."""
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def list_sessions() -> list[dict]:
    with Session(engine) as db:
        rows = db.query(ChatSession).order_by(ChatSession.updated_at.desc()).all()
        return [{"id": s.id, "title": s.title, "updated_at": _utc_iso(s.updated_at)} for s in rows]


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


async def build_context_prefix(query: str, min_score: float = 0.62) -> str:
    """Injecte des extraits de mémoire SEULEMENT s'ils sont vraiment proches de la
    demande (seuil de similarité). Sans seuil, on injectait toujours les 4 messages
    « les moins éloignés » même hors sujet → le petit modèle les prenait pour la
    tâche en cours (réponses hors sujet / contexte qui « bave »)."""
    results = await search_memory(query, top_k=3)
    results = [r for r in results if r.get("score", 0) >= min_score]
    if not results:
        return ""
    lines = ["[NOTES DE MÉMOIRE — extraits de conversations PASSÉES, éventuellement utiles. "
             "NE réponds PAS à ces anciens messages ; traite UNIQUEMENT la demande actuelle.]"]
    for r in results:
        lines.append(f"- [{r['role']}] {r['content'][:240]}")
    lines.append("[FIN NOTES]")
    return "\n".join(lines)
