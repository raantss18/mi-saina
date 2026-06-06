#!/usr/bin/env bash
# Désinstalle mi-saina installé via .run (/opt/mi-saina). À lancer avec sudo.
set -euo pipefail
PREFIX="/opt/mi-saina"

[ "$(id -u)" -eq 0 ] || { echo "Lance : sudo $0"; exit 1; }

echo "Suppression de mi-saina…"
rm -f /usr/share/applications/mi-saina.desktop
rm -f /etc/xdg/autostart/mi-saina.desktop
rm -f /usr/share/icons/hicolor/128x128/apps/mi-saina.png
rm -rf "$PREFIX"
command -v update-desktop-database &>/dev/null && update-desktop-database /usr/share/applications 2>/dev/null || true

echo "✓ mi-saina désinstallé."
echo "  Conservés (à supprimer manuellement si voulu) :"
echo "    • Modèles Ollama        : ollama list / ollama rm <modèle>"
echo "    • Réglages utilisateur  : ~/.config/mi-saina"
echo "    • Ollama lui-même reste installé."
