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


_EXEC_RE = re.compile(r"\[EXEC:\s*(.+?)\]", re.IGNORECASE | re.DOTALL)
_NOISE_RE = re.compile(r"\[(?:REMEMBER|RÉSULTAT|RESULTAT|DIAGNOSTIC|STATUT|INSTRUCTION)[^\]]*\]",
                       re.IGNORECASE)
_DIGEST_HEADER = "[RÉSUMÉ DES ÉCHANGES PLUS ANCIENS — élagués pour tenir dans le contexte]"


def _digest_line(msg: dict, limit: int = 160) -> str | None:
    """Une ligne compacte résumant un message élagué (extractif, sans LLM)."""
    role = msg.get("role")
    raw = msg.get("content") or ""
    # Les commandes exécutées sont l'info la plus utile à conserver
    cmds = [c.strip() for c in _EXEC_RE.findall(raw)]
    text = _EXEC_RE.sub("", raw)
    text = _NOISE_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    label = {"user": "Utilisateur", "assistant": "Assistant",
             "system": "Système"}.get(role, role or "?")
    parts = []
    if text:
        parts.append(text[:limit] + ("…" if len(text) > limit else ""))
    if cmds:
        parts.append("commandes : " + " ; ".join(c[:80] for c in cmds[:3]))
    if not parts:
        return None
    return f"{label} — " + " | ".join(parts)


def _build_digest(dropped: list[dict], max_tokens: int) -> str:
    """Résumé extractif des messages élagués, borné à max_tokens (sinon on retire
    les lignes les plus anciennes)."""
    lines = [ln for ln in (_digest_line(m) for m in dropped) if ln]
    if not lines:
        return ""
    # Si le digest déborde, on sacrifie les lignes les PLUS RÉCENTES : elles sont
    # adjacentes à la fenêtre conservée (déjà couvertes), tandis que les premiers
    # échanges portent l'intention initiale de la session — à préserver.
    while lines and estimate_tokens(_DIGEST_HEADER + "\n" + "\n".join(f"- {l}" for l in lines)) > max_tokens:
        lines.pop()
    if not lines:
        return ""
    return _DIGEST_HEADER + "\n" + "\n".join(f"- {l}" for l in lines)


def _fill_from_end(older: list[dict], base_used: int, budget: int) -> tuple[list[dict], list[dict]]:
    """Garde le plus de messages récents possible dans `budget`.
    Retourne (gardés_dans_l_ordre, élagués_dans_l_ordre)."""
    used = base_used
    kept_rev: list[dict] = []
    cut = 0
    for i in range(len(older) - 1, -1, -1):
        t = estimate_tokens(older[i].get("content", ""))
        if used + t > budget:
            cut = i + 1
            break
        used += t
        kept_rev.append(older[i])
    return list(reversed(kept_rev)), older[:cut]


def fit_budget(messages: list[dict], max_tokens: int | None = None) -> list[dict]:
    """Élague l'historique pour tenir dans le budget de tokens.

    Garde toujours : le message système (1er) et le DERNIER message ; remplit le
    reste depuis la fin (messages récents prioritaires). Quand des messages plus
    anciens doivent être retirés, ils sont **résumés** (extractif, sans LLM) dans
    un message synthétique au lieu d'être purement supprimés — pour garder le fil
    sur de longues sessions (cf. settings.CONTEXT_DIGEST).
    """
    max_tokens = max_tokens or settings.MAX_CONTEXT_TOKENS
    if not messages:
        return messages
    system = messages[0] if messages[0].get("role") == "system" else None
    body = messages[1:] if system else messages[:]
    if not body:
        return messages

    base = estimate_tokens(system["content"]) if system else 0
    last = body[-1]
    base += estimate_tokens(last["content"])
    older = body[:-1]

    # 1re passe : remplir avec tout le budget pour savoir s'il y a élagage.
    kept, dropped = _fill_from_end(older, base, max_tokens)
    if not dropped:
        return ([system] + kept + [last]) if system else (kept + [last])

    # Élagage nécessaire. Sans résumé → comportement historique (coupe nette).
    if not settings.CONTEXT_DIGEST:
        return ([system] + kept + [last]) if system else (kept + [last])

    # 2e passe : réserver une part du budget pour le résumé, puis le construire.
    digest_budget = max(150, max_tokens // 6)
    kept, dropped = _fill_from_end(older, base + digest_budget, max_tokens)
    digest = _build_digest(dropped, digest_budget) if dropped else ""

    head = [system] if system else []
    if digest:
        head.append({"role": "user", "content": digest})
    return head + kept + [last]


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


# ── Résolution de référents entre sous-tâches (« compile-le », « ouvre-la ») ──
# Chaque sous-tâche est exécutée dans un contexte NEUF : un pronom qui renvoie au
# résultat de l'étape précédente (le fichier créé, etc.) est sinon irrésolu.
# On détecte ces référents pendants (haute précision) et on pointe explicitement
# le dernier artefact concret produit par les commandes précédentes.

# Enclitique attaché à un verbe (compile-le, ouvre-la, lance-les, fais-le…) +
# démonstratifs autonomes. Volontairement strict pour éviter les faux positifs
# avec « le/la/les » articles (« ouvre le fichier main.c » ne matche pas).
_DANGLING_RE = re.compile(
    r"\w+-(?:le|la|les|l[ae]|y|en|moi|lui|leur)\b"
    r"|\b(?:[çc]a|cela|celui-ci|celle-ci|ceux-ci|celles-ci|"
    r"ce\s+dernier|cette\s+derni[èe]re|le\s+m[êe]me|la\s+m[êe]me)\b",
    re.IGNORECASE,
)

# Jeton ressemblant à un chemin de fichier : ~/…, ./…, /…, ou nom.ext
_PATH_TOKEN_RE = re.compile(
    r"(?:~|\.{1,2})?/[\w.\-/]+"          # ~/x, ./x, ../x, /x
    r"|\b[\w.\-/]+\.[A-Za-z0-9]{1,8}\b"  # fichier avec extension (main.c, app.py)
)


def has_dangling_reference(text: str) -> bool:
    """La sous-tâche contient-elle un pronom/référent qui dépend d'une étape
    précédente (ex. « compile-le », « ouvre-la », « lance ça ») ?"""
    return bool(_DANGLING_RE.search(text or ""))


def last_artifact(prev_cmds: list[str]) -> str:
    """Dernier artefact concret (chemin de fichier) cité dans les commandes déjà
    exécutées — c'est le candidat le plus probable pour résoudre un pronom."""
    for cmd in reversed(prev_cmds or []):
        paths = _PATH_TOKEN_RE.findall(cmd)
        # On écarte les options (-x) et binaires sans chemin : on veut un vrai fichier
        paths = [p for p in paths if "/" in p or "." in p.lstrip(".")]
        if paths:
            return paths[-1]
    return ""


def reference_hint(sub: str, prev_cmds: list[str]) -> str:
    """Indice à injecter avant une sous-tâche au référent pendant. Vide si rien à
    résoudre (pas de pronom, ou aucun artefact connu)."""
    if not has_dangling_reference(sub):
        return ""
    art = last_artifact(prev_cmds)
    if not art:
        return ""
    return (
        "[RÉFÉRENCE] Un pronom de cette sous-tâche (« le / la / -le … ») renvoie "
        f"très probablement à l'élément produit à l'étape précédente : {art}. "
        "Utilise ce chemin explicitement plutôt que le pronom."
    )
