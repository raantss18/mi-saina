# Changelog

Toutes les évolutions notables de **mi-saina** sont documentées ici.
Format inspiré de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) ;
versionnage [SemVer](https://semver.org/lang/fr/).

> Les en-têtes de version correspondent aux **releases publiées** sur GitHub
> (`v1.0.0` → `v1.0.10`). Le travail d'ingénierie réalisé avant la première
> release publique (03–05 juin) est consolidé dans la section **[1.0.0]**.

## [1.0.14] - 2026-06-08

### Ajouté — carte de configuration (connaissance du setup)
- **Carte de configuration** (`~/.config/mi-saina/config-map.md`) : scan **déterministe** (zéro LLM) et **secret-safe** de `~/.config`, `~/.local/bin` et `~/.local/share/applications` — applications configurées, **applis par défaut** (navigateur, PDF, etc.), **scripts/commandes perso**, thème, éditeur/terminal préférés, infos git non sensibles. Objectif : l'agent **connaît déjà ton setup** → moins d'hallucinations, moins d'erreurs de commandes, et **économie de tokens/temps** sur les tâches de configuration.
  - **Stratégie token-efficace** : un **index compact** est injecté au system prompt ; le **détail** n'est lu par l'agent qu'**à la demande** via `[READ: ~/.config/mi-saina/config-map.md]` (vérifié live : une question « navigateur/éditeur par défaut ? » est répondue **sans exécuter aucune commande**).
  - **Sûreté** : on ne lit que des **noms** (dossiers, scripts, lanceurs) et une **allowlist de clés non sensibles** ; tout fichier/clé ressemblant à un secret (token, clé, mot de passe, cookie, `.pem`, `id_rsa`…) est **ignoré**. Aucune valeur sensible n'est lue ni stockée.
  - **Cadence** : scan au démarrage si périmé (> 24 h) puis ~1×/jour ; bouton **« Rafraîchir »** dans Config → Mémoire. Réglage `CONFIG_MAP`. Endpoints `GET/POST /config/config-map`.

## [1.0.13] - 2026-06-08

### Ajouté — connaissance de la machine & maintenance
- **Profil machine** (`~/.config/mi-saina/machine.md`) : collecté au 1er démarrage et via un bouton **« Rafraîchir »** (Config → Mémoire). Capture les **chemins XDG réels** de l'utilisateur (résout enfin « Téléchargements » ↔ `~/Downloads` — fini les suppositions de noms), la **structure du dossier personnel** (niveau 1), un **aperçu agrégé** des dossiers standards (compte par type, taille — sans exposer les noms de fichiers) et les **outils installés**. Injecté dans le system prompt → l'agent agit avec les vrais chemins au lieu de deviner. Réglable (`MACHINE_PROFILE`). Read-only, borné, jamais bloquant.
- **Bilan santé périodique** (propose-only) : toutes les ~30 min (réglable `HEALTH_INTERVAL_MIN`), des vérifications **read-only et sans LLM** — mises à jour disponibles, services systemd en échec, espace disque, erreurs noyau récentes — remontent des **constats avec une action SUGGÉRÉE**. mi-saina **n'exécute jamais rien tout seul** : un bandeau 🩺 propose, et cliquer **« Exécuter »** pré-remplit le chat (tu valides comme d'habitude). Endpoints `/health-monitor/insights` et `/health-monitor/check`, toggle `HEALTH_MONITOR`.

### Corrigé — robustesse de l'exécution
- **Boucles de répétition** : les petits modèles répétaient parfois 20× la même commande dans une seule réponse. Les commandes identiques sont désormais **dédupliquées** par réponse.
- **Gabarits entre guillemets** : des templates recopiés comme `xdg-open "full path"` / `"chemin complet"` étaient exécutés ; ils sont désormais **détectés et ignorés** (complète le filtre de placeholders de v1.0.12).

## [1.0.12] - 2026-06-08

