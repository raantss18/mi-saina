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
import shutil
from pathlib import Path

CONFIG_FILE = Path(os.path.expanduser("~/.config/mi-saina/mcp.json"))
_PROTOCOL_VERSION = "2024-11-05"

# Appel d'outil dans la réponse du modèle : [MCP: serveur.outil {"arg": "val"}]
# Les arguments JSON sont optionnels : [MCP: serveur.outil]
# On tolère les préfixes que les modèles locaux improvisent (FETCH, TOOL, CALL…)
# pour ne pas rater l'appel ; [EXEC:] et [SEARCH:] restent gérés à part.
MCP_RE = re.compile(
    r'\[(?:MCP|FETCH|TOOL|OUTIL|CALL)\s*:\s*([\w.-]+?)\.([\w.-]+)\s*([^\]]*?)\s*\]',
    re.IGNORECASE | re.DOTALL)


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

    def _spawn_env(self) -> dict:
        """Env du serveur, avec un PATH élargi aux binaires utilisateur.
        Les services systemd ont un PATH restreint ; or des lanceurs courants
        (uvx, pipx, npm global…) vivent dans ~/.local/bin — on les rend trouvables
        sinon un serveur comme `uvx mcp-server-git` ne démarre pas."""
        env = {**os.environ, **self.env}
        extra = [
            os.path.expanduser("~/.local/bin"),
            os.path.expanduser("~/bin"),
            os.path.expanduser("~/.cargo/bin"),
            "/usr/local/bin",
        ]
        existing = env.get("PATH", "").split(os.pathsep)
        env["PATH"] = os.pathsep.join(
            [p for p in extra if p not in existing] + existing)
        return env

    async def start(self) -> bool:
        """Lance le serveur et récupère ses outils. False si échec (toléré)."""
        try:
            env = self._spawn_env()
            # Résout le binaire dans le PATH élargi (create_subprocess_exec n'utilise
            # pas le PATH de `env`, mais celui du process courant).
            resolved = shutil.which(self.command, path=env["PATH"]) or self.command
            self.proc = await asyncio.create_subprocess_exec(
                resolved, *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                env=env,
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
    has_fetch = False
    scoped: list[tuple[str, list[str]]] = []   # serveurs limités à des dossiers
    for name, srv in _servers.items():
        roots = [a for a in srv.args if a.startswith("/") or a.startswith("~")]
        is_fs = any(t["name"] in ("list_directory", "read_file", "directory_tree") for t in srv.tools)
        if is_fs and roots:
            scoped.append((name, roots))
        for t in srv.tools:
            desc = t.get("description") or ""
            if "DEPRECATED" in desc.upper():         # on n'expose pas les outils dépréciés
                continue
            if t["name"] == "fetch":
                has_fetch = True
            lines.append(f"- {name}.{t['name']} : {_short_desc(desc)}")

    # Périmètre des serveurs de fichiers : le modèle DOIT savoir qu'ils sont
    # limités à certains dossiers, et utiliser le SHELL (accès complet) ailleurs.
    if scoped:
        scope_txt = " ; ".join(f"'{n}' → {', '.join(r)}" for n, r in scoped)
        lines.append(
            f"\nPÉRIMÈTRE FICHIERS : les serveurs MCP de fichiers sont LIMITÉS à : {scope_txt}. "
            "Pour tout ce qui est HORS de ces dossiers — explorer/lister/analyser le home (~/), "
            "trouver des fichiers inutiles ou redondants, df, du, ls, find sur le système — "
            "utilise TOUJOURS le SHELL [EXEC: …] qui a un accès COMPLET, et NON les outils MCP "
            "de fichiers. N'utilise filesystem.* que pour les dossiers autorisés ci-dessus.")

    # Consignes d'usage ciblées (le modèle local sait mieux quoi déclencher).
    if has_fetch:
        # Guidage TERSE et SANS exemple concret : les petits modèles prennent un
        # exemple de tâche pour une vraie demande de l'utilisateur (contamination).
        lines.append(
            "\nSI ET SEULEMENT SI l'utilisateur fournit un site/URL dans SON message "
            "courant : récupère le contenu avec [MCP: fetch.fetch {\"url\": \"<l'URL "
            "EXACTE de l'utilisateur, https:// ajouté si absent>\"}]. Ne résume QUE le "
            "contenu réellement renvoyé ; si le fetch échoue, DIS-LE — n'invente jamais "
            "de contenu et ne réutilise pas un site d'une demande précédente. "
            "N'invoque AUCUN fetch si l'utilisateur n'a pas donné d'URL.")
        lines.append(
            "Pour télécharger des fichiers d'une page DEMANDÉE par l'utilisateur : "
            "(1) fetch la page pour LIRE les vrais liens ; (2) télécharge avec le shell "
            "vers un dossier dédié — [EXEC: mkdir -p <dossier> && wget -q -P <dossier> "
            "\"<url-réelle-vue-dans-la-page>\"]. N'invente jamais de lien.")
    return "\n".join(lines)


def tools_block() -> str:
    """Bloc d'outils pour le system prompt (vide si MCP off / aucun serveur)."""
    return _tools_block


def _required_arg(server: str, tool: str) -> str | None:
    """Nom de l'argument requis d'un outil (depuis son schéma), pour mapper une
    valeur nue (« https://… ») fournie sans JSON par un petit modèle."""
    srv = _servers.get(server)
    if srv:
        for t in srv.tools:
            if t.get("name") == tool:
                schema = t.get("inputSchema") or {}
                req = schema.get("required") or []
                if req:
                    return req[0]
                props = list((schema.get("properties") or {}).keys())
                if len(props) == 1:
                    return props[0]
    return {"fetch": "url"}.get(tool)   # repli courant


def _ensure_scheme(u: str) -> str:
    u = (u or "").strip()
    if u and not re.match(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://", u):
        return "https://" + u
    return u


def _normalize_quotes(s: str) -> str:
    return (s.replace("“", '"').replace("”", '"')
             .replace("‘", "'").replace("’", "'"))


def parse_calls(text: str) -> list[tuple[str, str, dict]]:
    """Extrait les appels [MCP: serveur.outil {json}] ou [MCP: fetch.fetch https://…]
    → [(serveur, outil, args)]. Tolérant : JSON malformé, guillemets typographiques,
    valeur nue, URL sans schéma (les petits modèles locaux improvisent souvent)."""
    calls = []
    for srv, tool, raw in MCP_RE.findall(text):
        raw = (raw or "").strip()
        args: dict = {}
        if raw:
            try:
                parsed = json.loads(_normalize_quotes(raw))
                if isinstance(parsed, dict):
                    args = parsed
            except Exception:
                # Pas du JSON → valeur nue mappée sur l'argument requis de l'outil.
                val = raw.strip().strip("`\"' ")
                key = _required_arg(srv, tool)
                if key and val and not val.startswith("{"):
                    args = {key: val}
        # URL sans schéma → ajoute https:// (fetch et assimilés).
        if isinstance(args.get("url"), str):
            args["url"] = _ensure_scheme(args["url"])
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
