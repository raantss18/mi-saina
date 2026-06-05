"""
Client MCP (Model Context Protocol) minimal — local & sans dépendance.

MCP est un standard ouvert pour exposer des « outils » à un assistant via des
serveurs (filesystem, git, fetch, sqlite…). Ici on parle le sous-ensemble
nécessaire du protocole JSON-RPC sur stdio (messages JSON délimités par des
retours à la ligne) : initialize → tools/list → tools/call.

Tout est OPT-IN (settings.MCP_ENABLED) et tolérant : un serveur mal configuré ou
absent est simplement ignoré, jamais bloquant pour le chat normal.

Config : ~/.config/mi-saina/mcp.json (même format que Claude Desktop) :
    {
      "mcpServers": {
        "filesystem": {
          "command": "npx",
          "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/moi"],
          "env": {}
        }
      }
    }
"""

import asyncio
import json
import os
import re
from pathlib import Path

CONFIG_FILE = Path(os.path.expanduser("~/.config/mi-saina/mcp.json"))
_PROTOCOL_VERSION = "2024-11-05"

# Appel d'outil dans la réponse du modèle : [MCP: serveur.outil {"arg": "val"}]
# Les arguments JSON sont optionnels : [MCP: serveur.outil]
MCP_RE = re.compile(r'\[MCP:\s*([\w.-]+?)\.([\w.-]+?)\s*(\{.*?\})?\s*\]', re.DOTALL)


def load_config() -> dict:
    """Retourne le dict {nom: {command, args, env}} ou {} si absent/invalide."""
    if not CONFIG_FILE.exists():
        return {}
    try:
        data = json.loads(CONFIG_FILE.read_text())
    except Exception:
        return {}
    servers = data.get("mcpServers", data)   # tolère les deux formes
    return servers if isinstance(servers, dict) else {}


class MCPServer:
    """Un serveur MCP lancé en sous-processus, piloté en JSON-RPC sur stdio."""

    def __init__(self, name: str, command: str, args: list[str], env: dict | None = None):
        self.name = name
        self.command = command
        self.args = args or []
        self.env = env or {}
        self.proc: asyncio.subprocess.Process | None = None
        self.tools: list[dict] = []
        self._id = 0
        self._lock = asyncio.Lock()      # une requête en vol à la fois

    async def start(self) -> bool:
        """Lance le serveur et récupère ses outils. False si échec (toléré)."""
        try:
            self.proc = await asyncio.create_subprocess_exec(
                self.command, *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                env={**os.environ, **self.env},
            )
            await self._rpc("initialize", {
                "protocolVersion": _PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "mi-saina", "version": "1.x"},
            })
            await self._notify("notifications/initialized")
            res = await self._rpc("tools/list", {})
            self.tools = res.get("tools", []) or []
            return True
        except Exception:
            await self.stop()
            return False

    async def stop(self):
        if self.proc and self.proc.returncode is None:
            try:
                self.proc.terminate()
            except Exception:
                pass
        self.proc = None

    async def _notify(self, method: str, params: dict | None = None):
        assert self.proc and self.proc.stdin
        msg = {"jsonrpc": "2.0", "method": method, "params": params or {}}
        self.proc.stdin.write((json.dumps(msg) + "\n").encode())
        await self.proc.stdin.drain()

    async def _rpc(self, method: str, params: dict | None = None, timeout: float = 20.0) -> dict:
        assert self.proc and self.proc.stdin and self.proc.stdout
        self._id += 1
        mid = self._id
        msg = {"jsonrpc": "2.0", "id": mid, "method": method, "params": params or {}}
        self.proc.stdin.write((json.dumps(msg) + "\n").encode())
        await self.proc.stdin.drain()
        # Lire jusqu'à la réponse portant notre id (on ignore notifications/logs)
        while True:
            line = await asyncio.wait_for(self.proc.stdout.readline(), timeout)
            if not line:
                raise RuntimeError(f"serveur MCP « {self.name} » fermé")
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except Exception:
                continue
            if data.get("id") == mid:
                if "error" in data:
                    raise RuntimeError(data["error"].get("message", "erreur MCP"))
                return data.get("result", {}) or {}

    async def call_tool(self, tool: str, arguments: dict) -> str:
        """Appelle un outil et retourne son texte de résultat."""
        async with self._lock:
            res = await self._rpc("tools/call", {"name": tool, "arguments": arguments or {}})
        return _content_to_text(res)


