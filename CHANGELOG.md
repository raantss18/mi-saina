# Changelog

Toutes les évolutions notables de **mi-saina** sont documentées ici.
Format inspiré de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) ;
versionnage [SemVer](https://semver.org/lang/fr/).

## [1.2.0] - 2026-06-04

### Ajouté
- **Planification & sous-agents** : les tâches « lourdes » (plusieurs actions enchaînées) sont automatiquement découpées en sous-tâches, chacune exécutée par un **sous-agent à contexte frais et minimal** — adapté aux petites VRAM (RTX 4060 8 Go). Découpage **par règles** (instantané, zéro swap de modèle) par défaut ; planificateur LLM optionnel (`PLANNER_USE_LLM`).
- **Garde-fou de contexte** : budget de tokens (`MAX_CONTEXT_TOKENS`) avec élagage de l'historique avant chaque appel ; fenêtre de contexte bornée (`NUM_CTX`).
- Affichage du **plan** et de la **progression des étapes** dans l'interface.
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
