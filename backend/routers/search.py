from fastapi import APIRouter
from pydantic import BaseModel

from services.web_search import search_web

router = APIRouter()


class SearchRequest(BaseModel):
    query: str


@router.post("/")
def web_search(body: SearchRequest):
    return search_web(body.query)