def _content_to_text(result: dict) -> str:
    """Aplati le `content` MCP en texte lisible pour le modèle."""
    parts = []
    for block in result.get("content", []) or []:
        if isinstance(block, dict):
            if block.get("type") == "text":
                parts.append(block.get("text", ""))
            else:
                parts.append(json.dumps(block, ensure_ascii=False))
        else:
            parts.append(str(block))
    text = "\n".join(p for p in parts if p)
    if result.get("isError"):
        text = f"[erreur outil] {text}"
    return text or "(aucun contenu)"


# ── Gestionnaire global (lazy, mis en cache) ──────────────────────────────────
_servers: dict[str, MCPServer] = {}
_started = False
_tools_block = ""


async def ensure_started() -> None:
    """Démarre les serveurs configurés (une fois) et prépare le bloc d'outils."""
    global _started, _tools_block
    if _started:
        return
    _started = True
    for name, cfg in load_config().items():
        cmd = (cfg or {}).get("command")
        if not cmd:
            continue
        srv = MCPServer(name, cmd, cfg.get("args", []), cfg.get("env", {}))
        if await srv.start():
            _servers[name] = srv
    _tools_block = _build_tools_block()


def _short_desc(text: str, limit: int = 90) -> str:
    """Première phrase d'une description, tronquée — pour un prompt compact."""
    text = " ".join((text or "").split())          # aplati les espaces/retours
    first = text.split(". ", 1)[0]                   # 1re phrase
    if len(first) > limit:
        first = first[:limit].rstrip() + "…"
    return first


def _build_tools_block() -> str:
    if not _servers:
        return ""
    # IMPORTANT : ces outils s'AJOUTENT au shell, ils ne le remplacent pas.
    # On le dit explicitement pour qu'un modèle local ne croie pas avoir « perdu »
    # l'accès terminal en voyant cette liste.
    lines = [
        "## OUTILS MCP (optionnels, EN PLUS du shell)",
        "Tu conserves ton accès complet au terminal via [EXEC: commande]. "
        "Les outils ci-dessous sont un BONUS, à utiliser seulement si c'est plus "
        "pratique que le shell. Syntaxe : [MCP: serveur.outil {\"arg\": \"valeur\"}] "
        "(JSON facultatif).",
    ]
    for name, srv in _servers.items():
        for t in srv.tools:
            desc = t.get("description") or ""
            if "DEPRECATED" in desc.upper():         # on n'expose pas les outils dépréciés
                continue
            lines.append(f"- {name}.{t['name']} : {_short_desc(desc)}")
    return "\n".join(lines)


def tools_block() -> str:
    """Bloc d'outils pour le system prompt (vide si MCP off / aucun serveur)."""
    return _tools_block


def parse_calls(text: str) -> list[tuple[str, str, dict]]:
    """Extrait les appels [MCP: serveur.outil {json}] → [(serveur, outil, args)]."""
    calls = []
    for srv, tool, raw_args in MCP_RE.findall(text):
        args = {}
        if raw_args:
            try:
                args = json.loads(raw_args)
            except Exception:
                args = {}
        calls.append((srv, tool, args))
    return calls


async def call(server: str, tool: str, arguments: dict) -> tuple[str, int]:
    """Appelle un outil MCP. Retourne (texte, rc) ; rc≠0 si erreur/inconnu."""
    srv = _servers.get(server)
    if srv is None:
        return (f"serveur MCP « {server} » introuvable ou non démarré", 1)
    try:
        return (await srv.call_tool(tool, arguments), 0)
    except Exception as e:
        return (f"échec de l'appel MCP {server}.{tool} : {e}", 1)


async def shutdown() -> None:
    for srv in _servers.values():
        await srv.stop()
    _servers.clear()
