# [mi-saina-improve] Nouveau module : classification de complexité d'une requête
# (SIMPLE / INTERMEDIATE / COMPLEX) par heuristiques LÉGÈRES (zéro LLM, zéro VRAM).
# Raison : le planner existant ne dit que « découper ou non » (binaire) ; ce classifieur
# ajoute un niveau de granularité réutilisable, notamment pour le THINKING CONDITIONNEL
# (P4) — un petit modèle ne doit pas « réfléchir » longuement sur « df -h ».
"""
Classifieur de complexité de requête — déterministe et bon marché.

Niveaux :
- SIMPLE       : question/commande directe, une seule intention (« quelle commande pour … »).
- INTERMEDIATE : dépannage/diagnostic ciblé, ou 2 actions enchaînées.
- COMPLEX      : analyse multi-étapes, « tous les … », plan complet, fenêtre temporelle, etc.

Le résultat pilote :
- le mode thinking (SIMPLE → off, sinon on) — voir services/llm.stream_response ;
- (indicatif) le découpage, déjà géré par services/planner.should_plan.
"""
import re

Level = str  # "SIMPLE" | "INTERMEDIATE" | "COMPLEX"

SIMPLE = "SIMPLE"
INTERMEDIATE = "INTERMEDIATE"
COMPLEX = "COMPLEX"

# Signaux de PORTÉE LARGE / multi-étapes → COMPLEX. (On NE met PAS les verbes bruts
# « analyse/diagnostique » seuls : un diagnostic d'UN service est INTERMEDIATE ; ce
# qui fait la complexité, c'est la portée — « tous les », « pour chacun », un plan, une
# fenêtre temporelle, un rollback, des conflits, etc.)
_COMPLEX_HINTS = re.compile(
    r"\b(tous?\s+les|toutes\s+les|chaque|pour\s+chacun|"
    r"plan\s+(?:complet|de\s+rem[eé]diation|de\s+nettoyage|ordonn[ée])|"
    r"depuis\s+\w+\s+(?:heures?|jours?|minutes?)|derni[èe]res?\s+\d+\s*(?:h|heures?|jours?)|"
    r"en\s+tenant\s+compte|rollback|caus(?:al|e\s+racine)|root\s*cause|"
    r"conflits?\s+de|redondan|orchestr|bout\s+en\s+bout)\b",
    re.IGNORECASE)

# Signaux de DÉPANNAGE/diagnostic ciblé → au moins INTERMEDIATE
_TROUBLE_HINTS = re.compile(
    r"\b(pourquoi|ne\s+(?:d[ée]marre|marche|fonctionne|se\s+lance)\s+(?:pas|plus)|"
    r"[eé]chou|en\s+[eé]chec|failed|erreur|error|bug|cass[ée]|r[ée]par|"
    r"fix|r[ée]sou(?:s|dre)|d[ée]panne[rz]?|corrige[rz]?|plante)\b",
    re.IGNORECASE)

# Question simple / consultation directe → tend vers SIMPLE
_SIMPLE_HINTS = re.compile(
    r"^\s*(quelle?\s+(?:est\s+la\s+)?commande|comment\s+(?:faire\s+)?pour|c'?est\s+quoi|"
    r"donne[\s-]?moi|affiche[\s-]?moi|montre[\s-]?moi|liste[\s-]?moi|quel\b)",
    re.IGNORECASE)

# Verbes d'action (réutilise l'esprit du planner) pour compter les étapes probables.
_ACTION_VERBS = re.compile(
    r"\b(ouvre|ouvrir|cherche|chercher|trouve|trouver|compile|compiler|build|lance|lancer|"
    r"d[ée]marre|d[ée]marrer|installe|installer|cr[ée]e|cr[ée]er|clone|cloner|mets?\s+à\s+jour|"
    r"affiche|afficher|liste|lister|run|ex[ée]cute|ex[ée]cuter|analyse|diagnostique|configure|"
    r"nettoie|supprime|propose|v[ée]rifie)\b", re.IGNORECASE)


# Clause de SYMPTÔME niée (« ne démarre pas », « ne se lance plus ») : ce n'est pas
# une action demandée → on la retire avant de compter les verbes d'action.
_NEG_SYMPTOM = re.compile(r"\bn[e']\s+(?:se\s+)?\w+\s+(?:pas|plus)\b", re.IGNORECASE)


def _verb_count(text: str) -> int:
    text = _NEG_SYMPTOM.sub(" ", text)
    return len({m.group(0).lower() for m in _ACTION_VERBS.finditer(text)})


def classify(text: str) -> Level:
    """Niveau de complexité par heuristiques. Jamais d'exception (renvoie SIMPLE par défaut)."""
    t = (text or "").strip()
    if not t:
        return SIMPLE
    verbs = _verb_count(t)
    long = len(t) > 240
    complex_hint = bool(_COMPLEX_HINTS.search(t))
    trouble = bool(_TROUBLE_HINTS.search(t))

    # COMPLEX : analyse/portée large, OU très long, OU multi-étapes nombreuses.
    if complex_hint or long or verbs >= 3:
        return COMPLEX
    # INTERMEDIATE : dépannage ciblé OU deux actions enchaînées.
    if trouble or verbs >= 2:
        return INTERMEDIATE
    # SIMPLE : question/consultation directe ou intention unique courte.
    if _SIMPLE_HINTS.search(t) or len(t) <= 120:
        return SIMPLE
    # Par défaut, prudence : INTERMEDIATE (on ne désactive le thinking que si SIMPLE).
    return INTERMEDIATE


def wants_thinking(level: Level) -> bool:
    """Thinking conditionnel : on ne « réfléchit » pas sur du SIMPLE (gain temps/tokens)."""
    return level != SIMPLE
