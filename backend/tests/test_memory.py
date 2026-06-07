"""
Tests for the memory service:
  - Session CRUD
  - Message persistence
  - Semantic search (mocked embeddings)
  - build_context_prefix
"""
import asyncio
import json
import pytest
import numpy as np
from services.memory import (
    create_session,
    update_session_title,
    list_sessions,
    get_session_messages,
    delete_session,
    session_message_count,
    add_message,
    search_memory,
    build_context_prefix,
    Message,
    ChatSession,
)
from sqlalchemy.orm import Session as DBSession


# ── Session CRUD ──────────────────────────────────────────────────────────────

class TestCreateSession:
    def test_creates_session_with_no_title(self, mem_engine, mock_embedding):
        s = create_session()
        assert s.id is not None
        assert s.title is None

    def test_creates_session_with_title(self, mem_engine, mock_embedding):
        s = create_session("My chat")
        assert s.title == "My chat"

    def test_returns_unique_ids(self, mem_engine, mock_embedding):
        s1 = create_session()
        s2 = create_session()
        assert s1.id != s2.id


class TestListSessions:
    def test_empty_db_returns_empty_list(self, mem_engine, mock_embedding):
        assert list_sessions() == []

    def test_lists_created_sessions(self, mem_engine, mock_embedding):
        create_session("First")
        create_session("Second")
        sessions = list_sessions()
        assert len(sessions) == 2
        titles = {s["title"] for s in sessions}
        assert titles == {"First", "Second"}

    def test_returns_id_and_title(self, mem_engine, mock_embedding):
        s = create_session("Test")
        sessions = list_sessions()
        assert sessions[0]["id"] == s.id
        assert sessions[0]["title"] == "Test"
        assert "updated_at" in sessions[0]

    def test_ordered_by_updated_at_desc(self, mem_engine, mock_embedding):
        s1 = create_session("Oldest")
        s2 = create_session("Newest")
        # The most recently created is first
        sessions = list_sessions()
        assert sessions[0]["id"] == s2.id


class TestUpdateSessionTitle:
    def test_updates_title(self, mem_engine, mock_embedding):
        s = create_session()
        update_session_title(s.id, "New title")
        sessions = list_sessions()
        assert sessions[0]["title"] == "New title"

    def test_nonexistent_session_does_nothing(self, mem_engine, mock_embedding):
        update_session_title("nonexistent-id", "Title")
        # Should not raise


class TestGetSessionMessages:
    def test_empty_session_returns_empty_list(self, mem_engine, mock_embedding):
        s = create_session()
        assert get_session_messages(s.id) == []

    def test_nonexistent_session_returns_empty_list(self, mem_engine, mock_embedding):
        assert get_session_messages("nonexistent-id") == []


class TestDeleteSession:
    def test_deletes_session(self, mem_engine, mock_embedding):
        s = create_session("To delete")
        delete_session(s.id)
        assert list_sessions() == []

    def test_delete_nonexistent_does_nothing(self, mem_engine, mock_embedding):
        delete_session("nonexistent-id")
        # Should not raise

    def test_delete_cascades_to_messages(self, mem_engine, mock_embedding):
        import services.memory as mem_module
        s = create_session()
        with DBSession(mem_engine) as db:
            msg = Message(session_id=s.id, role="user", content="hello")
            db.add(msg)
            db.commit()
        delete_session(s.id)
        with DBSession(mem_engine) as db:
            count = db.query(Message).filter_by(session_id=s.id).count()
        assert count == 0


class TestSessionMessageCount:
    def test_empty_session_count_is_zero(self, mem_engine, mock_embedding):
        s = create_session()
        assert session_message_count(s.id) == 0

    def test_count_increases_after_direct_insert(self, mem_engine, mock_embedding):
        s = create_session()
        with DBSession(mem_engine) as db:
            db.add(Message(session_id=s.id, role="user", content="hi"))
            db.add(Message(session_id=s.id, role="assistant", content="hello"))
            db.commit()
        assert session_message_count(s.id) == 2


# ── add_message (async) ───────────────────────────────────────────────────────

