"""Secours cloud 100 % gratuit via OpenRouter.

Utilisé seulement si settings.LLM_BACKEND == "openrouter" ET qu'une clé est
présente. Le service tente les modèles gratuits l'un après l'autre ; si tous
échouent (quota journalier, panne, hors ligne), l'appelant retombe sur Ollama.

Zéro frais garanti par deux verrous :
  1. seuls des identifiants de modèles à 0 $/token sont configurés ;
  2. `provider.max_price = 0` est envoyé à chaque requête → OpenRouter renvoie
     une erreur au lieu de facturer si un fournisseur payant était sélectionné.
"""
import json

import httpx

from config import settings

FREE_PRICE = {"prompt": 0, "completion": 0, "image": 0, "request": 0, "audio": 0}


class OpenRouterUnavailable(RuntimeError):
    """Aucun modèle gratuit n'a pu répondre (quota, réseau, clé absente)."""


def enabled() -> bool:
    return (settings.LLM_BACKEND or "ollama").lower() == "openrouter" and bool(
        settings.OPENROUTER_API_KEY.strip()
    )


def model_chain() -> list[str]:
    return [m.strip() for m in settings.OPENROUTER_MODELS.split(",") if m.strip()]


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY.strip()}",
        "Content-Type": "application/json",
        "X-Title": "mi-saina",
    }


def _body(model: str, messages: list, stream: bool, **opts) -> dict:
    body = {
        "model": model,
        "messages": messages,
        "stream": stream,
        "provider": {"max_price": FREE_PRICE},
        **opts,
    }
    return body


async def stream_response(messages: list, **opts):
    """Flux de tokens. Lève OpenRouterUnavailable si aucun modèle ne répond.

    Le premier token reçu « engage » le modèle : on ne bascule plus après, pour
    ne pas mélanger deux réponses partielles dans le chat.
    """
    url = settings.OPENROUTER_BASE_URL.rstrip("/") + "/chat/completions"
    errors = []
    async with httpx.AsyncClient(timeout=settings.OPENROUTER_TIMEOUT) as client:
        for model in model_chain():
            started = False   # au moins un token émis → modèle engagé
            in_think = False  # balise <think> ouverte, à refermer
            try:
                async with client.stream("POST", url, headers=_headers(),
                                         json=_body(model, messages, True, **opts)) as resp:
                    if resp.status_code >= 400:
                        detail = (await resp.aread()).decode("utf-8", "replace")[:200]
                        errors.append(f"{model}: HTTP {resp.status_code} {detail}")
                        continue
                    async for line in resp.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if data == "[DONE]":
                            break
                        try:
                            delta = json.loads(data)["choices"][0]["delta"]
                        except (ValueError, KeyError, IndexError, TypeError):
                            continue
                        # Certains modèles renvoient le raisonnement à part : on le
                        # remet en <think>…</think> comme le fait services/llm.py.
                        reasoning = delta.get("reasoning") or ""
                        if reasoning:
                            if not in_think:
                                yield "<think>"
                                in_think = True
                            started = True
                            yield reasoning
                        content = delta.get("content") or ""
                        if content:
                            if in_think:
                                yield "</think>"
                                in_think = False
                            started = True
                            yield content
                if in_think:
                    yield "</think>"
                if started:
                    return
                errors.append(f"{model}: réponse vide")
            except httpx.HTTPError as exc:
                if started:
                    # Flux déjà commencé : on ne rejoue pas, on laisse la réponse
                    # tronquée (mais bien formée).
                    if in_think:
                        yield "</think>"
                    return
                errors.append(f"{model}: {type(exc).__name__}")
    raise OpenRouterUnavailable(" | ".join(errors) or "aucun modèle gratuit configuré")


async def complete(messages: list, num_predict: int = 512,
                   temperature: float = 0.2) -> str:
    """Réponse complète (non streamée)."""
    url = settings.OPENROUTER_BASE_URL.rstrip("/") + "/chat/completions"
    errors = []
    async with httpx.AsyncClient(timeout=settings.OPENROUTER_TIMEOUT) as client:
        for model in model_chain():
            try:
                resp = await client.post(url, headers=_headers(), json=_body(
                    model, messages, False,
                    max_tokens=num_predict, temperature=temperature))
                if resp.status_code >= 400:
                    errors.append(f"{model}: HTTP {resp.status_code}")
                    continue
                text = resp.json()["choices"][0]["message"].get("content") or ""
                if text.strip():
                    return text
                errors.append(f"{model}: réponse vide")
            except (httpx.HTTPError, ValueError, KeyError, IndexError) as exc:
                errors.append(f"{model}: {type(exc).__name__}")
    raise OpenRouterUnavailable(" | ".join(errors) or "aucun modèle gratuit configuré")
