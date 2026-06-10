# [mi-saina-improve] Nouveau module : normalisation & sanitisation de l'entrée
# utilisateur AVANT construction du prompt. Raison : l'entrée était utilisée telle
# quelle (chat.py), sans neutraliser les tentatives d'injection de la SYNTAXE de
# directives de mi-saina ([EXEC:], <think>…) qui pouvaient se retrouver recopiées
# par le modèle, ni borner les entrées pathologiques.
"""
Sanitisation de l'entrée utilisateur.

IMPORTANT — templates de chat par modèle (Qwen im_start/im_end, Mistral [INST]…) :
mi-saina appelle Ollama via `/api/chat` avec des messages {role, content}. **Ollama
applique lui-même le template du modèle actif.** Réécrire ces balises à la main
DOUBLERAIT l'encadrement et casserait la génération. La « normalisation par modèle »
se limite donc, à juste titre, à :
  1) normaliser l'encodage (NFC) et les espaces/retours ligne ;
  2) retirer les caractères de contrôle invisibles ;
  3) DÉFANGER les marqueurs de directives mi-saina collés dans le texte utilisateur
     (un log collé contenant « [EXEC: rm -rf ~] » ne doit jamais devenir une action) ;
  4) borner la longueur pour éviter les entrées pathologiques (le budget fin reste
     géré en aval par planner.fit_budget).
"""
import re
import unicodedata

# Marqueurs de directives à neutraliser s'ils apparaissent dans le TEXTE utilisateur.
_DIRECTIVES = ("EXEC", "MCP", "READ", "RAG", "SEARCH", "REMEMBER", "FETCH", "TOOL", "OUTIL", "CALL")
_DIRECTIVE_RE = re.compile(r"\[(" + "|".join(_DIRECTIVES) + r")\s*:", re.IGNORECASE)
_THINK_RE = re.compile(r"</?\s*think\s*>", re.IGNORECASE)

# Caractères de contrôle (hors \n \t) → supprimés.
_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

_ZWSP = "​"   # espace de largeur nulle : défang lisible, casse le regex de parsing

# Borne haute et SÛRE (rétrocompatible) : on ne tronque que les entrées vraiment
# pathologiques. Le vrai budget de contexte reste géré par fit_budget en aval.
MAX_INPUT_CHARS = 8000


def sanitize(text: str, max_chars: int = MAX_INPUT_CHARS) -> str:
    """Normalise + défang + borne l'entrée utilisateur. Jamais d'exception."""
    if not text:
        return ""
    try:
        t = unicodedata.normalize("NFC", text)
    except Exception:
        t = text
    t = _CTRL_RE.sub("", t)
    # Défang : casse les marqueurs de directives et les balises think SANS rendre
    # le texte illisible (insertion d'un espace de largeur nulle après le marqueur).
    t = _DIRECTIVE_RE.sub(lambda m: f"[{m.group(1)}{_ZWSP}:", t)
    t = _THINK_RE.sub(lambda m: m.group(0).replace("think", f"thin{_ZWSP}k"), t)
    # Normalise les fins de ligne et limite les répétitions extrêmes de blancs.
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"\n{4,}", "\n\n\n", t)
    t = re.sub(r"[ \t]{200,}", " ", t)
    if len(t) > max_chars:
        # Coupe proprement à la dernière limite de ligne avant la borne, si possible.
        cut = t.rfind("\n", 0, max_chars)
        t = t[: cut if cut > max_chars - 400 else max_chars].rstrip() + "\n[…tronqué…]"
    return t.strip()


def was_defanged(original: str, sanitized: str) -> bool:
    """Vrai si la sanitisation a neutralisé quelque chose (utile pour les logs/tests)."""
    return original != sanitized
