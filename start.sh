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

if ! pgrep -x ollama &>/dev/null; then
    echo "→ Démarrage d'Ollama..."
    ollama serve &>/tmp/mi-saina-ollama.log &
    sleep 2
fi

echo "→ Backend FastAPI (port 8000)..."
source "$VENV_DIR/bin/activate"
cd "$INSTALL_DIR/backend"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

echo "→ Frontend Next.js (port 3001)..."
cd "$INSTALL_DIR/frontend"
npm run dev -- --port 3001 &
FRONTEND_PID=$!

echo ""
echo "mi-saina actif :"
echo "  Frontend → http://localhost:3001"
echo "  Backend  → http://localhost:8000"
echo "  API Docs → http://localhost:8000/docs"
echo ""
echo "Ctrl+C pour arrêter."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
