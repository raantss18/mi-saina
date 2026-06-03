import asyncio
import os

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config import settings

router = APIRouter()

_ENV_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"
)


def _update_env(model: str):
    if not os.path.exists(_ENV_FILE):
        return
    lines = open(_ENV_FILE).readlines()
    new_lines = []
    for line in lines:
        if line.startswith("REASONING_MODEL="):
            new_lines.append(f"REASONING_MODEL={model}\n")
        elif line.startswith("FAST_MODEL="):
            new_lines.append(f"FAST_MODEL={model}\n")
        else:
            new_lines.append(line)
    with open(_ENV_FILE, "w") as f:
        f.writelines(new_lines)


@router.get("/list")
async def list_models():
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            return [
                {
                    "name": m["name"],
                    "size_gb": round(m["size"] / 1e9, 1),
                    "modified": m.get("modified_at", ""),
                    "active": m["name"] == settings.REASONING_MODEL,
                }
                for m in models
            ]
    return []


class SelectModel(BaseModel):
    model: str


@router.post("/select")
async def select_model(body: SelectModel):
    settings.REASONING_MODEL = body.model
    settings.FAST_MODEL = body.model
    _update_env(body.model)
    return {"status": "ok", "active_model": body.model}


@router.get("/pull/{model_name:path}")
async def pull_model(model_name: str):
    """Télécharge ou met à jour un modèle — stream SSE."""

    async def event_stream():
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                f"{settings.OLLAMA_BASE_URL}/api/pull",
                json={"name": model_name, "stream": True},
            ) as resp:
                async for line in resp.aiter_lines():
                    if line:
                        yield f"data: {line}\n\n"
        yield 'data: {"status":"done"}\n\n'

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.delete("/delete/{model_name:path}")
async def delete_model(model_name: str):
    """Supprime un modèle Ollama."""
    if model_name == settings.REASONING_MODEL:
        raise HTTPException(400, detail="Impossible de supprimer le modèle actif. Changez d'abord de modèle.")
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.delete(
            f"{settings.OLLAMA_BASE_URL}/api/delete",
            json={"name": model_name},
        )
        if resp.status_code not in (200, 204):
            raise HTTPException(resp.status_code, detail=f"Erreur Ollama: {resp.text}")
    return {"status": "deleted", "model": model_name}
