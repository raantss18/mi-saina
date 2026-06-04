"""
Index des applications installées (fichiers .desktop) + résolution floue.

Permet d'ouvrir une appli par un nom APPROXIMATIF (« mission-center » →
binaire réel « missioncenter », appli « Mission Center »), y compris Flatpak,
au lieu d'exécuter brutalement un binaire inexistant dans le terminal.
"""

import os
import re
import shutil
import time
from glob import glob

# Dossiers standard des .desktop (système, utilisateur, Flatpak)
_DESKTOP_DIRS = [
    "/usr/share/applications",
    "/usr/local/share/applications",
    os.path.expanduser("~/.local/share/applications"),
    "/var/lib/flatpak/exports/share/applications",
    os.path.expanduser("~/.local/share/flatpak/exports/share/applications"),
]

_FIELD_CODES = re.compile(r"%[a-zA-Z%]")

_cache: dict = {"ts": 0.0, "apps": []}
_CACHE_TTL = 30.0   # secondes


def _norm(s: str) -> str:
    """Normalise pour comparaison : minuscule, sans séparateurs."""
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def _clean_exec(exec_line: str) -> str:
    """Retire les field codes (%U %F %i…) d'une ligne Exec."""
    return _FIELD_CODES.sub("", exec_line).strip()


def _parse_desktop(path: str) -> dict | None:
    name = exec_cmd = ""
    terms: list[str] = []          # GenericName / Keywords (toutes locales)
    terminal = nodisplay = hidden = False
    app_type = ""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            in_entry = False
            for line in f:
                line = line.rstrip("\n")
                if line.startswith("["):
                    in_entry = line.strip() == "[Desktop Entry]"
                    continue
                if not in_entry or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                base = key.split("[")[0]      # "Name[fr]" -> "Name"
                if key == "Name" and not name:           # nom canonique (non localisé)
                    name = val.strip()
                elif base == "Exec" and not exec_cmd:
                    exec_cmd = _clean_exec(val)
                elif base == "Name" or base in ("GenericName", "Keywords", "Comment"):
                    terms.append(val.strip())            # noms localisés + descriptifs → recherche
                elif key == "Terminal":
                    terminal = val.strip().lower() == "true"
                elif key == "NoDisplay":
                    nodisplay = val.strip().lower() == "true"
                elif key == "Hidden":
                    hidden = val.strip().lower() == "true"
                elif key == "Type":
                    app_type = val.strip()
    except OSError:
        return None
    if app_type and app_type != "Application":
        return None
    if not exec_cmd or hidden:
        return None
    app_id = os.path.basename(path)[:-len(".desktop")] if path.endswith(".desktop") else os.path.basename(path)
    bin_name = os.path.basename(exec_cmd.split()[0]) if exec_cmd.split() else ""
    return {
        "id": app_id,
        "name": name or app_id,
        "exec": exec_cmd,
        "bin": bin_name,
        "terms": " ".join(terms),
        "terminal": terminal,
        "nodisplay": nodisplay,
        "path": path,
    }


def index_apps(force: bool = False) -> list[dict]:
    """Liste des applications (.desktop), mise en cache (TTL)."""
    now = time.time()
    if not force and (now - _cache["ts"]) < _CACHE_TTL and _cache["apps"]:
        return _cache["apps"]
    seen: dict[str, dict] = {}
    for d in _DESKTOP_DIRS:
        for path in glob(os.path.join(d, "*.desktop")):
            entry = _parse_desktop(path)
            if entry and entry["id"] not in seen:
                seen[entry["id"]] = entry
    apps = list(seen.values())
    _cache.update(ts=now, apps=apps)
    return apps


def _gui_bins() -> set[str]:
    return {a["bin"] for a in index_apps() if a["bin"] and not a["terminal"] and not a["nodisplay"]}


def is_gui_binary(token: str) -> bool:
    """`token` est-il le binaire d'une application graphique installée ?"""
    if not token:
        return False
    return os.path.basename(token) in _gui_bins()


def _score(query_norm: str, query_raw: str, entry: dict) -> float:
    import difflib
    best = 0.0
    # Champs « identité » (nom exact attendu) : poids fort
    for field in (entry["name"], entry["id"], entry["bin"]):
        fn = _norm(field)
        if not fn:
            continue
        if query_norm == fn:
            return 1.0
        # l'utilisateur a tapé une portion significative du nom de l'appli
        if len(query_norm) >= 3 and query_norm in fn:
            best = max(best, 0.92)
        # le nom de l'appli (assez long) apparaît dans la requête
        if len(fn) >= 4 and fn in query_norm:
            best = max(best, 0.85)
        best = max(best, difflib.SequenceMatcher(None, query_norm, fn).ratio())
    # Champs « descriptifs » (GenericName/Keywords/Comment, ex. « gestionnaire de
    # fichiers ») : on n'accepte qu'un mot entier de la requête présent, poids modéré.
    terms_norm = _norm(entry.get("terms", ""))
    if terms_norm:
        words = [_norm(w) for w in re.split(r"[^a-zA-Z0-9]+", query_raw)]
        words = [w for w in words if len(w) >= 4]
        if words and all(w in terms_norm for w in words):
            best = max(best, 0.8)
    return best


def resolve_app(query: str, threshold: float = 0.7) -> tuple[str, str] | None:
    """Retrouve l'application correspondant à un nom approximatif.

    Retourne (commande_de_lancement, nom_affiché) ou None.
    Préfère les applis graphiques (Terminal=false) à profil égal.
    """
    qn = _norm(query)
    if not qn:
        return None
    best = None
    best_score = 0.0
    for a in index_apps():
        if a["nodisplay"]:
            continue
        s = _score(qn, query, a)
        if a["terminal"]:
            s -= 0.05   # léger malus : on privilégie le GUI
        if s > best_score:
            best, best_score = a, s
    if best and best_score >= threshold:
        return best["exec"], best["name"]
    return None


def looks_like_app_launch(cmd: str) -> bool:
    """Commande qui RESSEMBLE à un lancement d'appli mais dont le binaire
    n'existe pas (donc à résoudre plutôt qu'à exécuter brutalement)."""
    s = cmd.strip()
    if not s or any(c in s for c in "|&;<>$`()*{}"):
        return False
    toks = s.split()
    first = toks[0]
    if first in {"cd", "echo", "export", "source", ".", ":", "sudo", "env"}:
        return False
    # binaire déjà valide → ne pas toucher
    return shutil.which(first) is None
