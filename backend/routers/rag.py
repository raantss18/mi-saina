"""Endpoints RAG : indexer un dossier, interroger, statut, vider."""
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services import rag

router = APIRouter()


@router.get("/status")
def rag_status():
    return rag.status()


class SearchBody(BaseModel):
    query: str
    top_k: int = 5


@router.post("/search")
async def rag_search(body: SearchBody):
    return await rag.search(body.query, body.top_k)


@router.get("/index")
async def rag_index(folder: str):
    """Indexe un dossier — flux SSE de progression (EventSource)."""
    async def stream():
        async for ev in rag.index_folder(folder):
            yield f"data: {json.dumps(ev)}\n\n"
    return StreamingResponse(stream(), media_type="text/event-stream")


@router.delete("/clear")
def rag_clear():
    rag.clear()
    return {"status": "ok"}
