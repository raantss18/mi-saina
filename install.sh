#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
#  mi-saina — Script d'installation automatique
#  Testé sur : EndeavourOS / Arch Linux
#  Usage     : bash install.sh
# ─────────────────────────────────────────────────────────────────
set -e

INSTALL_DIR="$HOME/mi-saina"
VENV_DIR="$HOME/mi-saina-env"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Couleurs ──────────────────────────────────────────────────────
R='\033[0;31m'; G='\033[0;32m'; Y='\033[1;33m'; B='\033[0;34m'; NC='\033[0m'
ok()   { echo -e "${G}[✓]${NC} $1"; }
warn() { echo -e "${Y}[⚠]${NC} $1"; }
info() { echo -e "${B}[→]${NC} $1"; }
err()  { echo -e "${R}[✗]${NC} $1"; exit 1; }

echo ""
echo -e "${B}╔══════════════════════════════════════════╗${NC}"
echo -e "${B}║          mi-saina — Installation         ║${NC}"
echo -e "${B}║    Assistant IA local avec Ollama         ║${NC}"
echo -e "${B}╚══════════════════════════════════════════╝${NC}"
echo ""

# ── 1. Détection OS ───────────────────────────────────────────────
if command -v pacman &>/dev/null; then
    PKG_MGR="pacman"
    INSTALL_CMD="sudo pacman -S --needed --noconfirm"
elif command -v apt &>/dev/null; then
    PKG_MGR="apt"
    INSTALL_CMD="sudo apt install -y"
elif command -v dnf &>/dev/null; then
    PKG_MGR="dnf"
    INSTALL_CMD="sudo dnf install -y"
else
    warn "Gestionnaire de paquets non reconnu — installez manuellement python3, nodejs, npm, git"
    PKG_MGR="unknown"
fi
info "OS détecté : $PKG_MGR"

# ── 2. Dépendances système ────────────────────────────────────────
info "Vérification des dépendances système..."

if ! command -v python3 &>/dev/null; then
    warn "Python3 absent — installation..."
    case $PKG_MGR in
        pacman) $INSTALL_CMD python python-pip ;;
        apt)    $INSTALL_CMD python3 python3-pip python3-venv ;;
        dnf)    $INSTALL_CMD python3 python3-pip ;;
    esac
fi
ok "Python $(python3 --version 2>&1 | awk '{print $2}')"

if ! command -v node &>/dev/null; then
    warn "Node.js absent — installation..."
    case $PKG_MGR in
        pacman) $INSTALL_CMD nodejs npm ;;
        apt)
            curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
            $INSTALL_CMD nodejs ;;
        dnf)    $INSTALL_CMD nodejs npm ;;
    esac
fi
ok "Node.js $(node --version 2>&1)"

if ! command -v git &>/dev/null; then
    $INSTALL_CMD git
fi
ok "Git $(git --version | awk '{print $3}')"

# ── 3. Ollama ─────────────────────────────────────────────────────
if ! command -v ollama &>/dev/null; then
    info "Installation d'Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
    ok "Ollama installé"
else
    ok "Ollama $(ollama --version 2>&1 | head -1)"
fi

# Démarrer Ollama si pas actif
if ! pgrep -x ollama &>/dev/null; then
    info "Démarrage d'Ollama..."
    ollama serve &>/tmp/ollama_install.log &
    sleep 3
fi

# Service systemd Ollama
if ! systemctl --user is-enabled ollama &>/dev/null 2>&1; then
    info "Configuration du service Ollama..."
    cat > "$HOME/.config/systemd/user/ollama.service" << 'SVCEOF'
[Unit]
Description=Ollama Service
After=network.target

[Service]
ExecStart=/usr/local/bin/ollama serve
Restart=always
RestartSec=3
Environment=HOME=/home/$USER

[Install]
WantedBy=default.target
SVCEOF
    systemctl --user daemon-reload
    systemctl --user enable ollama 2>/dev/null || true
fi

# ── 4. Modèles Ollama ─────────────────────────────────────────────
echo ""
info "Vérification des modèles Ollama..."
INSTALLED_MODELS=$(ollama list 2>/dev/null | awk 'NR>1 {print $1}' | tr '\n' ' ')

pull_if_missing() {
    local model="$1"
    if echo "$INSTALLED_MODELS" | grep -qw "$model"; then
        ok "Modèle déjà présent : $model"
    else
        info "Téléchargement de $model..."
        ollama pull "$model"
        ok "$model téléchargé"
    fi
}

# Modèle par défaut léger (~6.6GB)
pull_if_missing "qwen3.5:9b"

