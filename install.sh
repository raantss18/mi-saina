#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
#  mi-saina — Installation automatique multi-distributions
#  Distros : Arch/EndeavourOS, Debian/Ubuntu, Fedora/RHEL, openSUSE,
#            Void, Alpine (détection automatique).
#  Usage   : bash install.sh
#  S'installe SUR PLACE (dans le dépôt cloné) — aucune donnée perso requise.
# ─────────────────────────────────────────────────────────────────
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$REPO_DIR"
VENV_DIR="${VENV_DIR:-$HOME/mi-saina-env}"

R='\033[0;31m'; G='\033[0;32m'; Y='\033[1;33m'; B='\033[0;34m'; NC='\033[0m'
ok()   { echo -e "${G}[✓]${NC} $1"; }
warn() { echo -e "${Y}[⚠]${NC} $1"; }
info() { echo -e "${B}[→]${NC} $1"; }
err()  { echo -e "${R}[✗]${NC} $1"; exit 1; }

echo ""
echo -e "${B}╔══════════════════════════════════════════╗${NC}"
echo -e "${B}║          mi-saina — Installation         ║${NC}"
echo -e "${B}║   Assistant IA local (Ollama) · Linux    ║${NC}"
echo -e "${B}╚══════════════════════════════════════════╝${NC}"
echo ""

# ── 1. Détection de la distribution ───────────────────────────────
ID=""; ID_LIKE=""
[ -r /etc/os-release ] && . /etc/os-release
DISTRO_IDS="${ID:-} ${ID_LIKE:-}"

PKG_FAMILY="unknown"; INSTALL_CMD=""; DEV_PKGS=""
have() { command -v "$1" &>/dev/null; }
# Pas de sudo si déjà root (utile en conteneur / CI)
SUDO="sudo"; [ "$(id -u)" -eq 0 ] && SUDO=""

if echo "$DISTRO_IDS" | grep -qiE 'arch'; then
    PKG_FAMILY="arch"
    INSTALL_CMD="$SUDO pacman -S --needed --noconfirm"
    DEV_PKGS="python python-pip nodejs npm git curl base-devel"
elif echo "$DISTRO_IDS" | grep -qiE 'debian|ubuntu'; then
    PKG_FAMILY="debian"
    INSTALL_CMD="$SUDO apt-get install -y"
    DEV_PKGS="python3 python3-pip python3-venv nodejs npm git curl build-essential"
    $SUDO apt-get update -y || true
elif echo "$DISTRO_IDS" | grep -qiE 'fedora|rhel|centos'; then
    PKG_FAMILY="fedora"
    INSTALL_CMD="$SUDO dnf install -y"
    DEV_PKGS="python3 python3-pip nodejs npm git curl @development-tools"
elif echo "$DISTRO_IDS" | grep -qiE 'suse'; then
    PKG_FAMILY="suse"
    INSTALL_CMD="$SUDO zypper install -y"
    DEV_PKGS="python3 python3-pip nodejs npm git curl gcc gcc-c++ make"
elif have xbps-install; then
    PKG_FAMILY="void"
    INSTALL_CMD="$SUDO xbps-install -Sy"
    DEV_PKGS="python3 python3-pip nodejs git curl base-devel"
elif have apk; then
    PKG_FAMILY="alpine"
    INSTALL_CMD="$SUDO apk add"
    DEV_PKGS="python3 py3-pip nodejs npm git curl build-base"
else
    warn "Distribution non reconnue — installe manuellement : python3, nodejs, npm, git, curl"
fi
info "Distribution : ${PRETTY_NAME:-$ID} (famille : $PKG_FAMILY)"

# ── 2. Dépendances système ────────────────────────────────────────
if [ "$PKG_FAMILY" != "unknown" ]; then
    if ! have python3 || ! have node || ! have git || ! have curl; then
        info "Installation des dépendances système…"
        # shellcheck disable=SC2086
        $INSTALL_CMD $DEV_PKGS || warn "Certains paquets n'ont pas pu être installés — vérifie manuellement."
    fi
fi
have python3 && ok "Python $(python3 --version 2>&1 | awk '{print $2}')"
have node    && ok "Node.js $(node --version 2>&1)"
have git     && ok "Git $(git --version | awk '{print $3}')"

# Mode test (CI / conteneur) : on valide la détection + les dépendances système
# puis on s'arrête avant Ollama / téléchargement de modèle / services systemd.
if [ -n "${MISAINA_TEST:-}" ]; then
    have python3 && have node && have git \
        && ok "Mode TEST : dépendances système OK pour la famille « $PKG_FAMILY »." \
        || err "Mode TEST : dépendances manquantes après installation."
    exit 0
fi

# ── 3. Ollama ─────────────────────────────────────────────────────
if ! have ollama; then
    info "Installation d'Ollama…"
    curl -fsSL https://ollama.com/install.sh | sh
fi
have ollama && ok "Ollama $(ollama --version 2>&1 | head -1)"

if ! pgrep -x ollama &>/dev/null; then
    info "Démarrage d'Ollama…"
    (ollama serve &>/tmp/mi-saina-ollama.log &) || true
    sleep 3
fi

# ── 4. Détection matériel + choix du modèle ───────────────────────
RAM_GB=$(awk '/MemTotal/{printf "%.0f",$2/1024/1024}' /proc/meminfo 2>/dev/null || echo 0)
VRAM_MB=0
if have nvidia-smi; then
    VRAM_MB=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -dc '0-9' || echo 0)
