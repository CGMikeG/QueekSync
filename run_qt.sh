#!/usr/bin/env bash
# QueekSync launcher for Linux / WSL (PyQt6 UI)
set -e

LOG="$HOME/.local/share/QueekSync/queeksync.log"
mkdir -p "$(dirname "$LOG")"

_die() {
    echo ""
    echo "══════════════════════════════════════════"
    echo "  QueekSync failed to start. Error log:"
    echo "  $LOG"
    echo "══════════════════════════════════════════"
    echo ""
    tail -30 "$LOG" 2>/dev/null || true
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
    echo "[QueekSync] Creating virtual environment..."
    python3 -m venv "$VENV"
fi

# ── Ensure PyQt6 is installed ───────────────────────────────────────────────
if ! "$VENV/bin/python" -c "import PyQt6" >/dev/null 2>&1; then
    echo "[QueekSync] Installing PyQt6..."
    "$VENV/bin/python" -m pip install --quiet PyQt6
fi

# ── Launch ───────────────────────────────────────────────────────────────────
echo "[QueekSync] Starting (PyQt6 UI)... (log: $LOG)"
"$VENV/bin/python" main_qt.py "$@" 2>&1 | tee "$LOG"
