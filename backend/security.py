"""Gardes réseau locales — source unique pour HTTP (main.py) et WebSocket (chat.py).

Le backend exécute des commandes shell : il ne doit être joignable que depuis la
machine. Deux vérifications complémentaires, mêmes défenses que Jupyter/Ollama :

- Origine (anti-CSRF / CSWSH) : une page web distante ouverte dans un navigateur
  local envoie son Origin → refusée. L'absence d'Origin (app native, curl) est
  tolérée.
- Host (anti-DNS-rebinding) : une page distante peut faire pointer son domaine
  sur 127.0.0.1 puis requêter « son » origine — le navigateur atteint alors ce
  backend SANS Origin (GET no-cors / navigation / EventSource) mais avec
  Host: attacker.com. La vérification d'origine seule ne suffit donc pas.
"""
from urllib.parse import urlparse

from config import settings

_LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1")


def origin_allowed(origin: str | None) -> bool:
    """N'autorise que les origines locales (web dev) et l'appli desktop (tauri)."""
    if not origin:
        return True  # clients natifs/CLI locaux (pas d'origine de navigateur)
    if origin.startswith("tauri://"):
        return True
    host = (urlparse(origin).hostname or "").lower()
    return host in _LOCAL_HOSTS or host.endswith(".localhost")


def host_allowed(host: str | None) -> bool:
    """Le header Host doit désigner la machine locale (ou un hôte explicitement
    autorisé via EXTRA_ALLOWED_HOSTS pour les setups avancés)."""
    if not host:
        return False
    h = host.strip().lower()
    if h.startswith("["):                       # [::1]:8000 → ::1
        h = h[1:].split("]", 1)[0]
    elif h.count(":") == 1:                     # localhost:8000 → localhost
        h = h.split(":", 1)[0]
    if h in _LOCAL_HOSTS or h.endswith(".localhost"):
        return True
    extra = {x.strip().lower()
             for x in (getattr(settings, "EXTRA_ALLOWED_HOSTS", "") or "").split(",")
             if x.strip()}
    return h in extra
