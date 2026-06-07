"""RAG local : découpage, indexation et recherche (DB temporaire, embeddings simulés)."""
import pytest
from sqlalchemy import create_engine

from services import rag


def test_chunk_short():
    assert rag._chunk("court") == ["court"]
    assert rag._chunk("") == []


def test_chunk_splits_large():
    text = "\n\n".join(f"Paragraphe {i} " + "x" * 300 for i in range(10))
    chunks = rag._chunk(text, size=500, overlap=50)
    assert len(chunks) > 1
    assert all(len(c) <= 800 for c in chunks)  # ~size, marge pour la jointure


VOCAB = ["python", "pomme", "voiture", "secret"]


@pytest.fixture
def temp_rag(monkeypatch, tmp_path):
    eng = create_engine(f"sqlite:///{tmp_path / 'rag.db'}")
    rag.Base.metadata.create_all(eng)
    monkeypatch.setattr(rag, "engine", eng)

    async def fake_emb(text: str):
        t = text.lower()
        v = [float(t.count(w)) for w in VOCAB]
        return v if any(v) else [0.01, 0.0, 0.0, 0.0]

    monkeypatch.setattr(rag, "_get_embedding_async", fake_emb)
    return rag


@pytest.mark.asyncio
async def test_index_and_search(temp_rag, tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "a.txt").write_text("Le python est un langage génial pour le python.")
    (docs / "b.txt").write_text("J'aime la pomme et la tarte aux pommes.")

    events = []
    async for ev in temp_rag.index_folder(str(docs)):
        events.append(ev)
    assert any(ev.get("done") for ev in events)
    assert temp_rag.status()["files"] == 2

    res = await temp_rag.search("python", top_k=2)
    assert res and "python" in res[0]["content"].lower()

    res2 = await temp_rag.search("pomme", top_k=2)
    assert res2 and "pomme" in res2[0]["content"].lower()


@pytest.mark.asyncio
async def test_index_missing_folder(temp_rag, tmp_path):
    events = [ev async for ev in temp_rag.index_folder(str(tmp_path / "nope"))]
    assert any("error" in ev for ev in events)


@pytest.mark.asyncio
async def test_clear(temp_rag, tmp_path):
    docs = tmp_path / "d"; docs.mkdir()
    (docs / "x.txt").write_text("secret code 4731")
    async for _ in temp_rag.index_folder(str(docs)):
        pass
    assert temp_rag.status()["chunks"] >= 1
    temp_rag.clear()
    assert temp_rag.status()["chunks"] == 0
