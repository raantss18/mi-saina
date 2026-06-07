"""RAG local : indexe un dossier de documents et répond aux questions par
similarité sémantique. Réutilise les embeddings Ollama (EMBED_MODEL) et la base
SQLite de la mémoire. 100 % local, aligné petite VRAM (corpus personnel)."""
import asyncio
import json
from pathlib import Path

import numpy as np
from sqlalchemy import Column, Integer, String, Text, delete
from sqlalchemy.orm import Session

from services.memory import engine, Base, _get_embedding_async
from services import documents


class RagChunk(Base):
    __tablename__ = "rag_chunks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    path = Column(String, nullable=False, index=True)
    chunk_index = Column(Integer, default=0)
    content = Column(Text, nullable=False)
    embedding = Column(Text, nullable=True)


Base.metadata.create_all(engine)


def _chunk(text: str, size: int = 1000, overlap: int = 150) -> list[str]:
    """Découpe en blocs ~size caractères sur des frontières de paragraphe,
    avec un léger recouvrement pour ne pas couper le contexte."""
    text = text.strip()
    if len(text) <= size:
        return [text] if text else []
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks, cur = [], ""
    for p in paras:
        if len(cur) + len(p) + 2 <= size:
            cur = f"{cur}\n\n{p}" if cur else p
        else:
            if cur:
                chunks.append(cur)
            if len(p) <= size:
                cur = p
            else:  # paragraphe géant → découpe dure avec recouvrement
                for i in range(0, len(p), size - overlap):
                    chunks.append(p[i:i + size])
                cur = ""
    if cur:
        chunks.append(cur)
    return chunks


async def index_folder(folder: str, max_files: int = 300, max_chunks_per_file: int = 80):
    """Indexe (ou ré-indexe) les documents d'un dossier. Générateur de progression."""
    root = Path(folder).expanduser()
    if not root.exists() or not root.is_dir():
        yield {"error": f"Dossier introuvable : {folder}"}
        return
    files = [p for p in sorted(root.rglob("*"))
             if p.is_file() and documents.is_supported(p.name)]
    files = files[:max_files]
    if not files:
        yield {"error": f"Aucun document pris en charge dans {folder}"}
        return

    yield {"total": len(files), "indexed": 0, "status": f"{len(files)} document(s) à indexer…"}
    indexed = 0
    for f in files:
        text, err = await asyncio.to_thread(documents.extract_text, str(f), 200000)
        if err:
            yield {"indexed": indexed, "total": len(files), "status": f"⏭ {f.name} : {err}"}
            continue
        chunks = _chunk(text)[:max_chunks_per_file]
        # Remplace les chunks existants de ce fichier (ré-indexation idempotente).
        with Session(engine) as db:
            db.execute(delete(RagChunk).where(RagChunk.path == str(f)))
            db.commit()
        added = 0
        for i, ch in enumerate(chunks):
            emb = await _get_embedding_async(ch)
            if emb is None:
                continue
            with Session(engine) as db:
                db.add(RagChunk(path=str(f), chunk_index=i, content=ch, embedding=json.dumps(emb)))
                db.commit()
            added += 1
        indexed += 1
        yield {"indexed": indexed, "total": len(files), "status": f"✅ {f.name} ({added} extraits)"}
    yield {"done": True, "indexed": indexed, "total": len(files)}


async def search(query: str, top_k: int = 5) -> list[dict]:
    q_raw = await _get_embedding_async(query)
    if q_raw is None:
        return []
    q = np.array(q_raw, dtype=float)
    qn = np.linalg.norm(q) or 1.0
    results = []
    with Session(engine) as db:
        rows = db.query(RagChunk).filter(RagChunk.embedding.isnot(None)).all()
        for r in rows:
            try:
                v = np.array(json.loads(r.embedding), dtype=float)
            except Exception:
                continue
            score = float(np.dot(q, v) / (qn * (np.linalg.norm(v) or 1.0)))
            results.append({"path": r.path, "content": r.content, "score": score})
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


def status() -> dict:
    with Session(engine) as db:
        rows = db.query(RagChunk.path).all()
    paths = {p[0] for p in rows}
    return {"chunks": len(rows), "files": len(paths)}


def clear() -> None:
    with Session(engine) as db:
        db.execute(delete(RagChunk))
        db.commit()
