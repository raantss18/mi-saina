from pathlib import Path
from pydantic_settings import BaseSettings

# .env est à la racine du projet (un niveau au-dessus de backend/)
_ENV_FILE = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    REASONING_MODEL: str = "qwen3.5:9b"
    FAST_MODEL: str = "qwen3.5:9b"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    MAX_SEARCH_RESULTS: int = 5
    SHELL_TIMEOUT: int = 30
    # Demander une confirmation (Exécuter/Refuser) avant CHAQUE commande [EXEC:]
    CONFIRM_BEFORE_EXEC: bool = True
    # Nb max d'allers-retours modèle ↔ commandes par requête (boucle agentique)
    MAX_AGENT_STEPS: int = 6

    # ── Planification / sous-agents (adapté petite VRAM, ex. RTX 4060 8 Go) ──
    PLANNER_ENABLED: bool = True            # découper automatiquement les tâches lourdes
    # Découpage par règles (rapide, 0 swap VRAM) par défaut. Mettre True pour utiliser
    # un petit modèle (PLANNER_MODEL) — plus lent et moins fiable en local 8 Go.
    PLANNER_USE_LLM: bool = False
    PLANNER_MODEL: str = "deepseek-r1:8b"   # modèle dédié au plan (si PLANNER_USE_LLM)
    MAX_SUBTASKS: int = 6                   # nb max de sous-tâches générées
    # Fenêtre de contexte passée à Ollama (tokens). 8192 ≈ raisonnable sur 8 Go.
    NUM_CTX: int = 8192
    # Budget de tokens des messages envoyés au modèle (garde-fou anti-saturation).
    MAX_CONTEXT_TOKENS: int = 5500

    class Config:
        env_file = str(_ENV_FILE)


settings = Settings()