### Corrigé — sûreté (hallucinations / auto-empoisonnement)
- **Boucle d'auto-empoisonnement de la mémoire** (bug critique) : l'auto-mémoire avait enregistré un « fait » **faux et inventé** — « l'utilisateur utilise le système de fichiers **Windows** » — qui était ensuite injecté dans **toutes** les sessions. Résultat : le modèle se croyait sous Windows (PowerShell, `C:\…`) et **fabriquait** des résultats (arborescence de dossiers « créée » sans qu'aucune commande ne tourne). Corrigé en profondeur :
  - **Extraction d'auto-mémoire durcie** : n'enregistre QUE des préférences/identité **explicitement** énoncées par l'utilisateur ; **interdiction d'inférer** quoi que ce soit, et **jamais** l'OS/distribution/système de fichiers (auto-détectés). Une tâche/requête ponctuelle n'est plus prise pour une préférence.
  - **Garde-fou anti-empoisonnement** (`services.userctx.append_profile`) : toute « mémoire » affirmant l'environnement (Windows/macOS/Ubuntu/filesystem…) est **rejetée à l'écriture** — défense en profondeur, même pour `[REMEMBER: …]`.
  - **Profil purgé** des entrées erronées (le faux « Windows » + des tâches stockées par erreur comme préférences).
- **Commandes-gabarits exécutées par erreur** : les petits modèles **recopiaient la syntaxe d'exemple** (`[EXEC: commande]`, `[EXEC: …]`) qui était alors exécutée — le résolveur d'applis lançait même une appli au hasard (ex. *AntiMicroX* pour « commande »). Ces placeholders (`commande`/`command`/`cmd`/`…`/`<command>`/ponctuation seule) sont désormais **ignorés** avant exécution.
- **Contamination par les exemples du guidage MCP** : le bloc « fetch/téléchargement » contenait des exemples concrets (« résume raantss18.github.io… », « télécharge les sujets de bac 2026 sur apmep ») que le modèle prenait pour de **vraies demandes** de l'utilisateur. Guidage rendu **concis et sans exemple piégeux** ; un fetch n'est déclenché que si l'utilisateur fournit réellement une URL.

### Renforcé
- **System prompt — règle anti-fabrication explicite** : nouvelle section « NEVER FABRICATE » — interdiction de prétendre avoir créé/listé/déplacé/installé quoi que ce soit **sans avoir réellement exécuté** la commande et reçu sa sortie ; l'OS/les chemins viennent **uniquement** du bloc SYSTEM (machine Linux, jamais Windows/macOS).

> Couvert par de nouveaux tests (`tests/test_chat_helpers.py`, `tests/test_userctx.py`) + reproduction live de bout en bout : la requête qui fabriquait une arborescence liste désormais le **vrai** dossier (`ls`/`du` réels) sans rien inventer.

## [1.0.11] - 2026-06-08

> Release de **maintenance / documentation** — aucun changement fonctionnel par
> rapport à v1.0.10 (le binaire est identique).

