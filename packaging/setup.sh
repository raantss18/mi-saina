#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
#  mi-saina — Installeur .run (s'installe dans /opt/mi-saina)
#  Lancé par l'archive auto-extractible. NE PAS lancer avec sudo :
#  le script demande le mot de passe au bon moment (les modèles Ollama
#  doivent s'installer pour TON utilisateur, pas pour root).
# ─────────────────────────────────────────────────────────────────
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"      # dossier extrait de l'archive
PREFIX="/opt/mi-saina"

R='\033[0;31m'; G='\033[0;32m'; Y='\033[1;33m'; B='\033[0;34m'; NC='\033[0m'
ok(){ echo -e "${G}[✓]${NC} $1"; }
warn(){ echo -e "${Y}[⚠]${NC} $1"; }
info(){ echo -e "${B}[→]${NC} $1"; }
err(){ echo -e "${R}[✗]${NC} $1"; exit 1; }
have(){ command -v "$1" &>/dev/null; }

echo ""
echo -e "${B}╔══════════════════════════════════════════╗${NC}"
echo -e "${B}║        mi-saina — Installation (.run)     ║${NC}"
echo -e "${B}║   Assistant IA local · créé par Antsa     ║${NC}"
echo -e "${B}╚══════════════════════════════════════════╝${NC}"
echo ""

[ "$(id -u)" -eq 0 ] && err "Ne lance PAS l'installeur avec sudo. Relance-le normalement :\n   ./mi-saina-*.run\n(Le mot de passe administrateur sera demandé automatiquement.)"

USER_NAME="$(id -un)"; USER_GROUP="$(id -gn)"
$( sudo -v ) || err "Privilèges administrateur requis pour installer dans $PREFIX."
SUDO="sudo"

UPDATING=""; [ -d "$PREFIX" ] && UPDATING=1 && info "Installation existante détectée → mise à jour (config/données préservées)."

# ── 1. Dépendances de base (curl) ─────────────────────────────────
. /etc/os-release 2>/dev/null || true
IDS="${ID:-} ${ID_LIKE:-}"
INSTALL=""
if   echo "$IDS" | grep -qiE 'arch';            then INSTALL="$SUDO pacman -S --needed --noconfirm"
elif echo "$IDS" | grep -qiE 'debian|ubuntu';   then INSTALL="$SUDO apt-get install -y"; $SUDO apt-get update -y || true
elif echo "$IDS" | grep -qiE 'fedora|rhel|centos'; then INSTALL="$SUDO dnf install -y"
elif echo "$IDS" | grep -qiE 'suse';            then INSTALL="$SUDO zypper install -y"
elif have apk;                                   then INSTALL="$SUDO apk add"
elif have xbps-install;                          then INSTALL="$SUDO xbps-install -Sy"
fi
if ! have curl && [ -n "$INSTALL" ]; then info "Installation de curl…"; $INSTALL curl python3 || true; fi
have python3 || { [ -n "$INSTALL" ] && $INSTALL python3 || err "python3 requis."; }

# ── 2. Ollama (moteur des modèles) ────────────────────────────────
if ! have ollama; then
    info "Installation d'Ollama…"
    curl -fsSL https://ollama.com/install.sh | sh
fi
have ollama && ok "Ollama $(ollama --version 2>&1 | head -1)"
if ! pgrep -x ollama &>/dev/null; then
    info "Démarrage d'Ollama…"; (ollama serve &>/tmp/mi-saina-ollama.log &) || true; sleep 3
fi

# ── 3. Matériel + choix du modèle ─────────────────────────────────
RAM_GB=$(awk '/MemTotal/{printf "%.0f",$2/1024/1024}' /proc/meminfo 2>/dev/null || echo 0)
VRAM_MB=0; have nvidia-smi && VRAM_MB=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -dc '0-9' || echo 0)
VRAM_GB=$(( VRAM_MB / 1024 ))
info "Matériel : ${RAM_GB} GB RAM, VRAM ${VRAM_GB} GB"
if   [ "$VRAM_GB" -ge 16 ] || { [ "$VRAM_MB" = 0 ] && [ "$RAM_GB" -ge 48 ]; }; then TIER="big"
elif [ "$VRAM_GB" -ge 8 ]  || { [ "$VRAM_MB" = 0 ] && [ "$RAM_GB" -ge 16 ]; }; then TIER="mid"
else TIER="small"; fi
case "$TIER" in
    big)   QWEN="qwen3:14b";   DEEPSEEK="deepseek-r1:14b"; GEMMA="gemma3:12b" ;;
    mid)   QWEN="qwen3:8b";    DEEPSEEK="deepseek-r1:8b";  GEMMA="gemma3:4b"  ;;
    small) QWEN="qwen2.5:3b";  DEEPSEEK="deepseek-r1:1.5b";GEMMA="gemma3:1b"  ;;
esac
echo ""
echo -e "${Y}Modèle recommandé pour ta machine (palier « $TIER ») :${NC}"
echo "   1) Qwen      → $QWEN   (polyvalent, recommandé)"
echo "   2) DeepSeek  → $DEEPSEEK   (raisonnement)"
echo "   3) Gemma     → $GEMMA   (léger)"
echo "   4) Autre tag Ollama"
if [ -t 0 ]; then read -rp "Ton choix [1] : " CHOICE; else CHOICE=1; fi
case "${CHOICE:-1}" in
    2) MODEL="$DEEPSEEK" ;; 3) MODEL="$GEMMA" ;;
    4) read -rp "Tag Ollama : " MODEL ;; *) MODEL="$QWEN" ;;
esac

