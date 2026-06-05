#!/usr/bin/env bash
# mi-saina — Démarrage manuel (sans systemd)
set -e

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${VENV_DIR:-$HOME/mi-saina-env}"

# Fallback sur l'ancien venv si présent
if [ ! -d "$VENV_DIR" ] && [ -d "$HOME/localmind-env" ]; then
    VENV_DIR="$HOME/localmind-env"
fi

echo "Démarrage de mi-saina..."

# Bascule automatique si un port est déjà occupé par un autre service.
port_in_use() {
    local p="$1"
    if command -v ss &>/dev/null;   then ss -ltnH 2>/dev/null | awk '{print $4}' | grep -qE "[:.]${p}\$"
    elif command -v lsof &>/dev/null; then lsof -iTCP:"$p" -sTCP:LISTEN >/dev/null 2>&1
    else (exec 3<>"/dev/tcp/127.0.0.1/$p") 2>/dev/null
    fi
}
pick_port() {
    local p="$1" max=$(( $1 + 50 ))
    while [ "$p" -le "$max" ]; do
        port_in_use "$p" || { echo "$p"; return 0; }
        p=$(( p + 1 ))
    done
    echo "$1"
}

BACKEND_PORT="$(pick_port "${BACKEND_PORT:-8000}")"
FRONTEND_PORT="$(pick_port "${FRONTEND_PORT:-3001}")"
[ "$BACKEND_PORT"  != "8000" ] && echo "⚠ Port 8000 occupé → backend sur $BACKEND_PORT"
[ "$FRONTEND_PORT" != "3001" ] && echo "⚠ Port 3001 occupé → frontend sur $FRONTEND_PORT"
# Le frontend doit savoir où joindre le backend (port éventuellement décalé).
export NEXT_PUBLIC_API_BASE="http://localhost:$BACKEND_PORT"

if ! pgrep -x ollama &>/dev/null; then
    echo "→ Démarrage d'Ollama..."
    ollama serve &>/tmp/mi-saina-ollama.log &
    sleep 2
fi

echo "→ Backend FastAPI (port $BACKEND_PORT)..."
source "$VENV_DIR/bin/activate"
cd "$INSTALL_DIR/backend"
uvicorn main:app --host 0.0.0.0 --port "$BACKEND_PORT" --reload &
BACKEND_PID=$!

echo "→ Frontend Next.js (port $FRONTEND_PORT)..."
cd "$INSTALL_DIR/frontend"
npm run dev -- --port "$FRONTEND_PORT" &
FRONTEND_PID=$!

echo ""
echo "mi-saina actif :"
echo "  Frontend → http://localhost:$FRONTEND_PORT"
echo "  Backend  → http://localhost:$BACKEND_PORT"
echo "  API Docs → http://localhost:$BACKEND_PORT/docs"
echo ""
echo "Ctrl+C pour arrêter."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
