"""Robustesse du parsing des appels MCP (les petits modèles improvisent le format)."""
from services.mcp_client import parse_calls


def test_clean_json():
    calls = parse_calls('[MCP: fetch.fetch {"url": "https://example.com"}]')
    assert calls == [("fetch", "fetch", {"url": "https://example.com"})]


def test_bare_url_gets_scheme():
    calls = parse_calls("[MCP: fetch.fetch raantss18.github.io/antsamath]")
    assert calls == [("fetch", "fetch", {"url": "https://raantss18.github.io/antsamath"})]


def test_url_without_scheme_in_json():
    calls = parse_calls('[MCP: fetch.fetch {"url": "apmep.fr"}]')
    assert calls[0][2]["url"] == "https://apmep.fr"


def test_existing_scheme_kept():
    calls = parse_calls('[MCP: fetch.fetch http://example.com]')
    assert calls[0][2]["url"] == "http://example.com"


def test_smart_quotes():
    calls = parse_calls('[MCP: fetch.fetch {“url”: “https://a.com”}]')
    assert calls[0][2]["url"] == "https://a.com"


def test_alt_prefix_fetch():
    calls = parse_calls("[FETCH: fetch.fetch https://a.com]")
    assert calls == [("fetch", "fetch", {"url": "https://a.com"})]


def test_filesystem_unaffected():
    calls = parse_calls('[MCP: filesystem.read_file {"path": "/tmp/x"}]')
    assert calls == [("filesystem", "read_file", {"path": "/tmp/x"})]


def test_no_args_stays_empty():
    calls = parse_calls("[MCP: git.status]")
    assert calls == [("git", "status", {})]