### Documentation
- **README (EN/FR/MG)** : ajout des fonctionnalités **sessions isolées** et **dossier de travail par session** (puces + section d'usage dédiée).
- **CHANGELOG réaligné sur le schéma `v1.0.x`** : les en-têtes correspondent désormais aux releases publiées sur GitHub (`v1.0.0` → `v1.0.10`), l'ancien historique interne `1.1.0` → `1.6.1` est consolidé sous **[1.0.0]** (première release publique) et le bucket *[Non publié]* ventilé dans les releases concernées. Aucun détail technique perdu.

## [1.0.10] - 2026-06-08

### Corrigé
- **Confusion entre sessions (« contexte qui bave »)** : une nouvelle session pouvait recevoir, par erreur, des extraits d'**autres** sessions (ex. une question « usage disque » renvoyait une réponse sur les **processus** d'une session passée). Cause : `build_context_prefix` injectait à chaque message les extraits sémantiques les « moins éloignés » d'autres conversations, que le petit modèle local prenait pour la tâche en cours. L'injection cross-session est **supprimée de la boucle de chat** : une session = *system prompt + profil/contexte global + historique de **cette** session* uniquement. La recherche sémantique reste disponible, mais seulement dans la **barre de recherche** de la barre latérale (là où c'est explicitement demandé). Validé par un test déterministe (zéro fuite) + un test live de bout en bout.
- **Raisonnement stocké en mémoire** : les blocs `<think>…</think>` sont désormais **retirés avant l'enregistrement** des réponses de l'assistant (`_clean_for_store`). La mémoire et les embeddings restent propres → plus de pollution inter-sessions à terme. Couvert par `tests/test_routers.py`.

### Ajouté
- **Dossier de travail par session** : bouton **📁** dans l'en-tête du chat pour attacher un dossier à une session. Les commandes shell de cette session s'exécutent **dans ce dossier** (`cwd` passé jusqu'à `stream_pty`) et le modèle en est informé (indice de contexte) → réponses plus précises avec chemins relatifs. Nouvelle colonne `working_dir` (migration auto sur base existante), endpoint `PUT /memory/sessions/{id}/working-dir` (dossier inexistant rejeté sans écraser l'ancien, `path:""` pour effacer). Fonctionne même depuis l'écran d'accueil (la session est créée à la volée). Couvert par `tests/test_routers.py`.

### Modifié
- **En-tête du chat** : le **titre auto-généré de la session** s'affiche dans l'espace libre de l'en-tête (à côté du modèle/Config/Tâches), au lieu d'une ligne séparée en dessous.
- **Barre latérale** : le bouton **« + Nouvelle session »** est désormais un bouton plein (couleur d'accent), nettement détaché de la liste d'historique.
- **Écran d'accueil** redessiné : héros centré (logo + accroche), section « Essayez un exemple », cartes avec **icône colorée + titre + description**, entièrement traduites (EN/FR/MG).

## [1.0.9] - 2026-06-07

### Corrigé
- **Ollama Hub réparé** : la **suppression** et le **téléchargement/mise à jour** de modèles fonctionnent à nouveau. Cause : `httpx.AsyncClient.delete()` n'accepte pas de corps JSON → la suppression renvoyait HTTP 500. Passage par `client.request("DELETE", …, json={…})` ; le pull remonte désormais les erreurs explicitement.

### Ajouté
- **Modèles suggérés** : une section propose des modèles populaires d'Ollama **adaptés au matériel** (badge « compatible », budget VRAM estimé via `nvidia-smi`/RAM) avec un bouton « Obtenir », et marque ceux déjà installés. Dans **Config → Modèles** (`/models/suggestions`). Import LM Studio toujours disponible (`/models/import-lmstudio`).

### Modifié
- **Libellés jolis** dans le sélecteur de modèle (« Qwen 3.5 9B » au lieu de `qwen3.5:9b`).
- **Barre latérale** : « Nouvelle session » séparée de la liste + en-tête « HISTORIQUE ».
- **Écran d'accueil** harmonisé (plus de mélange FR/EN), logo centré.
- **Titre de la session** affiché en haut de la discussion.

## [1.0.8] - 2026-06-07

### Modifié
- **Interface réorganisée** :
  - 📚 **Barre latérale = historique uniquement** (sessions + recherche + nouvelle session).
  - ⬇️ **Sélecteur de modèle** en liste déroulante dans le header (à côté de « modèle : ») pour changer de modèle d'un clic.
  - ⚙️ **Config & Tâches** en boutons dans le header. La gestion avancée des modèles (télécharger / mettre à jour / supprimer / importer LM Studio) devient un **onglet « Modèles » dans Config**.
  - 🧹 Retrait des icônes régénérer / copier / supprimer du header — déjà présentes **sous chaque message**.

## [1.0.7] - 2026-06-07

### Corrigé
- **Réponses précises** : correction d'un bug où l'assistant répondait parfois à une **ancienne question** au lieu de la demande actuelle. La mémoire n'est plus injectée que si elle dépasse un **seuil de similarité** (`build_context_prefix(min_score=0.62)`), et le system prompt cadre le modèle pour ne traiter que la dernière demande sans rien inventer. *(Remplacé en v1.0.10 par une isolation totale des sessions.)*
- **Dates de session** : fini le décalage de plusieurs heures (les dates UTC naïves sont désormais marquées UTC via `_utc_iso`, pour une conversion correcte côté navigateur).

### Ajouté
- **Raisonnement repliable** : le « raisonnement » du modèle s'affiche dans un menu déroulant (`<details>`, réduit par défaut) au lieu d'une réponse.
- **Actions par message** : copier / régénérer / supprimer sous chaque message.

### Modifié
- **Une seule barre de recherche** (plein-texte + sémantique combinés) dans la barre latérale.

## [1.0.6] - 2026-06-07

### Ajouté
- **Outils externes via MCP (Model Context Protocol)** — opt-in : mi-saina peut appeler des outils de serveurs MCP (filesystem, fetch, git…) avec la syntaxe `[MCP: serveur.outil {"arg": "valeur"}]`, en plus des `[EXEC: …]`. Client MCP minimal **sans dépendance** (JSON-RPC sur stdio : initialize → tools/list → tools/call). Serveurs déclarés dans `~/.config/mi-saina/mcp.json` (même format que Claude Desktop, voir `config/mcp.json.example`), activé via `MCP_ENABLED` (défaut **off**) dans l'UI Config. Les outils disponibles sont injectés dans le system prompt ; un serveur absent/mal configuré est ignoré (jamais bloquant). Le serveur web **fetch** est auto-configuré à l'installation. Couvert par `tests/test_mcp_client.py`.
- **Recherche web exécutée dans la boucle agentique** : le modèle peut émettre `[SEARCH: requête]` et les résultats (titres + URLs + extraits) lui sont **réinjectés** pour poursuivre (avant, `[SEARCH:]` n'ouvrait qu'un panneau côté frontend). Permet d'enchaîner recherche → `fetch` → action. Avec **consigne de téléchargement** : pour télécharger des fichiers depuis un site, le modèle est guidé à (1) `fetch` la page pour lire les liens, (2) `wget` les fichiers dans un dossier dédié.
- **Modèle d'embeddings dédié (`EMBED_MODEL`)** : la mémoire sémantique utilise désormais un modèle d'embeddings séparé (défaut `nomic-embed-text`) au lieu de `FAST_MODEL`. Beaucoup de modèles génératifs (ex. **gemma3**) ne supportent pas `/api/embeddings` — séparer évite de casser la recherche sémantique. À installer une fois : `ollama pull nomic-embed-text`.
- **`num_ctx` adaptatif selon la VRAM libre** : la fenêtre de contexte est réduite automatiquement quand la VRAM libre baisse (paliers), bornée par `NUM_CTX`. Détection agnostique du GPU (NVIDIA `nvidia-smi`, AMD sysfs `amdgpu`, cache 15 s). Toggle `NUM_CTX_AUTO` (défaut on). Couvert par `tests/test_num_ctx.py`.
- **Résolution de référents entre sous-tâches** : un pronom renvoyant à l'étape précédente (« compile-**le** », « ouvre-**la** ») reçoit un référent — le scratch partagé conserve les **commandes concrètes** réussies, et un indice `[RÉFÉRENCE]` pointant le **dernier artefact** est injecté. Détection stricte. Helpers `has_dangling_reference` / `last_artifact` / `reference_hint` dans `services.planner`, couverts par `tests/test_planner_refs.py`.
- **Fusion des micro-étapes du découpage** : les fragments (mot isolé, pur référent) sont recollés à l'étape précédente pour éviter de multiplier des sous-tâches inutiles. Couvert par `tests/test_planner_refs.py`.
- **Auto-complétion clavier des slash-commands** : navigation ↑/↓, **Tab/Entrée** pour valider, **Échap** pour fermer ; surbrillance synchronisée avec la souris.
- **Liste cliquable à l'ouverture ambiguë** : quand plusieurs fichiers proches existent, mi-saina propose une **liste cliquable** (modal) au lieu de deviner. Round-trip backend interruptible par ⏹. Couvert par `tests/test_shell_open_choices.py`.
- **Bouton « Tout valider »** dans la fenêtre de confirmation : approuve la commande **et toutes les suivantes de la tâche en cours**. Couvert par `tests/test_chat_confirm.py`.

### Corrigé
- **Résumé de pages web fiable** : le fetch accepte une URL telle quelle (sans `https://`, guillemets « courbes »…) et récupère le **bon** site — fini le mélange avec un site demandé précédemment. Parsing tolérant : `parse_calls` accepte URL nue, `https://` auto, guillemets normalisés.
- **Recherche web cassée** : le paquet `duckduckgo_search` (déprécié, renommé `ddgs`) ne renvoyait plus de résultats. Migration vers `ddgs` (repli sur l'ancien nom), erreurs réseau tolérées → liste vide non bloquante.
- **Serveurs MCP via `uvx`/`pipx` ne démarraient pas sous systemd** : le PATH restreint des services utilisateur n'inclut pas `~/.local/bin`. Le client MCP élargit le PATH (`~/.local/bin`, `~/bin`, `~/.cargo/bin`, `/usr/local/bin`) ; `install.sh` ajoute aussi ces chemins au service backend. Exemple **git** ajouté à `config/mcp.json.example`.
- **MCP activé faisait croire au modèle qu'il n'avait plus accès au terminal** : le bloc d'outils injecté était énorme (~4600 caractères). Il est désormais **compact** (1 ligne courte par outil, ~1440 caractères) et **rappelle explicitement** que l'accès terminal `[EXEC: …]` reste entier.
- **Ports 8000/3001 déjà occupés** : `install.sh`/`start.sh` détectent les ports pris et basculent automatiquement sur le prochain port libre (jusqu'à +50). L'URL du backend est centralisée (`lib/config.ts` : `API_BASE`/`WS_BASE`). Ports forçables via `BACKEND_PORT`/`FRONTEND_PORT`.
- **Lancement GUI : vrai succès vs échec, agnostique du bureau** : ouvrir un fichier inexistant est signalé sans rien lancer ; `stderr` inspecté avec des signatures d'échec **multi-toolkit** (Qt/GTK/xdg-open/gio). Couvert par `tests/test_shell_repair.py`.
- **Timeout shell tuant les longues commandes** (maj système, gros téléchargements) : `stream_pty` coupe désormais sur **inactivité** (`SHELL_IDLE_TIMEOUT`, défaut 600 s) et non plus sur le temps total — un `paru -Syu` de plusieurs Go n'est plus interrompu tant qu'il progresse. L'arrêt tue tout le **groupe de processus** (`killpg`/SIGKILL).

### Supprimé
- **Endpoint REST `POST /chat/complete`** (et le modèle `ChatRequest`) : code mort et divergent — le frontend ne passe que par le WebSocket `/chat/ws`. `services.shell_exec.execute_command` reste utilisé par l'endpoint `/shell`.

## [1.0.5] - 2026-06-07

### Ajouté
- **Interface entièrement traduite** (English / Français / Malagasy) — tous les panneaux.
- **Rendu Markdown des réponses** : titres, listes, **gras**, code, **tableaux**, liens (plus de markdown brut).

### Corrigé
- Le badge « modèle » affiche désormais le modèle réellement actif (fini le `magistral:small` codé en dur).

## [1.0.4] - 2026-06-07

### Ajouté
- **Multilingue** : English / Français / Malagasy — interface + réponses de l'assistant. Choisi à l'installation (défaut anglais), modifiable dans **Config → Réglages**.
- **Capture d'écran** : bouton qui capture l'écran pour le faire analyser par un modèle vision.
- **Panneau Artefacts** : épingle automatiquement les blocs de code des réponses (+ copier/télécharger).
- **Mémoire automatique** : le profil s'enrichit tout seul des faits durables (réglable).

### Modifié
- **System prompt** réécrit : compact, généraliste (toutes distros), précis — meilleur avec les petits modèles.

## [1.0.3] - 2026-06-07

### Ajouté
- **Base documentaire (RAG)** : indexe un dossier de documents (PDF, Word, Excel, PowerPoint, texte) et pose des questions sur **tes propres documents**. **Config → Mémoire → Base documentaire**. mi-saina retrouve les passages pertinents et **cite les fichiers source** automatiquement (ou via `[RAG: …]`). 100 % local (embeddings `nomic-embed-text`).

## [1.0.2] - 2026-06-07

### Ajouté
- **Lecture de documents** : mi-saina lit et résume les **PDF, Word (.docx), Excel (.xlsx), PowerPoint (.pptx), CSV** et fichiers texte/code. Joins un document (📎) → contenu extrait automatiquement, ou « résume ce PDF : /chemin… » → directive `[READ: chemin]`.
- **Réglages de raisonnement** (Config → Réglages) : `THINK` (auto/on/off) + chat épuré (masquage du `<think>`).

### Corrigé
- Robustesse : message clair en cas d'erreur de modèle (plus de coupure).

## [1.0.1] - 2026-06-07

### Sécurité
- Backend et frontend **bindés sur 127.0.0.1** uniquement (plus d'exposition réseau).
- **Anti-CSWSH** : le WebSocket valide l'origine (un site malveillant local ne peut plus piloter le shell).
- **Anti-CSRF/DNS-rebinding** : middleware HTTP qui refuse les origines navigateur distantes.
- **Blocklist shell renforcée** (`rm -rf /`, `--no-preserve-root`, `chmod -R 777 /`, écritures disque…).
- **Auto-update durci** (plus d'`os.system`, dossier temporaire privé, lancement sans shell).

## [1.0.0] - 2026-06-06

> Première **release publique** (installeur `.run` + fenêtre desktop). Consolide tout
> le travail d'ingénierie des 3–5 juin (boucle agentique, planification, multi-distro,
> compétences, planificateur, mémoire, diagnostics…).

### Application & distribution
- **Fenêtre desktop native** (Tauri) : appli dans le menu Applications, **icône dans la barre système** au démarrage, raccourci global **Ctrl+Alt+M**, notifications, palette de commandes ⌘K, thème clair/sombre/auto, panneau artefacts. Le backend est démarré/arrêté automatiquement par l'appli.
- **Installeur `.run`** auto-extractible (installe Ollama, télécharge un modèle adapté au matériel, installe dans `/opt/mi-saina`, ajoute au menu + démarrage) + **mise à jour intégrée** (Config → Réglages → Mettre à jour) + **import des modèles depuis LM Studio**.
- **Installation multi-distributions** : `install.sh` détecte la distribution (Arch/EndeavourOS, Debian/Ubuntu, Fedora/RHEL, openSUSE, Void, Alpine) et adapte l'installation des dépendances. Choix du modèle selon RAM/VRAM (big/mid/small). Services systemd `mi-saina-backend` / `mi-saina-frontend`.

### Agent & exécution
- **Cœur** : assistant IA local (Ollama) avec backend FastAPI, frontend Next.js, exécution shell en **PTY temps réel**, mémoire sémantique SQLite, gestion des modèles, skills, pièces jointes, recherche web.
- **Boucle agentique multi-étapes** : la sortie de chaque commande `[EXEC:]` est renvoyée au modèle, qui peut enchaîner (ex. `find` un fichier puis l'ouvrir). Plafond `MAX_AGENT_STEPS` (défaut 6).
- **Planification & sous-agents** : les tâches lourdes sont découpées en sous-tâches, chacune exécutée par un **sous-agent à contexte frais et minimal** (adapté aux petites VRAM). Découpage par règles par défaut ; planificateur LLM optionnel (`PLANNER_USE_LLM`). Affichage du plan et de la progression.
- **Garde-fou de contexte** : budget de tokens avec élagage de l'historique ; **résumé extractif déterministe** des vieux messages (`CONTEXT_DIGEST`, sans appel LLM) qui préserve l'intention initiale de la session.
- **Validation avant exécution** (`CONFIRM_MODE` : `risky` par défaut / `all` / `never`) : modale Exécuter/Refuser pour les commandes destructrices ; les commandes root restent validées par le mot de passe sudo (jamais stocké). **Stop réel** : ⏹ envoie SIGINT puis SIGKILL au groupe de processus.
- **Détection de statut fine** : `diagnostics.assess_outcome()` analyse la sortie pour repérer les **échecs logiques renvoyant pourtant 0** (tests « N failed », `Traceback`, `panic:`, `BUILD FAILED`, erreurs gcc/clang/rust/eslint…), avec garde anti-faux-positifs.
- **Vigilance sur la sortie du terminal** : ~35 motifs d'erreur diagnostiqués (pacman, dépendances, keyring, réseau/DNS, droits, disque, OOM, git, Python/pip & PEP 668, Node/npm, ports, Rust/Cargo, Go, make, Docker, systemd…) avec bannière d'alerte et bouton « Arrêter et corriger ».
- **Adaptation distro à l'exécution** : matériel et gestionnaire de paquets détectés au runtime (`services/sysinfo.py`) et injectés dans le system prompt — commandes update/install/search toujours correctes pour la distribution courante.

### Productivité
- **Compétences apprises** : après une tâche réussie (≥2 commandes OK), proposition d'enregistrer une **compétence réutilisable** (`/slash`). **Auto-correction** : une compétence qui échoue puis se corrige peut être mise à jour.
- **Planificateur de tâches local** : tâches récurrentes (X min / jour / semaine), exécution headless et sûre, panneau **⏰ Tâches** + endpoints `/schedule`.
- **Interrupt-redirect** : un message envoyé pendant une tâche est injecté comme nouvelle instruction (sans tout arrêter).
- **Mémoire & contexte** : recherche **sémantique** + **plein-texte (SQLite FTS5)** de l'historique ; **profil utilisateur** persistant via `[REMEMBER: …]` (`profile.md`) ; **fichiers de contexte** `~/.config/mi-saina/context.md` (global) et `MISAINA.md`/`README.md` de projet, injectés automatiquement. Éditables dans l'onglet **Mémoire**.
- **Lancement & ouverture de fichiers** : applications graphiques détachées avec remontée d'erreur ; **résolution d'applis par nom approximatif** (~350 entrées .desktop + Flatpak) ; **auto-réparation de chemin** ; routage par type de fichier (xdg-mime : PDF → okular, `.tex` → texstudio, code → kate).

### Notes
- **Sous-agents parallèles : non retenu** — sur une seule carte 8 Go, Ollama sérialise les générations (aucun gain) et le parallélisme casse la validation/sudo simultanés. Le découpage séquentiel reste optimal en local.