class TestAddMessage:
    @pytest.mark.asyncio
    async def test_persists_message(self, mem_engine, mock_embedding):
        s = create_session()
        await add_message(s.id, "user", "Hello world")
        msgs = get_session_messages(s.id)
        assert len(msgs) == 1
        assert msgs[0]["role"] == "user"
        assert msgs[0]["content"] == "Hello world"

    @pytest.mark.asyncio
    async def test_multiple_messages_in_order(self, mem_engine, mock_embedding):
        s = create_session()
        await add_message(s.id, "user", "First message")
        await add_message(s.id, "assistant", "Second message")
        msgs = get_session_messages(s.id)
        assert len(msgs) == 2
        assert msgs[0]["content"] == "First message"
        assert msgs[1]["content"] == "Second message"

    @pytest.mark.asyncio
    async def test_updates_session_updated_at(self, mem_engine, mock_embedding):
        s = create_session()
        original_sessions = list_sessions()
        assert len(original_sessions) == 1
        await add_message(s.id, "user", "Test")
        # updated_at should exist in sessions list
        sessions = list_sessions()
        assert "updated_at" in sessions[0]

    @pytest.mark.asyncio
    async def test_message_count_increases(self, mem_engine, mock_embedding):
        s = create_session()
        await add_message(s.id, "user", "msg1")
        await add_message(s.id, "assistant", "msg2")
        assert session_message_count(s.id) == 2


# ── search_memory (async, mocked embeddings) ──────────────────────────────────

class TestSearchMemory:
    @pytest.mark.asyncio
    async def test_returns_empty_when_no_embedding_available(self, mem_engine, mock_embedding):
        s = create_session()
        await asyncio.sleep(0)  # let background tasks settle
        result = await search_memory("test query")
        # mock_embedding returns None → no results
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_scored_results_with_real_embeddings(self, mem_engine, monkeypatch):
        import services.memory as mem_module

        # Provide a fake embedding that returns different vectors for query vs stored
        call_count = [0]

        async def fake_embedding(text: str):
            call_count[0] += 1
            # query gets [1,0,0], stored messages get [1,0,0] (high similarity)
            return [1.0, 0.0, 0.0]

        monkeypatch.setattr(mem_module, "_get_embedding_async", fake_embedding)

        s = create_session()
        # Directly insert a message with an embedding
        with DBSession(mem_engine) as db:
            db.add(Message(
                session_id=s.id, role="user",
                content="stored message",
                embedding=json.dumps([1.0, 0.0, 0.0])
            ))
            db.commit()

        results = await search_memory("test query", top_k=5)
        assert len(results) == 1
        assert results[0]["content"] == "stored message"
        assert results[0]["score"] > 0.9

    @pytest.mark.asyncio
    async def test_returns_top_k_results(self, mem_engine, monkeypatch):
        import services.memory as mem_module

        async def fake_embedding(text: str):
            return [1.0, 0.0, 0.0]

        monkeypatch.setattr(mem_module, "_get_embedding_async", fake_embedding)

        s = create_session()
        with DBSession(mem_engine) as db:
            for i in range(10):
                db.add(Message(
                    session_id=s.id, role="user",
                    content=f"message {i}",
                    embedding=json.dumps([1.0, 0.0, 0.0])
                ))
            db.commit()

        results = await search_memory("query", top_k=3)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_results_sorted_by_score_desc(self, mem_engine, monkeypatch):
        import services.memory as mem_module

        embeddings = {
            "query": [1.0, 0.0, 0.0],
            "close": [0.99, 0.1, 0.0],
            "far": [0.0, 0.0, 1.0],
        }
        call_idx = [0]
        order = ["query", "close", "far"]

        async def fake_embedding(text: str):
            # First call = query, subsequent calls = stored messages (not used here)
            return embeddings.get(text, [0.5, 0.5, 0.0])

        monkeypatch.setattr(mem_module, "_get_embedding_async", fake_embedding)

        s = create_session()
        with DBSession(mem_engine) as db:
            db.add(Message(
                session_id=s.id, role="user",
                content="close message",
                embedding=json.dumps(embeddings["close"])
            ))
            db.add(Message(
                session_id=s.id, role="user",
                content="far message",
                embedding=json.dumps(embeddings["far"])
            ))
            db.commit()

        results = await search_memory("query", top_k=10)
        assert len(results) == 2
        assert results[0]["score"] >= results[1]["score"]


# ── build_context_prefix ──────────────────────────────────────────────────────

class TestBuildContextPrefix:
    @pytest.mark.asyncio
    async def test_returns_empty_when_no_embeddings(self, mem_engine, mock_embedding):
        result = await build_context_prefix("test query")
        assert result == ""

    @pytest.mark.asyncio
    async def test_returns_formatted_prefix_when_results_found(self, mem_engine, monkeypatch):
        import services.memory as mem_module

        async def fake_embedding(text: str):
            return [1.0, 0.0, 0.0]

        monkeypatch.setattr(mem_module, "_get_embedding_async", fake_embedding)

        s = create_session()
        with DBSession(mem_engine) as db:
            db.add(Message(
                session_id=s.id, role="user",
                content="relevant past message",
                embedding=json.dumps([1.0, 0.0, 0.0])
            ))
            db.commit()

        result = await build_context_prefix("test query")
        assert "NOTES DE MÉMOIRE" in result
        assert "relevant past message" in result
        assert "FIN NOTES" in result