fi
VRAM_GB=$(( VRAM_MB / 1024 ))
info "Matériel : ${RAM_GB} GB RAM, VRAM ${VRAM_GB} GB $([ "$VRAM_MB" = 0 ] && echo '(pas de GPU NVIDIA détecté)')"

# Choix du palier selon VRAM (sinon RAM)
if   [ "$VRAM_GB" -ge 16 ] || { [ "$VRAM_MB" = 0 ] && [ "$RAM_GB" -ge 48 ]; }; then TIER="big"
elif [ "$VRAM_GB" -ge 8 ]  || { [ "$VRAM_MB" = 0 ] && [ "$RAM_GB" -ge 16 ]; }; then TIER="mid"
else TIER="small"; fi

case "$TIER" in
    big)   QWEN="qwen3:14b";   DEEPSEEK="deepseek-r1:14b"; GEMMA="gemma3:12b" ;;
    mid)   QWEN="qwen3:8b";    DEEPSEEK="deepseek-r1:8b";  GEMMA="gemma3:4b"  ;;
    small) QWEN="qwen2.5:3b";  DEEPSEEK="deepseek-r1:1.5b";GEMMA="gemma3:1b"  ;;
esac

echo ""
echo -e "${Y}Modèle local — recommandé pour ta machine : palier « $TIER »${NC}"
echo "   1) Qwen      → $QWEN   (polyvalent, recommandé)"
echo "   2) DeepSeek  → $DEEPSEEK   (raisonnement)"
echo "   3) Gemma     → $GEMMA   (Google, léger)"
echo "   4) Saisir un autre tag Ollama"
if [ -t 0 ]; then
    read -rp "Ton choix [1] : " CHOICE
else
    CHOICE=1   # non-interactif (CI) → recommandation par défaut
fi
CHOICE="${CHOICE:-1}"
case "$CHOICE" in
    1) MODEL="$QWEN" ;;
    2) MODEL="$DEEPSEEK" ;;
    3) MODEL="$GEMMA" ;;
    4) read -rp "Tag Ollama (ex: qwen2.5:7b) : " MODEL ;;
    *) MODEL="$QWEN" ;;
esac
info "Modèle choisi : $MODEL"
info "Téléchargement (peut prendre plusieurs minutes)…"
ollama pull "$MODEL" || warn "Échec du téléchargement — tu pourras réessayer avec : ollama pull $MODEL"

# ── 5. Configuration .env (minimale, sans données perso) ──────────
if [ ! -f "$INSTALL_DIR/.env" ]; then
    cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"
fi
# Renseigne le modèle choisi
sed -i -E "s|^REASONING_MODEL=.*|REASONING_MODEL=$MODEL|" "$INSTALL_DIR/.env"
sed -i -E "s|^FAST_MODEL=.*|FAST_MODEL=$MODEL|" "$INSTALL_DIR/.env"
ok ".env configuré (modèle : $MODEL)"

# ── 6. Environnement Python ───────────────────────────────────────
info "Création de l'environnement Python…"
python3 -m venv "$VENV_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
pip install --upgrade pip -q
info "Installation des dépendances Python…"
pip install -q \
    fastapi uvicorn httpx "pydantic>=2" pydantic-settings python-dotenv \
    aiofiles websockets rich sqlalchemy aiosqlite numpy ollama duckduckgo-search
ok "Dépendances Python installées"

# ── 7. Dépendances frontend ───────────────────────────────────────
info "Installation des dépendances frontend (npm)…"
( cd "$INSTALL_DIR/frontend" && npm install --silent )
ok "node_modules installé"

# ── 8. Services systemd utilisateur ───────────────────────────────
info "Configuration des services systemd…"
mkdir -p "$HOME/.config/systemd/user"

cat > "$HOME/.config/systemd/user/mi-saina-backend.service" <<SVCEOF
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

cat > "$HOME/.config/systemd/user/mi-saina-frontend.service" <<SVCEOF
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
systemctl --user enable --now mi-saina-backend mi-saina-frontend
command -v loginctl &>/dev/null && loginctl enable-linger "$USER" 2>/dev/null || true
ok "Services configurés et démarrés"

# ── 9. Vérification ───────────────────────────────────────────────
sleep 5
if curl -s http://localhost:8000/health 2>/dev/null | grep -q ok; then
    ok "Backend actif : http://localhost:8000"
else
    warn "Backend pas encore prêt — voir : journalctl --user -u mi-saina-backend -n 50"
fi

echo ""
echo -e "${G}╔══════════════════════════════════════════╗${NC}"
echo -e "${G}║        ✅ Installation terminée !         ║${NC}"
echo -e "${G}╠══════════════════════════════════════════╣${NC}"
echo -e "${G}║  Interface → http://localhost:3001        ║${NC}"
echo -e "${G}║  API       → http://localhost:8000        ║${NC}"
echo -e "${G}║  Modèle    → $MODEL${NC}"
echo -e "${G}╚══════════════════════════════════════════╝${NC}"
echo ""
echo "Commandes utiles :"
echo "  systemctl --user status mi-saina-backend"
echo "  bash $INSTALL_DIR/start.sh        # démarrage manuel sans systemd"
echo ""
