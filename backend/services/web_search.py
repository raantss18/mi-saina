from duckduckgo_search import DDGS

from config import settings


def search_web(query: str) -> list[dict]:
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=settings.MAX_SEARCH_RESULTS):
            results.append({
                "title": r.get("title"),
                "url": r.get("href"),
                "snippet": r.get("body"),
            })
    return results
