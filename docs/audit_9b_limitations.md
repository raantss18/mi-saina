# Audit — limites du 9B & état de l'architecture mi-saina

> Date : 2026-06-10 · Modèle audité : **Qwen3.5 9B (Q4_K_M)** sur **RTX 4060 8 Go** · `num_ctx=8192`
> Méthode : lecture du code (citations fichier:ligne) + mesures réelles avec Ollama lancé.

## Résumé exécutif

mi-saina **possède déjà** une architecture agentique mature. Sur les 5 problèmes ciblés,
**3 sont déjà résolus** (P1 décomposition, P2 RAG/contexte, P3 boucle ReAct) et **2 étaient
des manques réels** (P4 thinking conditionnel, P5 sanitisation d'entrée), désormais corrigés.

La principale limite résiduelle n'est pas architecturale mais **intrinsèque au 9B** :
sur une requête vraiment complexe en un seul passage, le modèle est lent voire ne conclut
pas (TEST_C > 170 s en appel direct) — d'où l'intérêt de la décomposition + sous-agents.

---

## Flux de données (Python ↔ Tauri ↔ Ollama)

```
Tauri (frontend, WebView)  ──WS──▶  FastAPI /chat/ws  (routers/chat.py)
                                       │
   sanitisation (P5) ──▶ classification (P4) ──▶ should_plan (P1)
                                       │
            ┌──────────────────────────┴───────────────────────┐
       simple/inter                                          complex
   _run_agent_loop  ◀── boucle ReAct (P3) ──▶  plan_task → sous-agents (contexte frais)
            │
   _build_messages (system prompt + RAG/contexte P2)  ──▶  fit_budget (budget tokens)
            │
   services/llm.stream_response  ──▶  ollama.AsyncClient.chat(messages, think=…)
            │                              (Ollama applique le TEMPLATE du modèle : im_start/[INST])
   [EXEC: …] détecté ──▶ services/shell_stream.stream_pty (PTY réel) ──▶ sortie réinjectée
```

Le **system prompt** est construit dans `routers/chat.py:_load_system_prompt()` : directive de
langue + `config/system_prompt.txt` + bloc SYSTÈME auto-détecté (`services/sysinfo.system_block`)
+ profil machine + carte de config + contexte/profil utilisateur + RAG actif + outils MCP.

---

## Diagnostic P1–P5 (avant améliorations)

### P1 — Décomposition de tâches complexes → **DÉJÀ RÉSOLU**
- `services/planner.py:133 should_plan()` : heuristique sans LLM (longueur > 240, mots de
  séquence, ≥ 2 verbes d'action).
- `services/planner.py:247 plan_task()` : découpage par règles (déterministe) ou LLM optionnel
  (`PLANNER_USE_LLM`).
- `routers/chat.py:816-857` : si découpage, chaque sous-tâche tourne dans un **sous-agent à
  contexte FRAIS et minimal** (idéal petite VRAM), avec scratch partagé et résolution de référents.
- Verdict : **présent**. ❌ Le prompt unique n'est PAS envoyé tel quel pour les requêtes multi-étapes.

### P2 — Contexte non géré / pas de RAG → **DÉJÀ RÉSOLU**
- `services/rag.py` : indexation locale (embeddings `nomic-embed-text` stockés en **SQLite**,
  table `rag_chunks`), `search()` par similarité cosinus (top-k), `_chunk()` avec **chevauchement
  de 150** (`rag.py:28`).
- `routers/chat.py:784-794` : **auto-RAG** — injection des extraits pertinents seulement si
  score ≥ 0.55 (pas d'injection brute).
- `services/planner.py:91 fit_budget()` + `MAX_CONTEXT_TOKENS` + `CONTEXT_DIGEST` (résumé
  extractif des vieux messages) : le contexte est **budgété et compressé**, jamais injecté brut.
- Recherche plein-texte FTS5 de l'historique en complément.
- Verdict : **présent** (équivalent « SQLite-vec » via embeddings + cosinus). Logs/fichiers
  ne sont **pas** injectés bruts.

### P3 — Absence de boucle ReAct → **DÉJÀ RÉSOLU**
- `routers/chat.py:558 _run_agent_loop()` : THINK (génération) → ACT (`[EXEC: …]`) →
  OBSERVE (sortie **réelle** du PTY via `_exec_streaming` + `_format_exec_feedback:439`,
  réinjectée au modèle `chat.py:525`) → décision (continuer/conclure).
- `routers/chat.py:572` : borne `MAX_AGENT_STEPS` (défaut 6).
- `routers/chat.py:619` + `services/shell_stream.is_destructive` : **interception des
  commandes destructrices** (confirmation selon `CONFIRM_MODE`, root via mot de passe sudo).
- Verdict : **présent**. Le modèle observe le résultat réel à chaque tour.

### P4 — Thinking non conditionnel → **MANQUE RÉEL (corrigé)**
- `services/llm.py:23 _think_kwargs()` lisait `settings.THINK` **global** (auto/on/off) — donc
  thinking ON ou OFF **indépendamment de la complexité** de la requête. En mode `auto`
  (défaut), qwen3 « réfléchit » même pour `df -h`.
- Impact mesuré (voir plus bas) : jusqu'à **+48 s et ×130 tokens** sur une requête triviale.
- Verdict : **confirmé**. ✅ Corrigé (classifieur → thinking par complexité).

### P5 — Prompts non normalisés → **PARTIEL (corrigé)**
- Templates par modèle (im_start/im_end, [INST]) : **gérés par Ollama** via `/api/chat`
  (`services/llm.py:94`). Les réécrire à la main les **dupliquerait** → on ne le fait pas (et on
  ne doit pas). Ce point du cahier des charges est donc volontairement « non applicable tel quel ».
- Sanitisation de l'entrée : **absente** — `user_input` était utilisé brut (`routers/chat.py:754,
  798`), sans neutraliser les marqueurs de directives collés (un log contenant `[EXEC: …]`),
  ni normaliser l'encodage, ni borner les entrées pathologiques.
- Verdict : **manque réel sur la sanitisation**. ✅ Corrigé (`services/prompt_normalizer.py`).

---

## Mesures réelles (Ollama lancé, qwen3.5:9b, num_ctx 8192)

`prompt_eval_count` = tokens envoyés · `eval_count` = tokens générés · temps mur réel.

| Test | Niveau | Mode | Temps | Tokens envoyés | Tokens reçus | « thinking » | Qualité |
|------|--------|------|------:|---------------:|-------------:|-------------:|---------|
| **A** « lister services systemd » | SIMPLE | think ON (avant) | 18.1 s | 2291 | 221 | 654 c | complète |
| **A** | SIMPLE | think OFF (après) | **4.9 s** | 2293 | **87** | 0 | complète |
| **D** « espace disque » | SIMPLE | think ON (avant) | 49.7 s | 2295 | 1171 | **4326 c** | complète |
| **D** | SIMPLE | think OFF (après) | **1.7 s** | 2297 | **9** → `df -h` | 0 | complète |
| **B** « nginx ne démarre pas… » | INTERMEDIATE | think ON | 11.8 s | 2303 | 255 | 618 c | complète |
| **C** « analyse logs 24 h, tous les services… » | COMPLEX | think ON (1 passage) | **> 170 s (timeout)** | 2300+ | — | — | **n'aboutit pas** |

### Lecture
- **P4 (thinking conditionnel) — impact majeur, prouvé** : sur du SIMPLE, désactiver le thinking
  donne **×3.7 à ×29 plus rapide** et **−60 % à −99 % de tokens générés**, à qualité égale
  (TEST_D : `df -h` en 1.7 s au lieu de 49.7 s, dont 4326 caractères de raisonnement inutile).
- **C en un seul passage** : le 9B ne conclut pas en < 170 s → **démontre la nécessité de la
  décomposition (P1) + ReAct (P3)** : mi-saina découpe C en sous-tâches à contexte frais, chacune
  traitable, plutôt qu'un mégaprompt que le 9B n'arrive pas à clore.

---

## Limites résiduelles du 9B (non résolubles par l'architecture seule)
1. **Raisonnement causal profond multi-services** : le 9B reste peu fiable sur l'inférence de
   cause racine ; l'architecture le borne et le vérifie (sortie réelle), mais ne le rend pas 70B.
2. **Latence du thinking** sur tâches longues : utile mais coûteux ; conditionner aide, sans
   supprimer le coût quand le thinking est réellement requis.
3. **Suivi d'instructions strict** : tendance à recopier des gabarits / boucler (mitigé par les
   garde-fous v1.0.12/v1.0.13 : dédup, placeholders, anti-fabrication).
4. **Fenêtre 8 Go** : `num_ctx` borné à ~8K ; les très gros contextes passent par RAG + digest.
