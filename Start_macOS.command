#!/bin/bash
# ============================================================================
# Code Launcher – Start-Skript für macOS (BOOTSTRAP)
# ============================================================================
# Diese kleine Datei holt sich die neueste Version aus dem Git-Repo
# und startet sie. Sie selbst ändert sich praktisch nie – die ganze
# Update-Logik lebt im Repo (siehe run.sh).
# ============================================================================

set -e
cd "$(dirname "$0")"

# === KONFIGURATION ====================================================
# Trage hier die HTTPS-URL deines Code-Launcher-Repos ein.
# Beispiel: https://github.com/max-kirchhoff/code-launcher.git
REPO_URL="https://github.com/revoic/code-launcher.git"
BRANCH="main"
# ======================================================================

APP_HOME="$HOME/.code-launcher-app"

echo ""
echo "================================================"
echo "  🚀 Code Launcher"
echo "================================================"
echo ""

# --- Platzhalter-Check --------------------------------------------------
if [[ "$REPO_URL" == *"CHANGE-ME"* ]]; then
  echo "⚠️  Im Start-Skript ist noch keine Repo-URL eingetragen."
  echo "    Öffne 'Start_macOS.command' in einem Texteditor und"
  echo "    ersetze die REPO_URL durch deine GitHub-Adresse."
  echo ""
  read -r -p "Drücke Enter zum Beenden …" _
  exit 1
fi

# --- 1) Git prüfen ------------------------------------------------------
if ! command -v git >/dev/null 2>&1; then
  echo "⚠️  Git ist nicht installiert."
  echo ""
  echo "Schnellste Variante (im Terminal eingeben):"
  echo "   xcode-select --install"
  echo ""
  echo "Alternativ: https://git-scm.com/download/mac"
  open "https://git-scm.com/download/mac" 2>/dev/null || true
  read -r -p "Drücke Enter zum Beenden …" _
  exit 1
fi

# --- 2) Repo klonen oder updaten ---------------------------------------
if [ ! -d "$APP_HOME/.git" ]; then
  echo "→ Erstinstallation: lade Code Launcher herunter …"
  rm -rf "$APP_HOME"
  if ! git clone --depth 1 -b "$BRANCH" "$REPO_URL" "$APP_HOME"; then
    echo ""
    echo "⚠️  Download fehlgeschlagen."
    echo "    Prüfe deine Internetverbindung oder die Repo-URL."
    read -r -p "Drücke Enter zum Beenden …" _
    exit 1
  fi
else
  echo "→ Suche nach Updates …"
  if git -C "$APP_HOME" fetch --depth 1 origin "$BRANCH" 2>/dev/null; then
    BEFORE="$(git -C "$APP_HOME" rev-parse HEAD)"
    git -C "$APP_HOME" reset --hard "origin/$BRANCH" >/dev/null
    AFTER="$(git -C "$APP_HOME" rev-parse HEAD)"
    if [ "$BEFORE" != "$AFTER" ]; then
      echo "✓ Neue Version installiert ($(echo "$AFTER" | cut -c1-7))."
    else
      echo "✓ Schon auf der neuesten Version."
    fi
  else
    echo "  (offline – fahre mit lokal vorhandener Version fort)"
  fi
fi

# Version für die App weitergeben
export CODE_LAUNCHER_VERSION="$(git -C "$APP_HOME" rev-parse --short HEAD 2>/dev/null || echo unknown)"

# --- 3) An run.sh übergeben -------------------------------------------
exec bash "$APP_HOME/run.sh"
