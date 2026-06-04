"""
Tests for services/web_search.py.
DDGS is mocked — no real network calls.
"""
import pytest
from unittest.mock import MagicMock, patch


class TestSearchWeb:
    def test_returns_formatted_results(self):
        from services.web_search import search_web

        fake_results = [
            {"title": "Result 1", "href": "https://example.com", "body": "Snippet 1"},
            {"title": "Result 2", "href": "https://example2.com", "body": "Snippet 2"},
        ]

        mock_ddgs = MagicMock()
        mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
        mock_ddgs.__exit__ = MagicMock(return_value=False)
        mock_ddgs.text = MagicMock(return_value=iter(fake_results))

        with patch("services.web_search.DDGS", return_value=mock_ddgs):
            results = search_web("test query")

        assert len(results) == 2
        assert results[0]["title"] == "Result 1"
        assert results[0]["url"] == "https://example.com"
        assert results[0]["snippet"] == "Snippet 1"

    def test_returns_empty_list_on_no_results(self):
        from services.web_search import search_web

        mock_ddgs = MagicMock()
        mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
        mock_ddgs.__exit__ = MagicMock(return_value=False)
        mock_ddgs.text = MagicMock(return_value=iter([]))

        with patch("services.web_search.DDGS", return_value=mock_ddgs):
            results = search_web("empty results query")

        assert results == []

    def test_respects_max_results_setting(self, monkeypatch):
        from config import settings
        from services.web_search import search_web

        monkeypatch.setattr(settings, "MAX_SEARCH_RESULTS", 3)

        mock_ddgs = MagicMock()
        mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
        mock_ddgs.__exit__ = MagicMock(return_value=False)
        mock_ddgs.text = MagicMock(return_value=iter([]))

        with patch("services.web_search.DDGS", return_value=mock_ddgs):
            search_web("query")

        mock_ddgs.text.assert_called_once_with("query", max_results=3)

    def test_handles_missing_fields_gracefully(self):
        from services.web_search import search_web

        fake_results = [
            {"title": None, "href": None, "body": None},
        ]

        mock_ddgs = MagicMock()
        mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
        mock_ddgs.__exit__ = MagicMock(return_value=False)
        mock_ddgs.text = MagicMock(return_value=iter(fake_results))

        with patch("services.web_search.DDGS", return_value=mock_ddgs):
            results = search_web("query")

        assert len(results) == 1
        assert results[0]["title"] is None
        assert results[0]["url"] is None
        assert results[0]["snippet"] is None
