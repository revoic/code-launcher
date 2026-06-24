#!/bin/bash
# ============================================================================
# Code Launcher – Runner (macOS / Linux)
# Wird vom Bootstrap (Start_macOS.command) aufgerufen, nachdem das Repo
# auf den neuesten Stand gebracht wurde. Kümmert sich um venv, Pakete
# und das Starten von Streamlit.
# ============================================================================

set -e
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$HOME/.code-launcher-venv"

# --- Python suchen -----------------------------------------------------
PY_BIN=""
for candidate in python3.12 python3.11 python3.10 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    PY_BIN="$(command -v "$candidate")"
    break
  fi
done

if [ -z "$PY_BIN" ]; then
  echo "⚠️  Python 3 wurde nicht gefunden."
  echo "    Installiere Python von https://www.python.org/downloads/"
  open "https://www.python.org/downloads/" 2>/dev/null || true
  read -r -p "Drücke Enter zum Beenden …" _
  exit 1
fi
echo "✓ Python: $PY_BIN"

# --- venv anlegen ------------------------------------------------------
if [ ! -d "$VENV_DIR" ]; then
  echo "→ Lege virtuelle Umgebung an (einmalig) …"
  "$PY_BIN" -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# --- Pakete installieren ----------------------------------------------
REQ_FILE="$APP_DIR/requirements.txt"
REQ_HASH_FILE="$VENV_DIR/.requirements.hash"
NEW_HASH="$(shasum -a 256 "$REQ_FILE" | awk '{print $1}')"
OLD_HASH="$(cat "$REQ_HASH_FILE" 2>/dev/null || echo none)"

if [ "$NEW_HASH" != "$OLD_HASH" ]; then
  echo "→ Aktualisiere Pakete …"
  python -m pip install --quiet --upgrade pip
  python -m pip install --quiet -r "$REQ_FILE"
  echo "$NEW_HASH" > "$REQ_HASH_FILE"
else
  echo "✓ Pakete aktuell."
fi

# --- Streamlit starten ------------------------------------------------
echo ""
echo "================================================"
echo "  Öffne den Code Launcher im Browser …"
echo "  Zum Beenden dieses Fenster schließen."
echo "================================================"
echo ""

exec python -m streamlit run "$APP_DIR/app.py" \
  --server.headless false \
  --browser.gatherUsageStats false