echo ""
warn "Modèles supplémentaires disponibles (optionnels, à installer manuellement):"
echo "   ollama pull deepseek-r1:8b      # 4.4GB — Raisonnement"
echo "   ollama pull gemma3:12b           # 7.3GB — Google"
echo "   ollama pull phi4-reasoning:latest # 9.1GB — Microsoft"
echo "   ollama pull magistral:small       # 14GB  — Mistral"

# ── 5. Copie des fichiers ─────────────────────────────────────────
echo ""
info "Installation dans $INSTALL_DIR..."

if [ "$REPO_DIR" != "$INSTALL_DIR" ]; then
    rsync -a --exclude='data/' --exclude='__pycache__' --exclude='*.pyc' \
          --exclude='node_modules' --exclude='.next' \
          "$REPO_DIR/" "$INSTALL_DIR/"
    ok "Fichiers copiés dans $INSTALL_DIR"
else
    ok "Déjà dans $INSTALL_DIR"
fi

# Config .env
if [ ! -f "$INSTALL_DIR/.env" ]; then
    cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"
    ok ".env créé depuis .env.example"
fi

# ── 6. Environnement Python ───────────────────────────────────────
echo ""
info "Création de l'environnement Python..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip -q

info "Installation des dépendances Python..."
pip install \
    fastapi uvicorn httpx "pydantic>=2" pydantic-settings python-dotenv \
    aiofiles websockets rich sqlalchemy aiosqlite numpy \
    ollama duckduckgo-search \
    --quiet
ok "Dépendances Python installées"

# ── 7. Dépendances Node.js ────────────────────────────────────────
echo ""
info "Installation des dépendances frontend..."
cd "$INSTALL_DIR/frontend"
npm install --silent
ok "node_modules installé"

# ── 8. Services systemd ───────────────────────────────────────────
echo ""
info "Configuration des services systemd..."
mkdir -p "$HOME/.config/systemd/user"

cat > "$HOME/.config/systemd/user/mi-saina-backend.service" << SVCEOF
[Unit]
Description=mi-saina Backend (FastAPI)
After=network.target

[Service]
Type=simple
WorkingDirectory=$INSTALL_DIR/backend
ExecStart=$VENV_DIR/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5
Environment=HOME=$HOME
Environment=PATH=$VENV_DIR/bin:/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=default.target
SVCEOF

cat > "$HOME/.config/systemd/user/mi-saina-frontend.service" << SVCEOF
[Unit]
Description=mi-saina Frontend (Next.js)
After=mi-saina-backend.service

[Service]
Type=simple
WorkingDirectory=$INSTALL_DIR/frontend
ExecStart=/usr/bin/npm run dev -- --port 3001
Restart=on-failure
RestartSec=5
Environment=HOME=$HOME

[Install]
WantedBy=default.target
SVCEOF

systemctl --user daemon-reload
systemctl --user enable mi-saina-backend mi-saina-frontend

# Activer le linger (démarrage sans session)
if command -v loginctl &>/dev/null; then
    loginctl enable-linger "$USER" 2>/dev/null || true
fi
ok "Services systemd configurés"

# ── 9. Démarrage ─────────────────────────────────────────────────
echo ""
info "Démarrage des services..."
systemctl --user restart mi-saina-backend mi-saina-frontend
sleep 6

if curl -s http://localhost:8000/health | grep -q "ok"; then
    ok "Backend actif : http://localhost:8000"
else
    warn "Backend pas encore prêt — attendez quelques secondes"
fi
ok "Frontend : http://localhost:3001"

# ── 10. Résumé ────────────────────────────────────────────────────
echo ""
echo -e "${G}╔══════════════════════════════════════════╗${NC}"
echo -e "${G}║       ✅ Installation terminée !          ║${NC}"
echo -e "${G}╠══════════════════════════════════════════╣${NC}"
echo -e "${G}║  Backend  → http://localhost:8000         ║${NC}"
echo -e "${G}║  Frontend → http://localhost:3001         ║${NC}"
echo -e "${G}║  API Docs → http://localhost:8000/docs    ║${NC}"
echo -e "${G}╠══════════════════════════════════════════╣${NC}"
echo -e "${G}║  Commandes utiles :                       ║${NC}"
echo -e "${G}║  systemctl --user status mi-saina-backend ║${NC}"
echo -e "${G}║  bash ~/mi-saina/start.sh                 ║${NC}"
echo -e "${G}╚══════════════════════════════════════════╝${NC}"
echo ""

# Importer les modèles LM Studio si présents
if [ -d "$HOME/.lmstudio/models" ]; then
    echo -e "${Y}[✦] LM Studio détecté ! Pour importer vos modèles :${NC}"
    echo "    bash $INSTALL_DIR/import_lmstudio.sh"
    echo ""
fi
