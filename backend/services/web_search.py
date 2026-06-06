# Le paquet a été renommé duckduckgo_search → ddgs. On préfère ddgs (maintenu)
# et on retombe sur l'ancien nom si besoin.
try:
    from ddgs import DDGS
except ImportError:                       # pragma: no cover
    from duckduckgo_search import DDGS

from config import settings


def search_web(query: str) -> list[dict]:
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=settings.MAX_SEARCH_RESULTS):
                results.append({
                    "title": r.get("title"),
                    "url": r.get("href"),
                    "snippet": r.get("body"),
                })
    except Exception:
        pass                              # réseau/rate-limit → liste vide (non bloquant)
    return results
