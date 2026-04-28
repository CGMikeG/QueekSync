"""
Design tokens – colours, fonts, radii used across the entire UI.
All values target customtkinter's dark glass aesthetic.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------

BG_ROOT       = "#080c14"   # window / outermost background
BG_SIDEBAR    = "#0d1421"   # sidebar background
BG_PANEL      = "#111827"   # content area panels
BG_CARD       = "#1a2035"   # cards / inner containers
BG_INPUT      = "#0f1623"   # text-entry / combobox background
BG_HOVER      = "#1f2d4a"   # hover highlight

BORDER        = "#1e2d45"   # subtle border
BORDER_BRIGHT = "#2a4070"   # focused / active border

ACCENT        = "#3b82f6"   # primary accent – blue
ACCENT_HOVER  = "#2563eb"
ACCENT_DIM    = "#1d4ed8"
ACCENT2       = "#8b5cf6"   # secondary – purple
ACCENT3       = "#14b8a6"   # tertiary  – teal

TEXT          = "#e2e8f0"   # primary text
TEXT_MUTED    = "#94a3b8"   # secondary / hint text
TEXT_DIM      = "#475569"   # disabled text

SUCCESS       = "#22c55e"
WARNING       = "#f59e0b"
ERROR         = "#ef4444"
INFO          = "#38bdf8"

# ---------------------------------------------------------------------------
# Semantic groups for customtkinter fg_color / border_color
# ---------------------------------------------------------------------------

FRAME_SIDEBAR  = (BG_SIDEBAR,  BG_SIDEBAR)
FRAME_PANEL    = (BG_PANEL,    BG_PANEL)
FRAME_CARD     = (BG_CARD,     BG_CARD)

BUTTON_PRIMARY = (ACCENT,      ACCENT)
BUTTON_PRIMARY_HOVER = (ACCENT_HOVER, ACCENT_HOVER)

BUTTON_GHOST   = ("transparent", "transparent")

TEXT_PRIMARY   = (TEXT,        TEXT)
TEXT_SECONDARY = (TEXT_MUTED,  TEXT_MUTED)

# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------

RADIUS_SM  = 6
RADIUS_MD  = 10
RADIUS_LG  = 14
RADIUS_XL  = 18

PAD_XS = 4
PAD_SM = 8
PAD_MD = 14
PAD_LG = 20
PAD_XL = 28

SIDEBAR_W  = 220
HEADER_H   = 52
CARD_GAP   = 14

# ---------------------------------------------------------------------------
# Status colour map
# ---------------------------------------------------------------------------

STATUS_COLORS = {
    "never":     TEXT_DIM,
    "success":   SUCCESS,
    "error":     ERROR,
    "running":   ACCENT,
    "cancelled": WARNING,
}

STATUS_LABELS = {
    "never":     "Never synced",
    "success":   "Last sync OK",
    "error":     "Sync error",
    "running":   "Running…",
    "cancelled": "Cancelled",
}

# ---------------------------------------------------------------------------
# Log level colours
# ---------------------------------------------------------------------------

LOG_COLORS = {
    "info":    TEXT_MUTED,
    "copy":    INFO,
    "delete":  WARNING,
    "skip":    TEXT_DIM,
    "error":   ERROR,
    "success": SUCCESS,
    "warning": WARNING,
}
