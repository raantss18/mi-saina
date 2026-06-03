#!/usr/bin/env bash
# Import automatique de tous les modèles GGUF LM Studio vers Ollama
# Usage: bash ~/localmind/import_lmstudio.sh
set -e

BASE="${LMSTUDIO_DIR:-$HOME/.lmstudio/models}"
LOG="/tmp/ollama_lmstudio_import.log"

already_imported() {
    ollama list 2>/dev/null | awk '{print $1}' | grep -qx "$1"
}

import_gguf() {
    local name="$1" path="$2"
    if already_imported "$name"; then
        echo "⏭  $name déjà importé — skip"
        return
    fi
    if [ ! -f "$path" ]; then
        echo "⚠  Fichier introuvable: $path"
        return
    fi
    echo "▶  Importation de $name ($(du -h "$path" | cut -f1))..."
    printf "FROM %s\n" "$path" | ollama create "$name" -f /dev/stdin
    echo "✅ $name importé"
}

echo "=== Import LM Studio → Ollama $(date) ===" | tee "$LOG"

# Modèles texte (sans mmproj)
import_gguf "deepseek-r1:8b"          "$BASE/lmstudio-community/DeepSeek-R1-0528-Qwen3-8B-GGUF/DeepSeek-R1-0528-Qwen3-8B-Q3_K_L.gguf"
import_gguf "gemma3:12b"              "$BASE/lmstudio-community/gemma-3-12b-it-GGUF/gemma-3-12b-it-Q4_K_M.gguf"
import_gguf "phi4-reasoning:latest"   "$BASE/lmstudio-community/Phi-4-reasoning-plus-GGUF/Phi-4-reasoning-plus-Q4_K_M.gguf"
import_gguf "gpt-oss:20b"             "$BASE/lmstudio-community/gpt-oss-20b-GGUF/gpt-oss-20b-MXFP4.gguf"
import_gguf "magistral:small"         "$BASE/lmstudio-community/Magistral-Small-2506-GGUF/Magistral-Small-2506-Q4_K_M.gguf"
import_gguf "gemma4:26b"              "$BASE/lmstudio-community/gemma-4-26B-A4B-it-GGUF/gemma-4-26B-A4B-it-Q4_K_M.gguf"
import_gguf "qwen3.6:35b"             "$BASE/lmstudio-community/Qwen3.6-35B-A3B-GGUF/Qwen3.6-35B-A3B-Q4_K_M.gguf"

# Ajouter ici de nouveaux modèles LM Studio au fur et à mesure :
# import_gguf "nom:tag"  "$BASE/lmstudio-community/Dossier/fichier.gguf"

echo ""
echo "=== Modèles Ollama disponibles ==="
ollama list

echo "Import terminé." | tee -a "$LOG"
