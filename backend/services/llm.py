import ollama
from config import settings


def select_model(task_type: str) -> str:
    fast_tasks = {"classify", "summarize_short", "autocomplete", "quick_answer"}
    return settings.FAST_MODEL if task_type in fast_tasks else settings.REASONING_MODEL


async def stream_response(messages: list, task_type: str = "reason"):
    model = select_model(task_type)
    client = ollama.AsyncClient(host=settings.OLLAMA_BASE_URL)
    async for chunk in await client.chat(
        model=model,
        messages=messages,
        stream=True,
    ):
        yield chunk["message"]["content"]
