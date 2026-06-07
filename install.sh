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

PKG_FAMILY="unknown"; INSTALL_CMD=""; DEV_PKGS=""; DESKTOP_PKGS=""
have() { command -v "$1" &>/dev/null; }
# Pas de sudo si déjà root (utile en conteneur / CI)
SUDO="sudo"; [ "$(id -u)" -eq 0 ] && SUDO=""

# ── Détection de ports occupés ────────────────────────────────────
# Un port déjà pris par un AUTRE service ne doit plus faire planter l'install :
# on bascule automatiquement sur le prochain port libre.
port_in_use() {
    local p="$1"
    if have ss;   then ss -ltnH 2>/dev/null | awk '{print $4}' | grep -qE "[:.]${p}\$"
    elif have lsof; then lsof -iTCP:"$p" -sTCP:LISTEN >/dev/null 2>&1
    else (exec 3<>"/dev/tcp/127.0.0.1/$p") 2>/dev/null
    fi
}
# Premier port libre à partir d'un port préféré (cherche jusqu'à +50).
pick_port() {
    local p="$1" max=$(( $1 + 50 ))
    while [ "$p" -le "$max" ]; do
        port_in_use "$p" || { echo "$p"; return 0; }
        p=$(( p + 1 ))
    done
    echo "$1"   # rien de libre trouvé → on garde le préféré
}

# ── Fenêtre desktop (Tauri) : compile l'appli native + l'ajoute au menu
#    Applications et au démarrage de session (icône dans la barre système).
#    Tout est best-effort : en cas d'échec, l'appli web reste utilisable.
#    Désactivable avec MISAINA_NO_DESKTOP=1.
install_desktop() {
    [ -n "${MISAINA_NO_DESKTOP:-}" ] && { info "Fenêtre desktop ignorée (MISAINA_NO_DESKTOP=1)."; return 0; }

    info "Préparation de la fenêtre desktop (Tauri)…"
    # Dépendances de build (webkit, tray, rust) — best effort.
    if [ "$PKG_FAMILY" != "unknown" ] && [ -n "$DESKTOP_PKGS" ]; then
        # shellcheck disable=SC2086
        $INSTALL_CMD $DESKTOP_PKGS || warn "Dépendances desktop partiellement installées — le build peut échouer."
    fi
    if ! have cargo; then
        warn "Rust/cargo introuvable → fenêtre desktop non compilée (l'appli web reste sur http://localhost:$FRONTEND_PORT)."
        warn "Pour l'activer plus tard : installe rust + webkit2gtk, puis relance : bash install.sh"
        return 0
    fi

    # 1) Export statique du frontend (embarqué dans le binaire ; pointe vers le backend détecté).
    info "Build du frontend desktop (export statique)…"
    ( cd "$INSTALL_DIR/frontend" && MS_DESKTOP=1 NEXT_PUBLIC_API_BASE="$API_BASE_URL" npm run build ) \
        || { warn "Build frontend desktop échoué — fenêtre non installée."; return 0; }

    # 2) Compilation du binaire natif (long au 1er build).
    info "Compilation de la fenêtre native (Rust — plusieurs minutes au 1er build)…"
    ( cd "$INSTALL_DIR/frontend/src-tauri" && cargo build --release ) \
        || { warn "Compilation desktop échouée — fenêtre non installée."; return 0; }

    local BIN="$INSTALL_DIR/frontend/src-tauri/target/release/mi-saina"
    [ -x "$BIN" ] || { warn "Binaire desktop introuvable après build."; return 0; }

    # 3) Icône.
    mkdir -p "$HOME/.local/share/icons/hicolor/128x128/apps"
    cp "$INSTALL_DIR/frontend/src-tauri/icons/128x128.png" \
       "$HOME/.local/share/icons/hicolor/128x128/apps/mi-saina.png" 2>/dev/null || true

    # 4) Lanceur dans le menu Applications.
    mkdir -p "$HOME/.local/share/applications"
    cat > "$HOME/.local/share/applications/mi-saina.desktop" <<DESKEOF
[Desktop Entry]
Type=Application
Name=mi-saina
Comment=Assistant IA local créé par Antsa
Exec=$BIN
Icon=mi-saina
Terminal=false
Categories=Utility;
Keywords=IA;assistant;ollama;mi-saina;
StartupNotify=true
DESKEOF

    # 5) Démarrage automatique dans la barre système (fenêtre masquée) à l'ouverture de session.
    mkdir -p "$HOME/.config/autostart"
    cat > "$HOME/.config/autostart/mi-saina.desktop" <<AUTOEOF
[Desktop Entry]
Type=Application
Name=mi-saina (barre système)
Comment=Démarre mi-saina dans la barre système
Exec=$BIN --minimized
Icon=mi-saina
Terminal=false
X-GNOME-Autostart-enabled=true
AUTOEOF

    command -v update-desktop-database &>/dev/null && \
        update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
    ok "Fenêtre desktop installée : menu Applications + barre système au démarrage (clic = ouvre la fenêtre native)."
}

if echo "$DISTRO_IDS" | grep -qiE 'arch'; then
    PKG_FAMILY="arch"
    INSTALL_CMD="$SUDO pacman -S --needed --noconfirm"
    DEV_PKGS="python python-pip nodejs npm git curl base-devel"
    DESKTOP_PKGS="webkit2gtk-4.1 libappindicator-gtk3 librsvg rust"
elif echo "$DISTRO_IDS" | grep -qiE 'debian|ubuntu'; then
    PKG_FAMILY="debian"
    INSTALL_CMD="$SUDO apt-get install -y"
    DEV_PKGS="python3 python3-pip python3-venv nodejs npm git curl build-essential"
    DESKTOP_PKGS="libwebkit2gtk-4.1-dev libayatana-appindicator3-dev librsvg2-dev libssl-dev cargo"
    $SUDO apt-get update -y || true
