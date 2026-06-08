<p align="center">
  <img src="logo/mi-saina-logo.png" alt="mi-saina" width="360">
</p>

> **Langue / Language / Fiteny :** [English](README.md) · **Français** · [Malagasy](README.mg.md)

<h1 align="center">mi-saina — Assistant IA local</h1>

**mi-saina** est un assistant IA local **créé par Antsa**, qui tourne **100 % sur ta machine** grâce à [Ollama](https://ollama.com). Aucune donnée n'est envoyée dans le cloud. Il a un accès complet à ton ordinateur Linux : exécution de commandes shell en temps réel, gestion de fichiers, recherche web, mémoire des conversations, et outils externes (MCP).

> 🐧 **Fonctionne sur toutes les grandes distributions Linux** — Arch/EndeavourOS, Debian/Ubuntu, Fedora/RHEL, openSUSE, Void, Alpine. mi-saina **détecte ta distribution** et utilise automatiquement le bon gestionnaire de paquets (`pacman`/`paru`, `apt`, `dnf`, `zypper`, `xbps`, `apk`). Pas besoin d'être sur Arch.

---

## ✨ Fonctionnalités

- **LLM 100 % local via Ollama** — compatible avec tous les modèles (Qwen, DeepSeek-R1, Gemma, Phi, Mistral…).
- **Shell interactif en temps réel** — vraies commandes, sortie en direct, prompts `[Y/n]` interactifs, mot de passe sudo géré en sécurité.
- **Agent multi-étapes** — le modèle enchaîne commande → résultat → commande suivante pour accomplir une tâche.
- **Adaptation automatique à ta distro et ton matériel** — les commandes de mise à jour/installation sont toujours correctes pour TON système.
- **Lecture de documents** — résume/analyse des **PDF, Word (.docx), Excel (.xlsx), PowerPoint (.pptx), CSV** et fichiers texte/code (joins-les, ou demande « résume ce PDF : … » → directive `[READ: chemin]`).
- **Base documentaire (RAG)** — indexe un dossier (PDF/Word/Excel/PowerPoint/texte) et pose des questions sur **tes documents** ; les passages pertinents sont retrouvés et cités automatiquement. 100 % local (embeddings `nomic-embed-text`).
- **Mémoire** — recherche sémantique + plein-texte de l'historique, profil utilisateur persistant, fichiers de contexte de projet.
- **Sessions isolées** — chaque conversation est autonome : aucun débordement entre sessions (un nouveau chat n'hérite jamais d'un sujet passé sans rapport). La recherche sémantique reste accessible à la demande depuis la barre latérale.
- **Dossier de travail par session** — attache un dossier à une session (📁 dans l'en-tête) : ses commandes shell s'exécutent **dans ce dossier** et le modèle l'utilise pour des réponses plus précises (chemins relatifs).
- **Profil machine** — collecte au 1er démarrage tes chemins réels (Téléchargements, Documents…), la structure du home et les outils installés, pour que l'assistant agisse sur les bons chemins au lieu de deviner. Bouton « Rafraîchir » dans Config → Mémoire.
- **Bilan santé (propose seulement)** — vérifie régulièrement le système (mises à jour, services en échec, disque, erreurs récentes) et **propose** des actions dans un bandeau. N'exécute jamais rien tout seul — cliquer pré-remplit le chat pour que tu valides.
- **Outils externes (MCP)** — branche des serveurs d'outils (filesystem, fetch web, git…) — *optionnel*.
- **Gestion de modèles** depuis l'interface, **skills** (slash-commands) personnalisables, **pièces jointes** (texte + images).
- **Fenêtre desktop native** (Tauri) — appli dans le menu Applications, **icône dans la barre système** au démarrage, raccourci global, notifications, palette de commandes ⌘K, thème clair/sombre/auto. Indépendante du navigateur et du bureau (KDE/GNOME/XFCE/Wayland).

---

## 🖥️ Prérequis matériels

| Composant | Minimum | Recommandé |
|-----------|---------|------------|
| RAM | 8 GB | 16–32 GB |
| GPU | *(optionnel)* | NVIDIA/AMD 8 GB+ VRAM |
| Stockage | 15 GB libres | 50 GB+ |
| OS | n'importe quelle distribution Linux récente | — |

> 💡 **Pas de GPU ?** Ça marche quand même : mi-saina détecte ta RAM et propose un modèle plus léger. C'est juste plus lent. Plus ton matériel est costaud, plus tu peux utiliser un gros modèle.

---

## 🚀 Installation

Deux méthodes au choix.

### Option A — Installeur `.run` (le plus simple) ⭐

Pour les utilisateurs : un seul fichier, aucune compilation.

```bash
# Télécharge mi-saina-X.Y.Z-x86_64.run depuis la page Releases, puis :
chmod +x mi-saina-*-x86_64.run
./mi-saina-*-x86_64.run        # NE PAS lancer avec sudo
```

L'installeur s'occupe de tout : installe **Ollama**, te propose un **modèle adapté à ton matériel** et le télécharge, installe mi-saina dans **`/opt/mi-saina`**, et ajoute l'appli au **menu Applications** + au **démarrage de session** (icône dans la barre système). La fenêtre desktop **démarre le backend toute seule** — rien d'autre à lancer. Linux x86_64.

> 📥 Page des releases : **https://github.com/raantss18/mi-saina/releases**
> Mise à jour : depuis l'appli, **Config → Réglages → Mettre à jour** (ou relance un `.run` plus récent).
> Désinstaller : `sudo /opt/mi-saina/uninstall.sh`.

### Option B — Depuis les sources (développeurs)

Une seule commande, quelle que soit ta distribution :

```bash
git clone https://github.com/raantss18/mi-saina.git
cd mi-saina
bash install.sh
```

Le script `install.sh` fait tout, dans l'ordre :

1. **Détecte ta distribution** et installe les dépendances système (Python 3, Node.js, Git, curl) avec ton gestionnaire de paquets.
2. **Installe et démarre Ollama**.
3. **Analyse ton matériel** (RAM/VRAM) et te propose un modèle adapté (Qwen / DeepSeek / Gemma, ou ton propre tag), puis le télécharge.
4. **Crée l'environnement Python** (`~/mi-saina-env`) et installe les dépendances du backend.
5. **Installe le frontend** (`npm install`).
6. **Configure les services systemd** pour un démarrage automatique au boot.
7. **Choisit automatiquement des ports libres** si 8000 (backend) ou 3001 (frontend) sont déjà occupés.
8. **Compile la fenêtre desktop** (si Rust + webkit sont disponibles) et l'ajoute au **menu Applications** + au **démarrage de session** (icône dans la barre système).

À la fin : cherche **« mi-saina »** dans ton menu d'applications, ou ouvre l'URL web affichée (par défaut **http://localhost:3001**).

> Tu peux forcer les ports : `BACKEND_PORT=8010 FRONTEND_PORT=3010 bash install.sh`.
> Pour **ne pas** compiler la fenêtre desktop : `MISAINA_NO_DESKTOP=1 bash install.sh`.

---

## 🔧 Installation manuelle (étape par étape)

Si tu préfères tout faire à la main.

### 1. Dépendances système

<details>
<summary><b>Arch / EndeavourOS / Manjaro</b></summary>

```bash
sudo pacman -S --needed python python-pip nodejs npm git curl base-devel
```
</details>

<details>
<summary><b>Debian / Ubuntu / Mint / Pop!_OS</b></summary>

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv nodejs npm git curl build-essential
```
</details>

<details>
<summary><b>Fedora / RHEL / CentOS</b></summary>

```bash
sudo dnf install -y python3 python3-pip nodejs npm git curl @development-tools
```
</details>

<details>
<summary><b>openSUSE</b></summary>

```bash
sudo zypper install -y python3 python3-pip nodejs npm git curl gcc gcc-c++ make
```
</details>

<details>
<summary><b>Void Linux</b></summary>

```bash
sudo xbps-install -Sy python3 python3-pip nodejs git curl base-devel
```
</details>

<details>
<summary><b>Alpine</b></summary>

```bash
sudo apk add python3 py3-pip nodejs npm git curl build-base
```
</details>

### 2. Ollama (le moteur des modèles)

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen3.5:9b       # modèle d'exemple (~6.5 GB) ; choisis selon ta machine
ollama pull nomic-embed-text # petit modèle d'embeddings pour la mémoire (~270 Mo)
```

> Petite config ? Essaie `qwen2.5:3b` ou `gemma3:4b`. Grosse config ? `qwen3:14b`, `gemma3:12b`…
>
> 💡 Le modèle d'embeddings (`nomic-embed-text`) est **séparé** du modèle de génération, car certains modèles (ex. gemma3) ne savent pas produire d'embeddings. Tu peux donc choisir n'importe quel modèle pour discuter sans casser la mémoire sémantique.

### 3. Backend (Python)

```bash
cd mi-saina
python3 -m venv ~/mi-saina-env
source ~/mi-saina-env/bin/activate
pip install -r backend/requirements.txt
```

### 4. Frontend (Next.js)

```bash
cd frontend
npm install
cd ..
```

### 5. Configuration

```bash
cp .env.example .env
# Édite .env pour choisir ton modèle (REASONING_MODEL / FAST_MODEL)
```

### 6. Démarrage

```bash
bash start.sh
```

`start.sh` lance Ollama (si besoin), le backend et le frontend, et **bascule automatiquement sur un port libre** si 8000/3001 sont pris. Ouvre ensuite l'URL affichée.

> Pour un démarrage automatique au boot, utilise plutôt `bash install.sh` qui crée les services systemd.

---

## 🎮 Utilisation

### Fenêtre desktop (recommandé)

Après `install.sh`, mi-saina est une vraie appli :

- **Menu Applications** → lance **« mi-saina »** (fenêtre native, pas le navigateur).
- **Barre système (tray)** : au démarrage de session, l'icône apparaît automatiquement. **Clic dessus → ouvre la fenêtre** ; clic droit → *Afficher* / *Quitter*.
- **Fermer la fenêtre** la réduit dans la barre système (mi-saina reste prêt en fond). Pour quitter complètement : tray → *Quitter*.
- **Ctrl+Alt+M** : affiche/masque la fenêtre depuis n'importe où.
- **Ctrl/⌘+K** : palette de commandes · **Ctrl/⌘+B** : replier la barre latérale.
- *Config → Réglages* : bouton **« Lancer au démarrage »** et bascule de thème (clair/sombre/auto).

> La fenêtre desktop parle directement au backend local ; **inutile de garder un navigateur ouvert**.
> Lancer/builder à la main : `cd frontend && npm run desktop:dev` (dev) ou `npm run desktop:build` (bundle).

### Interface web

Au besoin, ouvre **http://localhost:3001** (ou le port affiché au démarrage).

### Boutons principaux

| Bouton | Action |
|--------|--------|
| `↵` | Envoyer le message (**Maj+Entrée** = nouvelle ligne) |
| `⏹` | Arrêter la génération / la commande en cours |
| `↺` | Relancer le dernier prompt |
| `⎘` | Copier la dernière réponse |
| `🗑` | Effacer la conversation |
| `📎` | Joindre un fichier ou une image |
| `▣ Terminal` | Afficher le panneau terminal (sortie détaillée des commandes) |

### Parler naturellement

Demande simplement ce que tu veux, en langage courant :

- *« Crée un dossier `projet` dans mon home »*
- *« Mets à jour mon système »* → lance la bonne commande pour TA distro
- *« Montre-moi l'utilisation du disque »*
- *« Clone ce dépôt git et installe ses dépendances »*
- *« Crée un script Python qui affiche la date, puis exécute-le »*

mi-saina exécute les commandes lui-même (en demandant ton accord pour les actions sensibles). La sortie complète apparaît dans le panneau **▣ Terminal** ; le chat reste lisible.

### Skills (raccourcis `/`)

Tape `/` dans le champ pour voir les raccourcis (navigation au clavier ↑/↓, **Tab/Entrée** pour valider) :

| Raccourci | Description |
|-----------|-------------|
| `/sysinfo` | Infos système (CPU, RAM, GPU, disque) |
| `/git` | Statut git du dossier courant |
| `/top` | Processus les plus gourmands |
| `/net` | État réseau |
| `/pkg` | Mises à jour disponibles (sans installer) |
| `/update` | Met à jour le système (commande adaptée à ta distro) |
| `/explain` | Explique la dernière commande |

Crée tes propres skills dans **⚙ Config → Skills**.

### Dossier de travail

Clique sur **📁** dans l'en-tête du chat pour attacher un dossier à la session courante. Les commandes s'exécutent alors dedans : tu peux dire *« liste les fichiers ici »* ou *« compile ce projet »* sans répéter le chemin complet.

### Commandes nécessitant les droits root

Quand une action demande `sudo` (installer un paquet, activer un service…), une fenêtre **mot de passe sudo** s'ouvre. Le mot de passe **n'est jamais stocké** : il est transmis à la volée uniquement au moment où le système le demande.

- mi-saina utilise **le gestionnaire de paquets de ta distribution** (détecté automatiquement) — jamais celui d'une autre.
- Les confirmations `[Y/n]` restent **interactives** (tu réponds dans l'interface).
- Le bouton **« Tout valider »** permet d'approuver d'un coup toutes les commandes d'une tâche.

---

## 🧩 Outils externes (MCP) — optionnel

mi-saina peut utiliser des **serveurs d'outils MCP** (filesystem, fetch web, git, sqlite…) en plus du shell.

1. Copie l'exemple et adapte-le :
   ```bash
   cp config/mcp.json.example ~/.config/mi-saina/mcp.json
   # édite le fichier : chemins, serveurs voulus
   ```
2. Active **« Outils externes MCP »** dans **⚙ Config → Réglages**.

Les outils déclarés deviennent appelables par l'assistant. Désactivé par défaut pour garder l'installation simple. Liste de serveurs officiels : <https://github.com/modelcontextprotocol/servers>.

---

## ⚙️ Configuration avancée

### Réglages dans l'interface

**⚙ Config → Réglages** expose, applicables à chaud (sans redémarrage) :

- **Confirmation avant exécution** (`risky` / `all` / `never`)
- **Étapes agentiques max**
- **Timeout d'inactivité shell** (monte-le pour les grosses mises à jour / téléchargements)
- **Fenêtre de contexte** (`num_ctx`) + **adaptation automatique à la VRAM libre**
- **Découpage des tâches lourdes**, **résumé d'historique**, **outils MCP**

### Changer de modèle

- Via l'interface : bouton **⬡ Modèles**.
- Via `.env` :
  ```bash
  REASONING_MODEL=qwen3.5:9b
  FAST_MODEL=qwen3.5:9b
  ```

### Ports personnalisés

Les scripts choisissent un port libre automatiquement. Pour forcer :

```bash
BACKEND_PORT=8010 FRONTEND_PORT=3010 bash start.sh
```

Le frontend lit l'URL du backend via `NEXT_PUBLIC_API_BASE` (par défaut `http://localhost:8000`).

### System prompt

**⚙ Config → System Prompt**, ou directement `config/system_prompt.txt`.

### Importer des modèles LM Studio

Déjà des modèles GGUF via LM Studio ? Réutilise-les sans re-télécharger :

```bash
bash import_lmstudio.sh
```

---

## 🛠️ Dépannage

**Le backend ne démarre pas**
```bash
systemctl --user status mi-saina-backend
journalctl --user -u mi-saina-backend -n 50
```

**« model not found » / l'assistant ne répond pas** — le modèle de `.env` n'est pas téléchargé :
```bash
ollama list                 # voir les modèles installés
ollama pull qwen3.5:9b      # en télécharger un, puis le sélectionner dans ⬡ Modèles
```

**Ollama ne répond pas**
```bash
curl http://localhost:11434/api/tags   # vérifier l'API
systemctl --user restart ollama        # ou : ollama serve
```

**Le port 8000 ou 3001 est déjà pris** — les scripts basculent tout seuls sur un port libre (regarde l'URL affichée au démarrage). Tu peux aussi forcer `BACKEND_PORT`/`FRONTEND_PORT`.

**Mettre à jour mi-saina**
```bash
cd mi-saina
git pull
bash install.sh   # ré-installe les dépendances et redémarre les services
```

---

## 📁 Structure du projet

```
mi-saina/
├── backend/                 # API FastAPI (Python)
│   ├── main.py
│   ├── config.py            # réglages + valeurs modifiables à chaud
│   ├── routers/             # chat (WebSocket), models, shell, search, memory, config
│   └── services/
│       ├── llm.py           # interface Ollama (+ num_ctx adaptatif)
│       ├── shell_stream.py  # exécution PTY temps réel (sudo, GUI, réparation de chemin)
│       ├── planner.py       # découpage des tâches + gestion du contexte
│       ├── diagnostics.py   # détection d'erreurs dans la sortie
│       ├── sysinfo.py       # détection distro/matériel/VRAM
│       ├── mcp_client.py    # client MCP (outils externes)
│       └── memory.py        # SQLite + embeddings + recherche
├── frontend/                # interface Next.js
│   ├── app/page.tsx         # interface principale
│   ├── components/          # Chat, Terminal, Modèles, Config, Mémoire, Planning…
│   └── lib/config.ts        # URL backend centralisée (API_BASE / WS_BASE)
├── config/
│   ├── system_prompt.txt    # instructions globales du modèle
│   ├── skills/              # skills prédéfinis
│   └── mcp.json.example     # exemple de config MCP
├── install.sh               # installation automatique multi-distro
├── start.sh                 # démarrage manuel (sans systemd)
└── import_lmstudio.sh       # import de modèles LM Studio
```

---

## 📄 Licence

MIT — libre d'utilisation, de modification et de distribution.
