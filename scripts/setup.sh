#!/usr/bin/env bash
# scripts/setup.sh
# ─────────────────────────────────────────────────────────────
# Sets up the development environment for APK Editor Pro
# Usage:  bash scripts/setup.sh
# ─────────────────────────────────────────────────────────────
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ── Python version check ──────────────────────────────────────────────────
PYTHON_MIN="3.11"
PYTHON=$(python3 --version 2>&1 | awk '{print $2}')
info "Python: $PYTHON"
python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)" \
  || error "Python $PYTHON_MIN+ required. Got $PYTHON"

# ── Virtual environment ───────────────────────────────────────────────────
if [ ! -d ".venv" ]; then
  info "Creating virtual environment..."
  python3 -m venv .venv
fi
source .venv/bin/activate
info "Activated .venv"

# ── Pip install ───────────────────────────────────────────────────────────
info "Installing Python dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
info "Dependencies installed ✅"

# ── Java check ───────────────────────────────────────────────────────────
if command -v java &>/dev/null; then
  JAVA_VER=$(java -version 2>&1 | head -1)
  info "Java: $JAVA_VER"
else
  warn "Java not found – required for Android builds (JDK 17+)"
fi

# ── Android SDK check ─────────────────────────────────────────────────────
if [ -n "${ANDROID_HOME:-}" ]; then
  info "Android SDK: $ANDROID_HOME"
else
  warn "ANDROID_HOME not set – required for 'flet build android'"
fi

# ── Flet version ─────────────────────────────────────────────────────────
FLET_VER=$(python -c "import flet; print(flet.__version__)" 2>/dev/null || echo "not installed")
info "Flet version: $FLET_VER"

echo ""
info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
info "Setup complete. Commands:"
info ""
info "  Run on desktop (dev):  cd src && python main.py"
info "  Build Android APK:     cd src && flet build android"
info "  Install on device:     adb install build/apk/outputs/apk/debug/*.apk"
info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