elif echo "$DISTRO_IDS" | grep -qiE 'fedora|rhel|centos'; then
    PKG_FAMILY="fedora"
    INSTALL_CMD="$SUDO dnf install -y"
    DEV_PKGS="python3 python3-pip nodejs npm git curl @development-tools"
    DESKTOP_PKGS="webkit2gtk4.1-devel libappindicator-gtk3-devel librsvg2-devel openssl-devel cargo"
elif echo "$DISTRO_IDS" | grep -qiE 'suse'; then
    PKG_FAMILY="suse"
    INSTALL_CMD="$SUDO zypper install -y"
    DEV_PKGS="python3 python3-pip nodejs npm git curl gcc gcc-c++ make"
    DESKTOP_PKGS="webkit2gtk3-devel libappindicator3-1 librsvg-devel libopenssl-devel cargo"
elif have xbps-install; then
    PKG_FAMILY="void"
    INSTALL_CMD="$SUDO xbps-install -Sy"
    DEV_PKGS="python3 python3-pip nodejs git curl base-devel"
    DESKTOP_PKGS="webkit2gtk-devel libappindicator-devel librsvg-devel rust cargo"
elif have apk; then
    PKG_FAMILY="alpine"
    INSTALL_CMD="$SUDO apk add"
    DEV_PKGS="python3 py3-pip nodejs npm git curl build-base"
    DESKTOP_PKGS="webkit2gtk-dev libappindicator-dev librsvg-dev rust cargo"
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

# Modèle d'embeddings dédié (mémoire sémantique) — petit, indépendant du modèle
# génératif (certains, comme gemma3, ne savent pas faire d'embeddings).
info "Téléchargement du modèle d'embeddings (nomic-embed-text, ~270 Mo)…"
ollama pull nomic-embed-text || warn "Embeddings indisponibles — réessaie : ollama pull nomic-embed-text"

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

# Arrêter d'abord NOS services (sinon ils occuperaient « leur » port et seraient
# détectés comme conflit) ; les ports occupés par d'AUTRES services sont contournés.
systemctl --user stop mi-saina-backend mi-saina-frontend 2>/dev/null || true

BACKEND_PORT="$(pick_port "${BACKEND_PORT:-8000}")"
FRONTEND_PORT="$(pick_port "${FRONTEND_PORT:-3001}")"
[ "$BACKEND_PORT"  != "8000" ] && warn "Port 8000 occupé → backend sur le port $BACKEND_PORT"
[ "$FRONTEND_PORT" != "3001" ] && warn "Port 3001 occupé → frontend sur le port $FRONTEND_PORT"
API_BASE_URL="http://localhost:$BACKEND_PORT"

cat > "$HOME/.config/systemd/user/mi-saina-backend.service" <<SVCEOF
[Unit]
Description=mi-saina Backend (FastAPI)
After=network.target

[Service]
Type=simple
WorkingDirectory=$INSTALL_DIR/backend
ExecStart=$VENV_DIR/bin/uvicorn main:app --host 127.0.0.1 --port $BACKEND_PORT
Restart=on-failure
RestartSec=5
Environment=HOME=$HOME
Environment=PATH=$VENV_DIR/bin:$HOME/.local/bin:$HOME/bin:/usr/local/bin:/usr/bin:/bin

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
ExecStart=/usr/bin/npm run dev -- --hostname 127.0.0.1 --port $FRONTEND_PORT
Restart=on-failure
RestartSec=5
Environment=HOME=$HOME
Environment=NEXT_PUBLIC_API_BASE=$API_BASE_URL

[Install]
WantedBy=default.target
SVCEOF

systemctl --user daemon-reload
systemctl --user enable --now mi-saina-backend mi-saina-frontend
command -v loginctl &>/dev/null && loginctl enable-linger "$USER" 2>/dev/null || true
ok "Services configurés et démarrés (backend:$BACKEND_PORT, frontend:$FRONTEND_PORT)"

# ── 9. Vérification ───────────────────────────────────────────────
sleep 5
if curl -s "http://localhost:$BACKEND_PORT/health" 2>/dev/null | grep -q ok; then
    ok "Backend actif : http://localhost:$BACKEND_PORT"
else
    warn "Backend pas encore prêt — voir : journalctl --user -u mi-saina-backend -n 50"
fi

# ── 10. Fenêtre desktop (menu Applications + barre système) ────────
install_desktop

echo ""
echo -e "${G}╔══════════════════════════════════════════╗${NC}"
echo -e "${G}║        ✅ Installation terminée !         ║${NC}"
echo -e "${G}╠══════════════════════════════════════════╣${NC}"
echo -e "${G}  Interface → http://localhost:$FRONTEND_PORT"
echo -e "${G}  API       → http://localhost:$BACKEND_PORT"
echo -e "${G}  Modèle    → $MODEL${NC}"
echo -e "${G}╚══════════════════════════════════════════╝${NC}"
echo ""
echo "Application :"
echo "  • Fenêtre desktop : cherche « mi-saina » dans ton menu d'applications."
echo "  • Au prochain démarrage de session, l'icône apparaît dans la barre système (clic = ouvre la fenêtre)."
echo "  • Version web (au besoin) : http://localhost:$FRONTEND_PORT"
echo ""
echo "Commandes utiles :"
echo "  systemctl --user status mi-saina-backend"
echo "  bash $INSTALL_DIR/start.sh        # démarrage manuel sans systemd"
echo ""
