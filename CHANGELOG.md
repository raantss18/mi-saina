# Changelog

## [Non publié]

### Supprimé
- **Endpoint REST `POST /chat/complete`** (et le modèle `ChatRequest`) : code mort et divergent — le frontend ne passe que par le WebSocket `/chat/ws`. Ce chemin ne disposait ni de la boucle agentique, ni de la gestion GUI, ni de la validation/sudo, et constituait un piège (comportement différent du WS). Retiré ; `services.shell_exec.execute_command` reste utilisé par l'endpoint `/shell`.

## [1.6.1] - 2026-06-05

### Corrigé
- **`stop` pendant l'attente du mot de passe sudo** : une fois le prompt sudo affiché, le PTY avait rendu la main et l'attente du mot de passe (`sudo_q.get()`) n'écoutait plus le signal d'arrêt → un clic sur ⏹ (ou une déconnexion) restait sans effet jusqu'au timeout de 120 s. L'attente du mot de passe court désormais contre `stop_event` (`asyncio.wait` / FIRST_COMPLETED) : un stop ou une déconnexion interrompt immédiatement (le terminal passe en `stopped` et la tâche s'arrête). Le bouton « Annuler » du modal sudo envoie maintenant un vrai `stop` au backend. Couvert par `tests/test_chat_sudo.py`.
- **Bouton ⏹ qui disparaissait en plein milieu d'une tâche** : l'état `streaming` du frontend retombait à `false` dès qu'une commande se terminait (`shell_done`), alors que la boucle agentique continuait (réinjection de la sortie au modèle, commandes suivantes). `shell_done` ne modifie plus `streaming` ; seuls les events terminaux `done`/`stopped` le remettent à false.

## [1.6.0] - 2026-06-05

### Ajouté
- **Résumé de l'historique élagué** : sur les longues sessions, `fit_budget` ne **coupe** plus net les vieux messages — il en insère un **résumé extractif déterministe** (sans appel LLM, donc 0 swap VRAM) : 1 ligne par message (texte tronqué + commandes `[EXEC:]` conservées), borné à ~1/6 du budget de contexte. Si le résumé déborde, il **préserve l'origine de la session** (l'intention initiale) plutôt que les échanges récents déjà couverts par la fenêtre conservée. Réglable via `CONTEXT_DIGEST` (activé par défaut). Couvert par `tests/test_planner.py`.
- **Détection de statut fine** : le succès/échec d'une commande ne dépend plus du seul code retour. `diagnostics.assess_outcome()` analyse aussi la **sortie** pour repérer les **échecs logiques renvoyant pourtant 0** (suites de tests « N failed / failing », `Traceback`, `panic:`, `BUILD FAILED`, `error:` gcc/clang/rust, eslint « ✖ N problems (N errors) », rspec…), avec garde anti-faux-positifs (« 0 errors », « no failures », « all tests passed »…). L'échec logique est affiché dans le terminal (« ✗ échec logique (rc=0) » + raison), injecté au modèle pour qu'il corrige, et compté comme échec pour l'apprentissage de compétences. Couvert par `tests/test_diagnostics.py`.

## [1.5.0] - 2026-06-04

### Ajouté
- **Planificateur de tâches local** : crée des tâches récurrentes (toutes les X min / chaque jour / chaque semaine) exécutées en arrière-plan, **headless et sûres** (commandes root/destructrices ignorées faute de validation). Résultats consultables dans une session « ⏰ ». Panneau **⏰ Tâches** + endpoints `/schedule`.
- **Interrupt-redirect** : envoie un message pendant qu'une tâche tourne → il est injecté comme nouvelle instruction (sans tout arrêter). Notice « ↪ Nouvelle instruction prise en compte ».
- **Auto-correction des compétences** : si une compétence (`/slash`) échoue puis est corrigée par l'agent, mi-saina propose de **mettre à jour la compétence** avec la version qui a marché.

### Notes
- **Sous-agents parallèles : non retenu** pour l'instant. Sur une seule carte 8 Go, Ollama sérialise les générations → le parallélisme n'accélère pas (et complique la validation/sudo simultanés). Le découpage séquentiel reste le bon choix local. (Voir TODO.)


Toutes les évolutions notables de **mi-saina** sont documentées ici.
Format inspiré de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) ;
versionnage [SemVer](https://semver.org/lang/fr/).

## [1.4.0] - 2026-06-04

### Ajouté
- **Compétences apprises** (inspiré de hermes-agent, adapté local) : après une tâche réussie (≥2 commandes exécutées avec succès), mi-saina propose de l'enregistrer comme **compétence réutilisable** (`/slash`) construite à partir des commandes. Réutilisable ensuite depuis le menu des skills.
- **Recherche plein-texte de l'historique (SQLite FTS5)** : section « Recherche dans l'historique » du panneau sessions — retrouve une ancienne conversation par mot-clé (extraits surlignés) et l'ouvre d'un clic. Vient compléter la recherche sémantique.
- **Fichiers de contexte** : un `~/.config/mi-saina/context.md` (instructions/contexte persistants) et un `MISAINA.md`/`README.md` de projet (dossier `PROJECT_DIR`) sont injectés automatiquement dans le prompt. Éditables via l'onglet **Mémoire** du panneau Config.
- **Profil utilisateur persistant** : l'assistant mémorise des préférences/faits durables via `[REMEMBER: …]` dans `~/.config/mi-saina/profile.md`, réinjectés à chaque conversation (notice « 🧠 Mémorisé »). Éditable dans l'onglet Mémoire. Endpoints `/config/context` et `/config/profile`.
- Analyse de hermes-agent et feuille de route (TODO) des fonctionnalités à reprendre en restant **local & simple**.

### Modifié
- **Confirmation allégée** (`CONFIRM_MODE`) : par défaut `risky` — la fenêtre Exécuter/Refuser n'apparaît plus que pour les commandes **destructrices/irréversibles** (rm, dd, mkfs, kill, git reset --hard, push --force…). Les commandes root restent validées par le mot de passe sudo (plus de double pop-up). Modes : `risky` / `all` / `never`.

## [1.3.0] - 2026-06-04

### Ajouté
- **Installation multi-distributions** : `install.sh` détecte la distribution (Arch/EndeavourOS, Debian/Ubuntu, Fedora/RHEL, openSUSE, Void, Alpine) et adapte automatiquement l'installation des dépendances. Installation **sur place** (dans le dépôt cloné), sans duplication ni données personnelles.
- **Choix du modèle selon le matériel** : `install.sh` détecte RAM/VRAM, recommande un palier (big/mid/small) et propose Qwen / DeepSeek / Gemma (ou un tag personnalisé), puis configure `.env`.
- **Adaptation distro à l'exécution** : le matériel et le gestionnaire de paquets sont détectés au runtime (`services/sysinfo.py`) et injectés dans le system prompt — les commandes update/install/search sont toujours correctes pour la distribution courante. Le system prompt versionné est désormais **générique** (aucune spec matérielle personnelle).
- **Vigilance étendue** : ~35 motifs d'erreur diagnostiqués (pacman, dépendances, keyring, réseau/DNS, droits, disque, OOM, git, Python/pip & PEP 668, Node/npm, ports, Rust/Cargo, Go, make/compilation, Docker, systemd…).

### Modifié
- System prompt : section paquets rendue distro-agnostique (s'appuie sur le bloc « SYSTÈME détecté »).

## [1.2.0] - 2026-06-04

### Ajouté
- **Planification & sous-agents** : les tâches « lourdes » (plusieurs actions enchaînées) sont automatiquement découpées en sous-tâches, chacune exécutée par un **sous-agent à contexte frais et minimal** — adapté aux petites VRAM (RTX 4060 8 Go). Découpage **par règles** (instantané, zéro swap de modèle) par défaut ; planificateur LLM optionnel (`PLANNER_USE_LLM`).
- **Garde-fou de contexte** : budget de tokens (`MAX_CONTEXT_TOKENS`) avec élagage de l'historique avant chaque appel ; fenêtre de contexte bornée (`NUM_CTX`).
- Affichage du **plan** et de la **progression des étapes** dans l'interface.
- **Panneau Terminal** optionnel (activable/désactivable, à côté du chat) : sortie agrégée en direct de toutes les commandes.
- **Statut de tâche** lu depuis les codes de retour : *en cours* / *succès* / *échec* / *arrêté*, affiché dans l'en-tête et le panneau Terminal.
- **Résolution d'applications par nom approximatif** : catalogue des applis installées (.desktop + Flatpak, ~350 entrées) avec correspondance floue sur le nom, l'identifiant, le binaire, le nom générique et les mots-clés (multilingue). Ex. « mission-center » → appli « Mission Center » (binaire `missioncenter`) ; « gestionnaire de fichiers » → Dolphin ; « machine virtuelle » → virt-manager. Évite l'exécution brute d'un binaire inexistant.

### Ajouté
- **Stop tue réellement le processus** : le bouton ⏹ envoie un Ctrl+C (SIGINT) au groupe de processus du terminal via le PTY — arrête proprement `paru`/`pacman` (y compris leurs enfants root) — puis force (SIGKILL) si nécessaire. Stoppe aussi la chaîne agentique en cours.
- **Vigilance sur la sortie du terminal** : détection en temps réel de problèmes connus (verrou pacman périmé, droits manquants, disque plein, keyring, erreurs réseau/miroir, paquet/commande introuvable) avec **bannière d'alerte** et bouton « Arrêter et corriger » (lance la commande corrective via la validation habituelle). Le diagnostic est aussi transmis au modèle pour qu'il propose lui-même la correction.

### Corrigé
- **Saisie interactive depuis le panneau Terminal** : il était en lecture seule ; on peut maintenant répondre aux prompts (`[Y/n]`, etc.) directement depuis le panneau, en plus du bloc terminal du chat.
- **Bloc terminal en double** lors d'une commande root : le passage par la fenêtre de mot de passe sudo créait un second bloc (le 1er restait « en cours » vide). Une seule et même zone terminal est désormais réutilisée.
- **Historique des conversations** : les anciennes sessions s'affichaient vides alors que les messages étaient bien en base. Sélectionner une session charge désormais son fil via `GET /memory/sessions/{id}/messages`.
- Curseur clignotant affiché dans **toutes** les bulles assistant lors d'une tâche multi-étapes : il ne s'affiche plus que sur le message en cours.
- **Routage automatique par type de fichier** : `xdg-open` route vers okular (PDF/livres), texstudio (`.tex`), kate (code/texte) ; associations xdg-mime posées ; recette « projet LaTeX = ouvrir le `main.tex` ».

### Modifié
- Boucle agentique extraite en fonction réutilisable (chemin principal et sous-agents).
- **Rebranding LocalMind → mi-saina** : titre API, écran d'accueil, prompts par défaut.

## [1.1.0] - 2026-06-04

### Ajouté
- **Boucle agentique multi-étapes** : la sortie de chaque commande `[EXEC:]` est renvoyée au modèle, qui peut enchaîner (ex. `find` un fichier puis l'ouvrir). Plafond `MAX_AGENT_STEPS` (défaut 6).
- **Validation avant exécution** (`CONFIRM_BEFORE_EXEC`) : modale **Exécuter / Refuser** avant chaque commande ; un refus stoppe la chaîne.
- **Lancement détaché des applications graphiques** (`setsid -w`) avec remontée des erreurs (code retour + message).
- **Auto-réparation de chemin** à l'ouverture : un nom inexistant (apostrophe typographique, espaces multiples mal retapés) est résolu vers le vrai fichier le plus proche du dossier.
- **Routage automatique par type de fichier** (xdg-mime) : PDF → okular, `.tex` → texstudio, code/texte → kate.
- Recettes par domaine dans le system prompt : projets & code, build & run (latexmk, python, npm, cargo, go, jupyter), VM (virt-manager) & conteneurs (podman), système & fichiers.
- Skills `/update` (`paru -Syu`), `/vm`, `/projects`.
- Réglages `CONFIRM_BEFORE_EXEC` et `MAX_AGENT_STEPS` (config + `.env`).

### Modifié
- System prompt réécrit dans un style proche de Claude Code, avec règles Arch/EndeavourOS (pacman/paru, jamais apt/dnf), distinction CLI/GUI et ouverture de fichiers robuste.
- Détection root élargie (`paru`, `yay`, `pacman -S/R/U/D`, `systemctl …`) ; mot de passe sudo injecté à la détection du prompt `[sudo] password for` (fonctionne aussi pour les aides AUR).
- `--noconfirm` retiré automatiquement (le `[Y/n]` reste interactif) ; `sudo` retiré devant `paru`/`yay`.
- Source unique : services systemd renommés `mi-saina-backend` / `mi-saina-frontend`, pointant vers le dépôt git ; venv via symlink `~/mi-saina-env`.

### Corrigé
- Race condition : la réponse au mot de passe sudo (`sudo_response`) pouvait être « mangée » par le routage stdin → queue dédiée.
- Bug `cmd.lstrip("sudo")` (supprimait des caractères au lieu du préfixe) dans le chemin non-streaming.
- Ouverture de fichiers aux noms complexes qui échouait silencieusement (faux « lancée »).

## [1.0.0] - 2026-06-03

### Ajouté
- Version initiale : assistant IA local (Ollama) avec backend FastAPI, frontend Next.js, exécution shell en PTY temps réel, mémoire sémantique SQLite, gestion des modèles, skills, pièces jointes, recherche web DuckDuckGo, services systemd.
