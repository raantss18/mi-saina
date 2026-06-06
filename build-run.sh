#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
#  Construit l'installeur auto-extractible  dist/mi-saina-<ver>-x86_64.run
#  (binaire natif prébuilt + backend + config + installeur).
#  Usage : bash build-run.sh
# ─────────────────────────────────────────────────────────────────
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
VER="$(tr -d '[:space:]' < "$ROOT/VERSION")"
OUT="$ROOT/dist"
RUN="$OUT/mi-saina-$VER-x86_64.run"
STAGE="$(mktemp -d /tmp/mi-saina-stage.XXXXXX)"
trap 'rm -rf "$STAGE"' EXIT

B='\033[0;34m'; G='\033[0;32m'; NC='\033[0m'
info(){ echo -e "${B}[→]${NC} $1"; }
ok(){ echo -e "${G}[✓]${NC} $1"; }

info "1/4 — Build du frontend (export statique)…"
( cd "$ROOT/frontend" && MS_DESKTOP=1 NEXT_PUBLIC_API_BASE=http://localhost:8000 npm run build >/dev/null )

info "2/4 — Compilation du binaire natif (release)…"
( cd "$ROOT/frontend/src-tauri" && cargo build --release )
BIN="$ROOT/frontend/src-tauri/target/release/mi-saina"
[ -x "$BIN" ] || { echo "binaire introuvable"; exit 1; }

info "3/4 — Préparation du contenu…"
mkdir -p "$STAGE/bin" "$STAGE/icons"
cp "$BIN" "$STAGE/bin/mi-saina"
cp -r "$ROOT/backend" "$STAGE/backend"
# Ne pas embarquer : données locales, caches, tests, dossiers vides.
rm -rf "$STAGE/backend/data" "$STAGE/backend/tests" "$STAGE/backend/photo-vacance"
find "$STAGE/backend" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
cp -r "$ROOT/config" "$STAGE/config"
cp "$ROOT/VERSION" "$STAGE/VERSION"
cp "$ROOT/frontend/src-tauri/icons/128x128.png" "$STAGE/icons/128x128.png"
cp "$ROOT/packaging/setup.sh" "$STAGE/setup.sh"
cp "$ROOT/packaging/uninstall.sh" "$STAGE/uninstall.sh"
chmod +x "$STAGE/setup.sh" "$STAGE/uninstall.sh" "$STAGE/bin/mi-saina"

info "4/4 — Assemblage de l'archive auto-extractible…"
mkdir -p "$OUT"
cat > "$RUN" <<'HEADER'
#!/usr/bin/env bash
# Installeur auto-extractible mi-saina — créé par Antsa.
set -e
echo "Extraction de mi-saina…"
TMP="$(mktemp -d /tmp/mi-saina-install.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT
LINE=$(awk '/^__MISAINA_ARCHIVE__$/{print NR + 1; exit 0}' "$0")
tail -n +"$LINE" "$0" | tar xz -C "$TMP"
bash "$TMP/setup.sh"
exit $?
__MISAINA_ARCHIVE__
HEADER
tar czf - -C "$STAGE" . >> "$RUN"
chmod +x "$RUN"

ok "Installeur prêt : $RUN ($(du -h "$RUN" | cut -f1))"
echo "    Test rapide :  bash $RUN        (installe dans /opt/mi-saina)"
