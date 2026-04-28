#!/usr/bin/env bash
# QSync launcher for Linux / WSL
set -e

LOG="$HOME/.local/share/QSync/qsync.log"
mkdir -p "$(dirname "$LOG")"

_die() {
    echo ""
    echo "══════════════════════════════════════════"
    echo "  QSync failed to start. Error log:"
    echo "  $LOG"
    echo "══════════════════════════════════════════"
    echo ""
    tail -30 "$LOG" 2>/dev/null || true
    # Keep terminal open when launched by double-click
    if [ -t 1 ]; then
        read -rp "Press Enter to close..." _
    fi
    exit 1
}
trap _die ERR

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── WSLg display setup ───────────────────────────────────────────────────────
if grep -qi microsoft /proc/version 2>/dev/null; then
    export DISPLAY="${DISPLAY:-:0}"
    export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
    export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/mnt/wslg/runtime-dir}"
fi

VENV="$SCRIPT_DIR/.venv"

# ── Create venv if it doesn't exist ─────────────────────────────────────────
if [ ! -f "$VENV/bin/python" ]; then
    echo "[QSync] Creating virtual environment..."
    python3 -m venv "$VENV"
    echo "[QSync] Installing dependencies..."
    "$VENV/bin/pip" install --quiet -r requirements.txt
    echo "[QSync] Dependencies installed."
fi

# ── Launch ───────────────────────────────────────────────────────────────────
echo "[QSync] Starting... (log: $LOG)"
"$VENV/bin/python" main.py "$@" 2>&1 | tee "$LOG"
