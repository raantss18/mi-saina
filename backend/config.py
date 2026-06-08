import json
import os
from pathlib import Path
from pydantic_settings import BaseSettings

# .env est à la racine du projet (un niveau au-dessus de backend/)
_ENV_FILE = Path(__file__).parent.parent / ".env"
# Réglages modifiables à chaud depuis l'UI (persistés ici, hors git)
_OVERRIDES_FILE = Path(os.path.expanduser("~/.config/mi-saina/settings.json"))


class Settings(BaseSettings):
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    REASONING_MODEL: str = "qwen3.5:9b"
    FAST_MODEL: str = "qwen3.5:9b"
    # Modèle DÉDIÉ aux embeddings de la mémoire sémantique. Beaucoup de modèles
    # génératifs (ex. gemma3) ne supportent pas /api/embeddings → on garde un petit
    # modèle d'embeddings séparé pour ne pas casser la recherche sémantique.
    EMBED_MODEL: str = "nomic-embed-text"
    # Boucle locale uniquement : le backend exécute des commandes shell avec accès
    # complet → ne JAMAIS l'exposer au réseau. (Override possible via .env si besoin.)
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    MAX_SEARCH_RESULTS: int = 5
    SHELL_TIMEOUT: int = 30
    # Timeout d'INACTIVITÉ du PTY (s) : on coupe une commande seulement si elle
    # ne produit AUCUNE sortie pendant ce délai (process bloqué / abandonné).
    # Un téléchargement long (paru -Syu de plusieurs Go) sort en continu → jamais
    # coupé tant qu'il progresse. ⏹ reste disponible pour arrêter manuellement.
    SHELL_IDLE_TIMEOUT: int = 600
    # Quand demander la confirmation Exécuter/Refuser avant une commande :
    #   "risky"  → seulement les commandes destructrices (rm, dd, kill, git reset --hard…)
    #   "all"    → avant chaque commande
    #   "never"  → jamais
    # (les commandes root demandent de toute façon le mot de passe sudo = validation)
    CONFIRM_MODE: str = "risky"
    # Nb max d'allers-retours modèle ↔ commandes par requête (boucle agentique)
    MAX_AGENT_STEPS: int = 6

    # ── Planification / sous-agents (adapté petite VRAM, ex. RTX 4060 8 Go) ──
    PLANNER_ENABLED: bool = True            # découper automatiquement les tâches lourdes
    # Découpage par règles (rapide, 0 swap VRAM) par défaut. Mettre True pour utiliser
    # un petit modèle (PLANNER_MODEL) — plus lent et moins fiable en local 8 Go.
    PLANNER_USE_LLM: bool = False
    PLANNER_MODEL: str = "deepseek-r1:8b"   # modèle dédié au plan (si PLANNER_USE_LLM)
    MAX_SUBTASKS: int = 6                   # nb max de sous-tâches générées
    # Dossier de projet dont on injecte le MISAINA.md/README.md (vide = désactivé)
    PROJECT_DIR: str = ""
    # Fenêtre de contexte passée à Ollama (tokens). 8192 ≈ raisonnable sur 8 Go.
    # Sert de PLAFOND quand NUM_CTX_AUTO est actif.
    NUM_CTX: int = 8192
    # Adapter num_ctx à la VRAM LIBRE détectée (borné par NUM_CTX). False = fixe.
    NUM_CTX_AUTO: bool = True
    # Outils externes via MCP (serveurs configurés dans ~/.config/mi-saina/mcp.json).
    # Désactivé par défaut pour garder l'install simple.
    MCP_ENABLED: bool = False
    # Budget de tokens des messages envoyés au modèle (garde-fou anti-saturation).
    MAX_CONTEXT_TOKENS: int = 5500
    # Résumer (extractif, sans LLM) l'historique élagué au lieu de le couper net,
    # pour garder le fil sur de longues sessions. False = ancien comportement.
    CONTEXT_DIGEST: bool = True
    # Raisonnement (« thinking ») des modèles qui le supportent (qwen3, deepseek…) :
    #   "auto" → comportement par défaut du modèle
    #   "on"   → force le raisonnement (meilleure qualité, plus lent)
    #   "off"  → désactive le raisonnement (plus rapide, réponses directes)
    THINK: str = "auto"
    # Afficher le raisonnement <think>…</think> dans le chat. False = chat épuré
    # (le raisonnement est masqué ; la réponse reste complète).
    SHOW_THINKING: bool = False
    # Langue de l'application et des réponses de l'assistant : en / fr / mg.
    LANGUAGE: str = "en"
    # Mémoire automatique : extrait en arrière-plan les faits/préférences durables
    # de l'utilisateur et enrichit profile.md (sans [REMEMBER:] explicite).
    AUTO_MEMORY: bool = True
    # Profil machine : collecte (1er run + à la demande) les chemins XDG réels, la
    # structure du home et les outils installés → injecté au system prompt.
    MACHINE_PROFILE: bool = True
    # Bilan santé périodique : checks read-only (maj, services en échec, disque,
    # erreurs journal) qui PROPOSENT des actions (n'exécutent jamais rien seuls).
    HEALTH_MONITOR: bool = True
    HEALTH_INTERVAL_MIN: int = 30
    # Carte de configuration : scan déterministe de ~/.config et ~/.local (apps
    # configurées, applis par défaut, scripts perso) → index compact injecté +
    # détail consultable à la demande. Aucune valeur sensible lue. ~1×/jour.
    CONFIG_MAP: bool = True

    class Config:
        env_file = str(_ENV_FILE)


