"""
Planification et gestion du contexte (adapté petite VRAM).

- estimate_tokens / fit_budget : garde-fou anti-saturation du contexte.
- should_plan : décide si une tâche est « lourde » et mérite un découpage.
- plan_task : découpe une demande en sous-tâches via un petit modèle (deepseek-r1:8b).
  Chaque sous-tâche sera ensuite exécutée dans un contexte NEUF et minimal.
"""

import json
import re

from config import settings
from services.llm import complete

THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
# Indices qu'une demande contient plusieurs actions enchaînées
_MULTI_ACTION = re.compile(
    r"\b(puis|ensuite|apr[èe]s|et\s+(?:ensuite|aussi)|enfin|chaque|tous?\s+les|toutes\s+les|"
    r"plusieurs|d'?abord)\b", re.IGNORECASE)
_ACTION_VERBS = re.compile(
    r"\b(ouvre|ouvrir|cherche|chercher|trouve|trouver|compile|compiler|build|lance|lancer|"
    r"d[ée]marre|d[ée]marrer|installe|installer|cr[ée]e|cr[ée]er|clone|cloner|mets?\s+à\s+jour|"
    r"affiche|afficher|liste|lister|run|ex[ée]cute|ex[ée]cuter)\b", re.IGNORECASE)


def estimate_tokens(text: str) -> int:
    """Estimation grossière : ~4 caractères par token."""
    return max(1, len(text) // 4)


def fit_budget(messages: list[dict], max_tokens: int | None = None) -> list[dict]:
    """Élague l'historique pour tenir dans le budget de tokens.

    Garde toujours : le message système (1er) et le DERNIER message.
    Remplit le reste depuis la fin (messages récents prioritaires).
    """
    max_tokens = max_tokens or settings.MAX_CONTEXT_TOKENS
    if not messages:
        return messages
    system = messages[0] if messages[0].get("role") == "system" else None
    body = messages[1:] if system else messages[:]
    if not body:
        return messages

    used = estimate_tokens(system["content"]) if system else 0
    last = body[-1]
    used += estimate_tokens(last["content"])
    kept_rev = [last]
    for msg in reversed(body[:-1]):
        t = estimate_tokens(msg.get("content", ""))
        if used + t > max_tokens:
            break
        used += t
        kept_rev.append(msg)
    kept = list(reversed(kept_rev))
    return ([system] + kept) if system else kept


def should_plan(user_input: str) -> bool:
    """Heuristique sans LLM : la tâche est-elle « lourde » (à découper) ?"""
    if not settings.PLANNER_ENABLED:
        return False
    text = user_input.strip()
    if len(text) > 240:
        return True
    if _MULTI_ACTION.search(text):
        return True
    # Plusieurs verbes d'action distincts = plusieurs étapes probables
    verbs = {m.group(0).lower() for m in _ACTION_VERBS.finditer(text)}
    return len(verbs) >= 2


_PLAN_SYSTEM = (
    "Tu es un planificateur de tâches pour un assistant Linux (EndeavourOS/Arch). "
    "Découpe la demande en une courte liste ordonnée de sous-tâches CONCRÈTES, "
    "autonomes et exécutables une par une. Chaque sous-tâche = une phrase d'action "
    "impérative courte (ex. \"Trouver le projet LaTeX COMIA dans ~/Documents/GitHub\"). "
    f"Maximum {settings.MAX_SUBTASKS} sous-tâches.\n"
    "RÉPONDS STRICTEMENT par un tableau JSON de chaînes sur UNE ligne, et RIEN d'autre. "
    "Exemple de format EXACT attendu :\n"
    '["Première action", "Deuxième action", "Troisième action"]'
)


def _parse_subtasks(raw: str) -> list[str]:
    """Strict : on n'accepte qu'un vrai tableau JSON de chaînes courtes.
    En cas de doute → liste vide (pas de découpage, plutôt que des sous-tâches bidon)."""
    raw = THINK_RE.sub("", raw)
    # Si un <think> n'est pas fermé, ne garder que ce qui suit la dernière balise
    if "<think>" in raw and "</think>" not in raw:
        raw = raw.rsplit("<think>", 1)[0]
    # Prendre le DERNIER tableau JSON (la réponse finale, après l'éventuel raisonnement)
    matches = re.findall(r"\[[^\[\]]*\]", raw, re.DOTALL)
    for cand in reversed(matches):
        try:
            arr = json.loads(cand)
        except Exception:
            continue
        if not isinstance(arr, list):
            continue
        tasks = [str(x).strip() for x in arr if isinstance(x, str) and x.strip()]
        # Validation : sous-tâches plausibles (ni vides, ni prose trop longue)
        if tasks and all(3 <= len(t) <= 200 for t in tasks):
            return tasks[: settings.MAX_SUBTASKS]
    return []


# ── Découpage par règles (rapide, déterministe, AUCUN modèle → 0 swap VRAM) ──
_SEQ_STRONG = re.compile(
    r"\s*(?:\bpuis\b|\bensuite\b|\benfin\b|\bet\s+puis\b|\bet\s+ensuite\b|"
    r"\bapr[èe]s\s+[çc]a\b|;|,\s*puis\b)\s*", re.IGNORECASE)
_SEQ_SOFT = re.compile(r"\s*,\s*|\s+et\s+", re.IGNORECASE)


def _clean_parts(parts: list[str]) -> list[str]:
    out = []
    for p in parts:
        p = p.strip(" ,.;:\t")
        # retire un « d'abord »/« ensuite » résiduel en tête
        p = re.sub(r"^(?:d'?abord|ensuite|puis|enfin|et|aussi)\s+", "", p, flags=re.IGNORECASE).strip()
        if p:
            out.append(p)
    return out[: settings.MAX_SUBTASKS]


def rule_split(text: str) -> list[str]:
    """Découpe « fais A puis B puis C » / « A, B et C » en sous-tâches."""
    text = text.strip()
    strong = _clean_parts(_SEQ_STRONG.split(text))
    if len(strong) > 1:
        return strong
    # Sinon : virgules / « et », seulement si plusieurs verbes d'action distincts
    soft = _clean_parts(_SEQ_SOFT.split(text))
    if len(soft) > 1 and sum(1 for p in soft if _ACTION_VERBS.search(p)) >= 2:
        return soft
    return [text]


async def _llm_plan(user_input: str) -> list[str]:
    """Planification par petit modèle (opt-in : peu fiable/lent en local 8 Go)."""
    try:
        raw = await complete(
            [{"role": "system", "content": _PLAN_SYSTEM},
             {"role": "user", "content": user_input}],
            model=settings.PLANNER_MODEL,
            num_predict=900,
            temperature=0.0,
        )
        return _parse_subtasks(raw)
    except Exception:
        return []


async def plan_task(user_input: str) -> list[str]:
    """Renvoie la liste ordonnée des sous-tâches (1 seule = pas de découpage)."""
    if settings.PLANNER_USE_LLM:
        tasks = await _llm_plan(user_input)
        if len(tasks) > 1:
            return tasks
    return rule_split(user_input)
