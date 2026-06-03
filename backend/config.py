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

    class Config:
        env_file = str(_ENV_FILE)


settings = Settings()