settings = Settings()


# ── Réglages modifiables à chaud (exposés dans l'UI Config) ────────────────────
# Chaque entrée décrit le type, les bornes/choix, un libellé et une aide pour l'UI.
EDITABLE_SETTINGS: dict = {
    "CONFIRM_MODE": {
        "type": "choice", "choices": ["risky", "all", "never"],
        "label": "Confirmation avant exécution",
        "help": "risky = seulement les commandes destructrices · all = chaque commande · never = jamais "
                "(les commandes root demandent de toute façon le mot de passe sudo).",
    },
    "MAX_AGENT_STEPS": {
        "type": "int", "min": 1, "max": 20,
        "label": "Étapes agentiques max",
        "help": "Nombre max d'allers-retours modèle ↔ commandes par requête.",
    },
    "SHELL_IDLE_TIMEOUT": {
        "type": "int", "min": 30, "max": 7200, "step": 30,
        "label": "Timeout d'inactivité shell (s)",
        "help": "On coupe une commande seulement après ce délai SANS aucune sortie. "
                "Mettre haut (ex. 1800) pour les longues maj/téléchargements ; ⏹ arrête à la main.",
    },
    "NUM_CTX": {
        "type": "int", "min": 1024, "max": 32768, "step": 512,
        "label": "Fenêtre de contexte Ollama (num_ctx)",
        "help": "Tokens passés au modèle. 8192 ≈ raisonnable sur 8 Go de VRAM ; plus = plus de RAM/VRAM. "
                "Sert de plafond si l'adaptation auto est activée.",
    },
    "NUM_CTX_AUTO": {
        "type": "bool",
        "label": "Adapter num_ctx à la VRAM libre",
        "help": "Réduit automatiquement la fenêtre de contexte quand la VRAM libre est faible "
                "(borné par num_ctx ci-dessus). VRAM inconnue → valeur fixe.",
    },
    "MCP_ENABLED": {
        "type": "bool",
        "label": "Outils externes MCP",
        "help": "Active les serveurs d'outils MCP configurés dans ~/.config/mi-saina/mcp.json "
                "(filesystem, git, fetch…). Désactivé = aucun outil externe.",
    },
    "MAX_CONTEXT_TOKENS": {
        "type": "int", "min": 1000, "max": 30000, "step": 250,
        "label": "Budget d'historique (tokens)",
        "help": "Garde-fou anti-saturation : au-delà, l'historique est élagué (et résumé).",
    },
    "CONTEXT_DIGEST": {
        "type": "bool",
        "label": "Résumer l'historique élagué",
        "help": "Insère un résumé des messages élagués au lieu de les couper net.",
    },
    "PLANNER_ENABLED": {
        "type": "bool",
        "label": "Découpage des tâches lourdes",
        "help": "Découpe automatiquement les demandes complexes en sous-tâches.",
    },
    "THINK": {
        "type": "choice", "choices": ["auto", "on", "off"],
        "label": "Raisonnement du modèle (thinking)",
        "help": "auto = défaut du modèle · on = force le raisonnement (qualité, plus lent) · "
                "off = réponses directes (plus rapide). Pour qwen3, deepseek-r1, etc.",
    },
    "SHOW_THINKING": {
        "type": "bool",
        "label": "Afficher le raisonnement dans le chat",
        "help": "Désactivé = chat épuré (le bloc <think>…</think> est masqué, la réponse reste complète).",
    },
    "LANGUAGE": {
        "type": "choice", "choices": ["en", "fr", "mg"],
        "label": "Langue / Language / Fiteny",
        "help": "Langue de l'interface et des réponses de l'assistant (English, Français, Malagasy).",
    },
    "AUTO_MEMORY": {
        "type": "bool",
        "label": "Mémoire automatique",
        "help": "Enrichit automatiquement le profil (profile.md) avec les préférences/faits durables "
                "détectés au fil des échanges, sans avoir à le demander.",
    },
    "MACHINE_PROFILE": {
        "type": "bool",
        "label": "Profil machine",
        "help": "Injecte les chemins réels de l'utilisateur (Téléchargements, Documents…), la structure "
                "du dossier personnel et les outils installés → l'agent est plus précis. Bouton « Rafraîchir » dans Mémoire.",
    },
    "HEALTH_MONITOR": {
        "type": "bool",
        "label": "Bilan santé périodique",
        "help": "Vérifie régulièrement le système (mises à jour, services en échec, disque, erreurs récentes) "
                "et PROPOSE des actions — n'exécute jamais rien tout seul.",
    },
    "HEALTH_INTERVAL_MIN": {
        "type": "int", "min": 5, "max": 240, "step": 5,
        "label": "Intervalle du bilan santé (min)",
        "help": "Fréquence des vérifications de santé (en minutes). Plus haut = moins intrusif.",
    },
    "CONFIG_MAP": {
        "type": "bool",
        "label": "Carte de configuration",
        "help": "Scanne ~/.config et ~/.local (apps configurées, applis par défaut, scripts perso) ~1×/jour "
                "et injecte un index compact → l'agent connaît ton setup, évite les erreurs et économise des "
                "tokens. Aucune valeur sensible (token/clé/mot de passe) n'est lue. Bouton « Rafraîchir » dans Mémoire.",
    },
}


