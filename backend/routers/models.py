import asyncio
import json
import os
import re
import shutil
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config import settings

router = APIRouter()


def _lmstudio_dir() -> Path:
    return Path(os.environ.get("LMSTUDIO_DIR", str(Path.home() / ".lmstudio" / "models")))


def _derive_name(gguf: Path) -> str:
    """Déduit un nom Ollama `modele:quant` à partir du chemin d'un .gguf LM Studio."""
    base = re.sub(r"-?GGUF$", "", gguf.parent.name, flags=re.I)
    base = re.sub(r"[^A-Za-z0-9._-]+", "-", base).strip("-").lower() or gguf.stem.lower()
    m = re.search(r"(Q\d[\w]*|MXFP4|IQ\d\w*|BF16|F16|F32)", gguf.name, re.I)
    tag = m.group(1).lower() if m else "latest"
    return f"{base}:{tag}"

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


@router.get("/import-lmstudio")
async def import_lmstudio():
    """Importe tous les modèles GGUF de LM Studio vers Ollama — stream SSE."""

    def ev(obj: dict) -> str:
        return f"data: {json.dumps(obj)}\n\n"

    async def event_stream():
        base = _lmstudio_dir()
        if not base.exists():
            yield ev({"status": f"Dossier LM Studio introuvable : {base}"})
            yield ev({"status": "done"})
            return
        if not shutil.which("ollama"):
            yield ev({"status": "Commande 'ollama' introuvable dans le PATH"})
            yield ev({"status": "done"})
            return

        ggufs = sorted(p for p in base.rglob("*.gguf") if "mmproj" not in p.name.lower())
        if not ggufs:
            yield ev({"status": f"Aucun fichier .gguf trouvé dans {base}"})
            yield ev({"status": "done"})
            return

        # Modèles déjà présents (pour éviter les ré-imports)
        existing: set[str] = set()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
                existing = {m["name"] for m in resp.json().get("models", [])}
        except Exception:
            pass

        yield ev({"status": f"{len(ggufs)} modèle(s) GGUF détecté(s) dans LM Studio"})
        for g in ggufs:
            name = _derive_name(g)
            if name in existing or name.replace(":latest", "") in {e.replace(":latest", "") for e in existing}:
                yield ev({"status": f"⏭ {name} déjà importé"})
                continue
            yield ev({"status": f"▶ Import de {name}…"})
            try:
                proc = await asyncio.create_subprocess_exec(
                    "ollama", "create", name, "-f", "-",
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                )
                assert proc.stdin and proc.stdout
                proc.stdin.write(f"FROM {g}\n".encode())
                await proc.stdin.drain()
                proc.stdin.close()
                async for line in proc.stdout:
                    t = line.decode(errors="replace").strip()
                    if t:
                        yield ev({"status": t})
                rc = await proc.wait()
                yield ev({"status": (f"✅ {name} importé" if rc == 0 else f"✗ Échec import {name}")})
            except Exception as e:  # noqa: BLE001
                yield ev({"status": f"✗ {name} : {e}"})
        yield ev({"status": "done"})

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