# Langue de l'application (défaut : anglais)
echo ""
echo "Language / Langue / Fiteny :  1) English   2) Français   3) Malagasy"
if [ -t 0 ]; then read -rp "Choice [1] : " LCHOICE; else LCHOICE=1; fi
case "${LCHOICE:-1}" in 2) APP_LANG=fr ;; 3) APP_LANG=mg ;; *) APP_LANG=en ;; esac
mkdir -p "$HOME/.config/mi-saina"
python3 - "$APP_LANG" <<'PY' || true
import json, os, sys
p = os.path.expanduser("~/.config/mi-saina/settings.json")
d = {}
try:
    with open(p) as f: d = json.load(f)
except Exception: pass
d["LANGUAGE"] = sys.argv[1]
os.makedirs(os.path.dirname(p), exist_ok=True)
open(p, "w").write(json.dumps(d, indent=2, ensure_ascii=False))
PY
ok "Langue / Language : $APP_LANG"

info "Téléchargement du modèle $MODEL (peut prendre plusieurs minutes)…"
ollama pull "$MODEL" || warn "Échec — réessaie plus tard : ollama pull $MODEL"
info "Modèle d'embeddings (mémoire sémantique)…"
ollama pull nomic-embed-text || warn "Embeddings indisponibles — ollama pull nomic-embed-text"

# ── 4. Copie du bundle dans /opt (code en lecture seule) ──────────
info "Installation dans $PREFIX…"
$SUDO mkdir -p "$PREFIX/bin"
$SUDO cp -f "$SRC/bin/mi-saina" "$PREFIX/bin/mi-saina"
$SUDO chmod +x "$PREFIX/bin/mi-saina"
$SUDO cp -rf "$SRC/backend/." "$PREFIX/backend/"   # écrase le code, préserve backend/data/
$SUDO cp -f  "$SRC/VERSION" "$PREFIX/VERSION"
$SUDO mkdir -p /usr/share/icons/hicolor/128x128/apps
$SUDO cp -f "$SRC/icons/128x128.png" /usr/share/icons/hicolor/128x128/apps/mi-saina.png 2>/dev/null || true
[ -f "$SRC/uninstall.sh" ] && $SUDO cp -f "$SRC/uninstall.sh" "$PREFIX/uninstall.sh" && $SUDO chmod +x "$PREFIX/uninstall.sh"

# Config + .env : seedés au 1er install, JAMAIS écrasés ensuite (éditions utilisateur).
if [ ! -d "$PREFIX/config" ]; then $SUDO cp -rf "$SRC/config" "$PREFIX/config"; fi
if [ ! -f "$PREFIX/.env" ]; then
    printf 'REASONING_MODEL=%s\nFAST_MODEL=%s\n' "$MODEL" "$MODEL" | $SUDO tee "$PREFIX/.env" >/dev/null
elif [ -z "$UPDATING" ]; then
    printf 'REASONING_MODEL=%s\nFAST_MODEL=%s\n' "$MODEL" "$MODEL" | $SUDO tee "$PREFIX/.env" >/dev/null
fi

# Données + dossiers modifiables → propriété de l'utilisateur (backend lancé en user).
$SUDO mkdir -p "$PREFIX/backend/data"
$SUDO chown -R "$USER_NAME:$USER_GROUP" "$PREFIX/config" "$PREFIX/.env" "$PREFIX/backend/data"
ok "Bundle installé dans $PREFIX"

# ── 5. Environnement Python (venv root, lecture seule) ────────────
info "Environnement Python…"
$SUDO python3 -m venv "$PREFIX/venv"
$SUDO "$PREFIX/venv/bin/pip" install --upgrade pip -q
$SUDO "$PREFIX/venv/bin/pip" install -q -r "$PREFIX/backend/requirements.txt" || \
    $SUDO "$PREFIX/venv/bin/pip" install -q fastapi uvicorn httpx "pydantic>=2" pydantic-settings \
        python-dotenv aiofiles websockets rich sqlalchemy aiosqlite numpy ollama ddgs \
        pypdf python-docx openpyxl python-pptx
ok "Dépendances Python installées"

# ── 6. Intégration bureau (menu Applications + tray au démarrage) ──
$SUDO tee /usr/share/applications/mi-saina.desktop >/dev/null <<DESKEOF
[Desktop Entry]
Type=Application
Name=mi-saina
Comment=Assistant IA local créé par Antsa
Exec=$PREFIX/bin/mi-saina
Icon=mi-saina
Terminal=false
Categories=Utility;
Keywords=IA;assistant;ollama;mi-saina;
StartupNotify=true
DESKEOF
$SUDO mkdir -p /etc/xdg/autostart
$SUDO tee /etc/xdg/autostart/mi-saina.desktop >/dev/null <<AUTOEOF
[Desktop Entry]
Type=Application
Name=mi-saina (barre système)
Comment=Démarre mi-saina dans la barre système
Exec=$PREFIX/bin/mi-saina --minimized
Icon=mi-saina
Terminal=false
X-GNOME-Autostart-enabled=true
AUTOEOF
have update-desktop-database && $SUDO update-desktop-database /usr/share/applications 2>/dev/null || true
ok "Intégration bureau OK (menu + barre système au démarrage)"

echo ""
echo -e "${G}╔══════════════════════════════════════════╗${NC}"
echo -e "${G}║        ✅ mi-saina est installé !         ║${NC}"
echo -e "${G}╚══════════════════════════════════════════╝${NC}"
echo "  • Cherche « mi-saina » dans ton menu d'applications, ou lance :"
echo "      $PREFIX/bin/mi-saina"
echo "  • L'appli démarre le backend toute seule (rien d'autre à lancer)."
echo "  • Désinstaller : sudo $PREFIX/uninstall.sh"
echo ""
