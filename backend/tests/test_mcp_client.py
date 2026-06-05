"""
Tests du client MCP minimal (services.mcp_client).

On lance un VRAI faux serveur MCP (script Python parlant le JSON-RPC sur stdio)
pour valider initialize → tools/list → tools/call de bout en bout, sans dépendance.
"""
import json
import sys
import textwrap

import pytest

from services import mcp_client as mcp


MOCK_SERVER = textwrap.dedent('''
    import sys, json
    def send(o): sys.stdout.write(json.dumps(o)+"\\n"); sys.stdout.flush()
    for line in sys.stdin:
        line = line.strip()
        if not line: continue
        m = json.loads(line); mid = m.get("id"); method = m.get("method")
        if method == "initialize":
            send({"jsonrpc":"2.0","id":mid,"result":{"protocolVersion":"2024-11-05","capabilities":{},"serverInfo":{"name":"mock","version":"1"}}})
        elif method == "notifications/initialized":
            pass
        elif method == "tools/list":
            send({"jsonrpc":"2.0","id":mid,"result":{"tools":[
                {"name":"echo","description":"Renvoie le message","inputSchema":{}},
                {"name":"boom","description":"Erreur","inputSchema":{}}]}})
        elif method == "tools/call":
            p = m.get("params",{}); name = p.get("name"); args = p.get("arguments",{})
            if name == "echo":
                send({"jsonrpc":"2.0","id":mid,"result":{"content":[{"type":"text","text":"echo: "+str(args.get("msg",""))}]}})
            elif name == "boom":
                send({"jsonrpc":"2.0","id":mid,"result":{"content":[{"type":"text","text":"kaboom"}],"isError":True}})
            else:
                send({"jsonrpc":"2.0","id":mid,"error":{"code":-32601,"message":"unknown tool"}})
''')


@pytest.fixture
def mock_server_path(tmp_path):
    p = tmp_path / "mock_mcp.py"
    p.write_text(MOCK_SERVER)
    return str(p)


@pytest.fixture(autouse=True)
def _reset_manager():
    # isole l'état global du gestionnaire entre les tests
    mcp._servers.clear()
    mcp._started = False
    mcp._tools_block = ""
    yield
    mcp._servers.clear()
    mcp._started = False
    mcp._tools_block = ""


# ── Helpers purs ───────────────────────────────────────────────────────────────

class TestParseCalls:
    def test_with_json_args(self):
        calls = mcp.parse_calls('je fais [MCP: filesystem.read_file {"path": "/etc/hostname"}] voilà')
        assert calls == [("filesystem", "read_file", {"path": "/etc/hostname"})]

    def test_without_args(self):
        assert mcp.parse_calls("[MCP: git.status]") == [("git", "status", {})]

    def test_multiple(self):
        calls = mcp.parse_calls('[MCP: a.x {"n": 1}] et [MCP: b.y]')
        assert calls == [("a", "x", {"n": 1}), ("b", "y", {})]

    def test_none(self):
        assert mcp.parse_calls("aucun appel ici") == []


class TestContentToText:
    def test_text_blocks(self):
        assert mcp._content_to_text({"content": [{"type": "text", "text": "hi"}]}) == "hi"

    def test_error_flag(self):
        out = mcp._content_to_text({"content": [{"type": "text", "text": "bad"}], "isError": True})
        assert out.startswith("[erreur outil]")

    def test_empty(self):
        assert mcp._content_to_text({}) == "(aucun contenu)"


def test_load_config(tmp_path, monkeypatch):
    cfg = tmp_path / "mcp.json"
    cfg.write_text(json.dumps({"mcpServers": {"fs": {"command": "x", "args": ["a"]}}}))
    monkeypatch.setattr(mcp, "CONFIG_FILE", cfg)
    assert mcp.load_config() == {"fs": {"command": "x", "args": ["a"]}}


def test_load_config_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(mcp, "CONFIG_FILE", tmp_path / "absent.json")
    assert mcp.load_config() == {}


# ── Bout en bout avec un vrai sous-processus ───────────────────────────────────

@pytest.mark.asyncio
async def test_server_start_lists_and_calls_tools(mock_server_path):
    srv = mcp.MCPServer("mock", sys.executable, [mock_server_path])
    assert await srv.start() is True
    names = {t["name"] for t in srv.tools}
    assert names == {"echo", "boom"}
    assert await srv.call_tool("echo", {"msg": "hi"}) == "echo: hi"
    assert (await srv.call_tool("boom", {})).startswith("[erreur outil]")
    await srv.stop()


@pytest.mark.asyncio
async def test_manager_ensure_started_and_call(mock_server_path, monkeypatch):
    monkeypatch.setattr(mcp, "load_config",
                        lambda: {"mock": {"command": sys.executable, "args": [mock_server_path]}})
    await mcp.ensure_started()
    block = mcp.tools_block()
    assert "mock.echo" in block and "OUTILS MCP" in block
    assert await mcp.call("mock", "echo", {"msg": "x"}) == ("echo: x", 0)
    # serveur inconnu → rc≠0, jamais d'exception
    out, rc = await mcp.call("ghost", "x", {})
    assert rc == 1 and "introuvable" in out
    await mcp.shutdown()
