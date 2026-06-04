# mi-saina — Assistant IA local

**mi-saina** est un assistant IA local inspiré de Claude Code, fonctionnant entièrement en local avec [Ollama](https://ollama.com). Il dispose d'un accès complet à votre machine Linux : exécution de commandes shell en temps réel, gestion de fichiers, recherche web, et mémoire sémantique des conversations.

## Fonctionnalités

- **LLM local via Ollama** — compatible avec tous les modèles (qwen3.5, magistral, deepseek-r1, gemma, phi4, etc.)
- **Shell interactif en temps réel** — PTY (pseudo-terminal) avec streaming de la sortie, prompts Y/n interactifs
- **Mémoire sémantique** — historique des sessions avec recherche cosinus
- **Gestion de modèles** — téléchargement, mise à jour, suppression depuis l'interface
- **Skills (slash-commands)** — `/sysinfo`, `/git`, `/top`, `/net` et créez les vôtres
- **Pièces jointes** — fichiers texte et images (pour modèles vision)
- **System prompt configurable** — instructions de base pour tous les modèles
- **Nommage automatique des sessions** — titre généré par le LLM
- **Import modèles LM Studio** — réutilise les GGUF déjà téléchargés

## Configuration matérielle recommandée

| Composant | Minimum | Recommandé |
|-----------|---------|------------|
| RAM | 16 GB | 32 GB |
| GPU VRAM | 6 GB | 8 GB+ |
| Stockage | 20 GB libres | 100 GB+ |
| OS | Linux (Arch, Ubuntu, Fedora) | EndeavourOS / Arch |

## Installation rapide

```bash
# 1. Cloner le dépôt
git clone https://github.com/raantss18/mi-saina.git
cd mi-saina

# 2. Lancer l'installation automatique
bash install.sh
```

L'installeur :
1. **Détecte ta distribution** (Arch/EndeavourOS, Debian/Ubuntu, Fedora/RHEL, openSUSE, Void, Alpine) et installe Python 3, Node.js, Git avec le bon gestionnaire de paquets
2. Installe et configure Ollama
3. **Détecte ton matériel (RAM/VRAM)** et te propose le modèle idéal — Qwen, DeepSeek ou Gemma (taille adaptée à ta machine)
4. Crée le venv Python et installe les dépendances
5. Installe les dépendances Node.js
6. Configure les services systemd (démarrage automatique au boot)

> mi-saina s'adapte ensuite **automatiquement à ta distribution** : le matériel et les commandes du gestionnaire de paquets (mise à jour, installation…) sont détectés à l'exécution et fournis au modèle.

## Installation manuelle (étape par étape)

### Prérequis

```bash
# Arch / EndeavourOS
sudo pacman -S --needed python nodejs npm git curl

# Ubuntu / Debian
sudo apt install python3 python3-pip python3-venv nodejs npm git curl
```

### Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen3.5:9b   # Modèle par défaut (~6.6GB)
```

### Backend Python

```bash
python3 -m venv ~/mi-saina-env
source ~/mi-saina-env/bin/activate
pip install fastapi uvicorn httpx "pydantic>=2" pydantic-settings python-dotenv \
    aiofiles websockets rich sqlalchemy aiosqlite numpy ollama duckduckgo-search
```

### Frontend Next.js

```bash
cd ~/mi-saina/frontend
npm install
```

### Configuration

```bash
cp .env.example .env
# Éditez .env pour choisir vos modèles
```

### Services systemd (démarrage auto)

```bash
# Créer les services
mkdir -p ~/.config/systemd/user

# Voir install.sh pour les fichiers de service complets
systemctl --user enable --now mi-saina-backend mi-saina-frontend
loginctl enable-linger $USER
```

### Démarrage manuel

```bash
bash ~/mi-saina/start.sh
```

## Importer les modèles LM Studio

Si vous avez déjà téléchargé des modèles via LM Studio (`~/.lmstudio/models/`), vous pouvez les importer dans Ollama sans re-télécharger :

```bash
bash ~/mi-saina/import_lmstudio.sh
```

Le script détecte automatiquement ce qui est déjà importé et saute les doublons.

## Utilisation

### Interface web

Ouvrez http://localhost:3001 dans votre navigateur.

### Contrôles

| Bouton | Action |
|--------|--------|
| `↵` | Envoyer le message |
| `⏹` (rouge) | Arrêter la génération |
| `↺` | Relancer le dernier prompt |
| `⎘` | Copier la dernière réponse |
| `🗑` | Effacer la conversation |
| `📎` | Joindre un fichier / image |

### Skills (slash-commands)

Tapez `/` dans le champ pour voir les skills disponibles :

| Trigger | Description |
|---------|-------------|
| `/sysinfo` | Infos système (CPU, RAM, GPU, disque) |
| `/git` | Statut git du répertoire courant |
| `/top` | Processus les plus gourmands |
| `/net` | État réseau |
| `/pkg` | Mises à jour disponibles (sans installer) |
| `/update` | Mise à jour complète du système (`paru -Syu`) |
| `/explain` | Explique la dernière commande |

Créez vos propres skills dans **⚙ Config → Skills**.

### Exécution de commandes

L'assistant peut exécuter des commandes directement sur votre machine. Il utilise la syntaxe `[EXEC: commande]` dans ses réponses. Les commandes sont exécutées dans un PTY (pseudo-terminal) avec streaming en temps réel.

**Exemples :**
- *"Crée un dossier projet dans mon home"*
- *"Met à jour mon système"* (lance `paru -Syu`)
- *"Montre-moi l'utilisation disque"*
- *"Clone ce dépôt git et installe ses dépendances"*

### Commandes root (sudo / pacman / paru)

mi-saina cible **EndeavourOS / Arch** : il utilise `pacman` et `paru` (jamais `apt`/`dnf`).

Quand une commande nécessite les droits root (`paru`, `sudo pacman -S`, `systemctl enable`…), l'interface ouvre une fenêtre **mot de passe sudo**. Le mot de passe n'est jamais stocké : il est injecté à la volée uniquement au moment où sudo l'affiche (`[sudo] password for …`), ce qui fonctionne aussi pour `paru` (qui escalade lui-même via sudo).

Les confirmations `[Y/n]` restent **interactives** : elles s'affichent dans le bloc terminal et vous répondez via le champ de saisie. mi-saina n'ajoute jamais `--noconfirm`, et ne lance jamais `paru`/`yay` avec `sudo` (ces outils refusent de tourner en root).

## Structure du projet

```
mi-saina/
├── backend/                 # API FastAPI
│   ├── main.py
│   ├── config.py
│   ├── routers/
│   │   ├── chat.py          # WebSocket + shell streaming
│   │   ├── models.py        # Gestion modèles Ollama
│   │   ├── shell.py         # Exécution shell
│   │   ├── search.py        # Recherche DuckDuckGo
│   │   ├── memory.py        # Sessions et mémoire
│   │   └── config_router.py # System prompt + skills
│   └── services/
│       ├── llm.py           # Interface Ollama
│       ├── shell_stream.py  # PTY streaming
│       ├── shell_exec.py    # Exécution simple
│       ├── web_search.py    # DuckDuckGo
│       └── memory.py        # SQLite + embeddings
├── frontend/                # Next.js
│   ├── app/
│   │   ├── page.tsx         # Interface principale
│   │   └── layout.tsx
│   └── components/
│       ├── ChatWindow.tsx
│       ├── MemoryPanel.tsx
│       ├── ModelPanel.tsx
│       ├── ConfigPanel.tsx
│       └── SearchResults.tsx
├── config/
│   ├── system_prompt.txt    # Instructions globales pour le LLM
│   └── skills/              # Skills prédéfinis
├── .env.example
├── install.sh
├── start.sh
└── import_lmstudio.sh
```

## Configuration avancée

### Changer le modèle

Via l'interface : bouton **⬡ Modèles** dans le header.

Via le fichier `.env` :
```bash
REASONING_MODEL=magistral:small
FAST_MODEL=magistral:small
```

### Modifier le system prompt

Via l'interface : **⚙ Config → System Prompt**.

Ou directement dans `config/system_prompt.txt`.

### Ajouter un modèle personnalisé

```bash
# Depuis Ollama Hub
ollama pull nom-du-modele

# Depuis un fichier GGUF local
echo "FROM /chemin/vers/model.gguf" | ollama create mon-modele -f /dev/stdin
```

## Dépannage

### Le backend ne démarre pas

```bash
systemctl --user status mi-saina-backend
journalctl --user -u mi-saina-backend -n 50
```

### Ollama ne répond pas

```bash
curl http://localhost:11434/api/tags   # Vérifier l'API
pgrep -a ollama                         # Vérifier le processus
systemctl --user restart ollama         # Redémarrer
```

### Les commandes shell ne s'exécutent pas

Vérifiez que le backend tourne et que votre modèle comprend la syntaxe `[EXEC: ...]`. Le system prompt inclut les instructions nécessaires.

### Mise à jour de l'application

```bash
cd mi-saina
git pull
bash install.sh   # Ré-exécuter pour mettre à jour les dépendances
```

## Licence

MIT — Libre d'utilisation, modification et distribution.
