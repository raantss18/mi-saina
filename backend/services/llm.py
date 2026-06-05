import ollama
from config import settings
from services.sysinfo import recommended_num_ctx


def select_model(task_type: str) -> str:
    fast_tasks = {"classify", "summarize_short", "autocomplete", "quick_answer"}
    return settings.FAST_MODEL if task_type in fast_tasks else settings.REASONING_MODEL


def num_ctx() -> int:
    """Fenêtre de contexte : adaptée à la VRAM libre si NUM_CTX_AUTO, sinon fixe."""
    if settings.NUM_CTX_AUTO:
        return recommended_num_ctx(settings.NUM_CTX)
    return settings.NUM_CTX


def _options() -> dict:
    """Options Ollama communes : fenêtre de contexte bornée (petite VRAM)."""
    return {"num_ctx": num_ctx()}


async def stream_response(messages: list, task_type: str = "reason"):
    model = select_model(task_type)
    client = ollama.AsyncClient(host=settings.OLLAMA_BASE_URL)
    async for chunk in await client.chat(
        model=model,
        messages=messages,
        stream=True,
        options=_options(),
    ):
        yield chunk["message"]["content"]


async def complete(messages: list, model: str | None = None,
                   num_predict: int = 512, temperature: float = 0.2) -> str:
    """Réponse complète (non streamée) — utilisée par le planificateur."""
    client = ollama.AsyncClient(host=settings.OLLAMA_BASE_URL)
    resp = await client.chat(
        model=model or settings.REASONING_MODEL,
        messages=messages,
        stream=False,
        options={"num_ctx": num_ctx(),
                 "num_predict": num_predict,
                 "temperature": temperature},
    )
    return resp["message"]["content"]
