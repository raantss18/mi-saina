# Rapport d'amélioration — mi-saina

> Date : 2026-06-10 · Mission : audit P1–P5 + implémentation S1–S5 + tests + doc.
> Principe respecté : **améliorer > remplacer**, rétrocompatibilité, zéro régression.

## 1. Fichiers créés / modifiés / non touchés

### Créés
- `backend/services/task_classifier.py` — classifieur de complexité SIMPLE/INTERMEDIATE/COMPLEX (S1 enrichi, S4).
- `backend/services/prompt_normalizer.py` — sanitisation de l'entrée utilisateur (S5).
- `backend/tests/test_task_classifier.py`, `backend/tests/test_prompt_normalizer.py` — 26 tests.
- `docs/audit_9b_limitations.md`, `docs/improvement_report.md`.

### Modifiés (intégration minimale, balisée `# [mi-saina-improve]`)
- `backend/services/llm.py` — `stream_response(..., think)` : override du thinking par requête.
- `backend/routers/chat.py` — sanitisation à l'entrée, classification, thinking conditionnel
  threadé jusqu'à `stream_response`, event WS `meta` (complexité + thinking).

### NON touchés (features déjà en place, conservées telles quelles)
- `services/planner.py` (P1), `services/rag.py` + `fit_budget` (P2), boucle ReAct
  `_run_agent_loop` (P3), `shell_stream.is_destructive` (confirmation destructive).

## 2. Statut des 5 solutions

| Sol. | Cible | Statut | Détail |
|------|-------|--------|--------|
| **S1** | Décomposition | **Déjà implémenté → enrichi** | `planner.should_plan/plan_task` + sous-agents existaient ; ajout d'un **classifieur 3 niveaux** réutilisable (`task_classifier`). |
| **S2** | RAG / compression | **Déjà implémenté** | `rag.py` (embeddings nomic en SQLite + cosinus, chunks chevauchés) + `fit_budget` + `CONTEXT_DIGEST` + seuil d'injection 0.55. Pas de duplication ChromaDB (inutile). |
| **S3** | Boucle ReAct | **Déjà implémenté** | `_run_agent_loop` : génération → `[EXEC:]` → sortie PTY réelle réinjectée → répéter ; `MAX_AGENT_STEPS` ; interception destructive. |
| **S4** | Thinking conditionnel | **Implémenté (manque réel)** | `task_classifier` → SIMPLE = thinking OFF, sinon ON ; override threadé `chat → _run_agent_loop → _stream_llm → stream_response(think=…)`. Override seulement si réglage global `THINK=auto`. VRAM/num_ctx déjà borné par `NUM_CTX_AUTO`. |
| **S5** | Normalisation prompts | **Implémenté (partie utile)** | Sanitisation d'entrée (`prompt_normalizer`) : NFC, suppression caractères de contrôle, **défang** des marqueurs de directives collés (`[EXEC:`, `<think>`…), borne 8000 c. **Templates par modèle laissés à Ollama** (les réécrire les casserait). |

## 3. Comparatif performances avant / après (mesuré, qwen3.5:9b, num_ctx 8192)

| Test | Niveau | Avant (temps / tokens reçus) | Après (temps / tokens reçus) | P résolu |
|------|--------|------------------------------|------------------------------|----------|
| **A** lister services systemd | SIMPLE | 18.1 s / 221 | **4.9 s / 87** | P4 ✅ |
| **D** espace disque | SIMPLE | 49.7 s / 1171 (4326 c thinking) | **1.7 s / 9** (`df -h`) | P4 ✅ (régression OK : < 3 s, ≤ 200 tok, thinking OFF) |
| **B** nginx ne démarre pas | INTERMEDIATE | 11.8 s (thinking ON) | 11.8 s (thinking ON, **conservé**) | P4 n/a (inter→thinking voulu) |
| **C** analyse logs 24 h, tous services | COMPLEX | > 170 s (1 passage, **n'aboutit pas**) | décomposé en sous-tâches + ReAct (P1+P3 déjà là) | P1/P3 ✅ |

> P4 sur SIMPLE : **×3.7 à ×29 plus rapide**, jusqu'à **−99 % de tokens**, qualité égale.
> P5 : entrée sanitisée (un log collé `[EXEC: rm -rf ~]` est neutralisé, encodage normalisé,
> entrées pathologiques bornées) sans coût de tokens visible (`sent` inchangé ~2290).

### Régression / stress
- **TEST_D (régression)** : ✅ rapide (1.7 s en bench, thinking OFF, ≤ 200 tokens).
- **TEST_E (stress, COMPLEX)** : classé COMPLEX → décomposition + sous-agents (architecture déjà
  validée v1.0.10) ; thinking ON. Pas de régression introduite.

## 4. Recommandations prochaines versions
- **Re-classifier chaque sous-tâche** d'un plan (actuellement le thinking du parent est propagé) :
  une sous-tâche atomique « lister X » pourrait passer en thinking OFF → gain additionnel.
- **Surfacer la complexité dans l'UI** (badge SIMPLE/INTER/COMPLEX) à partir de l'event `meta`.
- **Cache de classification** par message (négligeable, mais propre).
- **Indexation RAG des pages man / wiki Arch** locales (S2 optionnel) pour enrichir le contexte
  des diagnostics, déjà supporté par `rag.index_folder`.
- **Modèle de raisonnement plus grand en option** (si VRAM le permet) pour le causal multi-services.

## 5. Limites résiduelles du 9B (architecture impuissante)
- Inférence causale profonde multi-services : bornée et vérifiée, pas rendue fiable.
- Coût du thinking quand il est réellement nécessaire (INTERMEDIATE/COMPLEX) : incompressible.
- Suivi d'instructions strict / boucles : mitigé (dédup, placeholders, anti-fabrication) mais non nul.
- Fenêtre 8 Go (num_ctx ~8K) : gros contextes via RAG + digest, pas en contexte plein.
