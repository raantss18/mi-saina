import pytest
from sqlalchemy import create_engine
import services.memory as memory_module
from services.memory import Base


@pytest.fixture
def mem_engine(monkeypatch):
    """Replace the memory engine with a fresh in-memory SQLite for each test."""
    test_engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(test_engine)
    monkeypatch.setattr(memory_module, "engine", test_engine)
    yield test_engine
    Base.metadata.drop_all(test_engine)


@pytest.fixture
def mock_embedding(monkeypatch):
    """Disable real Ollama embedding calls."""
    async def _no_embedding(text: str):
        return None

    monkeypatch.setattr(memory_module, "_get_embedding_async", _no_embedding)