def _coerce_setting(key: str, value):
    """Valide et convertit une valeur selon EDITABLE_SETTINGS. Lève ValueError si invalide."""
    spec = EDITABLE_SETTINGS.get(key)
    if spec is None:
        raise ValueError(f"Réglage inconnu ou non modifiable : {key}")
    t = spec["type"]
    if t == "choice":
        if value not in spec["choices"]:
            raise ValueError(f"{key} doit être l'un de {spec['choices']}")
        return value
    if t == "int":
        try:
            v = int(value)
        except (TypeError, ValueError):
            raise ValueError(f"{key} doit être un entier")
        if v < spec["min"] or v > spec["max"]:
            raise ValueError(f"{key} doit être entre {spec['min']} et {spec['max']}")
        return v
    if t == "bool":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "yes", "on", "oui")
        return bool(value)
    raise ValueError(f"Type non géré pour {key}")


def _apply_overrides() -> None:
    """Applique les réglages persistés (UI) par-dessus l'env/.env, au démarrage."""
    if not _OVERRIDES_FILE.exists():
        return
    try:
        data = json.loads(_OVERRIDES_FILE.read_text())
    except Exception:
        return
    for key, value in data.items():
        if key in EDITABLE_SETTINGS:
            try:
                setattr(settings, key, _coerce_setting(key, value))
            except ValueError:
                continue


def current_settings() -> dict:
    """Valeurs courantes des réglages modifiables (pour l'UI)."""
    return {key: getattr(settings, key) for key in EDITABLE_SETTINGS}


def update_settings(updates: dict) -> dict:
    """Valide, applique à chaud et persiste un lot de réglages. Retourne l'état courant.
    Lève ValueError sur la première clé/valeur invalide (rien n'est appliqué)."""
    coerced = {k: _coerce_setting(k, v) for k, v in updates.items()}
    for k, v in coerced.items():
        setattr(settings, k, v)
    persisted = {}
    if _OVERRIDES_FILE.exists():
        try:
            persisted = json.loads(_OVERRIDES_FILE.read_text())
        except Exception:
            persisted = {}
    persisted.update(coerced)
    _OVERRIDES_FILE.parent.mkdir(parents=True, exist_ok=True)
    _OVERRIDES_FILE.write_text(json.dumps(persisted, indent=2, ensure_ascii=False))
    return current_settings()


_apply_overrides()
