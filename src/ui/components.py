"""
Reusable UI components built on top of customtkinter.
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable, List, Optional, Tuple

import customtkinter as ctk

from ui import theme as T


# ---------------------------------------------------------------------------
# Glass card frame
# ---------------------------------------------------------------------------

class GlassCard(ctk.CTkFrame):
    """A rounded, bordered card with the glass-dark look."""

    def __init__(self, master, **kw) -> None:
        kw.setdefault("fg_color", T.BG_CARD)
        kw.setdefault("border_color", T.BORDER)
        kw.setdefault("border_width", 1)
        kw.setdefault("corner_radius", T.RADIUS_LG)
        super().__init__(master, **kw)


# ---------------------------------------------------------------------------
# Section header label
# ---------------------------------------------------------------------------

class SectionLabel(ctk.CTkLabel):
    def __init__(self, master, text: str, **kw) -> None:
        kw.setdefault("font", ctk.CTkFont(size=11, weight="bold"))
        kw.setdefault("text_color", T.TEXT_DIM)
        kw.setdefault("text", text.upper())
        super().__init__(master, **kw)


# ---------------------------------------------------------------------------
# Status badge
# ---------------------------------------------------------------------------

class StatusBadge(ctk.CTkLabel):
    """Pill-shaped coloured label showing sync status."""

    _STATUS_COLOR = {
        "never":     ("#3d4450", "#6b7280"),
        "success":   ("#14532d", T.SUCCESS),
        "error":     ("#450a0a", T.ERROR),
        "running":   ("#1e3a5f", T.ACCENT),
        "cancelled": ("#451a03", T.WARNING),
    }

    def __init__(self, master, status: str = "never", **kw) -> None:
        bg, fg = self._STATUS_COLOR.get(status, self._STATUS_COLOR["never"])
        kw.setdefault("corner_radius", 20)
        kw.setdefault("font", ctk.CTkFont(size=11, weight="bold"))
        from ui.theme import STATUS_LABELS
        label = STATUS_LABELS.get(status, status.capitalize())
        super().__init__(
            master,
            text=f"  {label}  ",
            fg_color=bg,
            text_color=fg,
            **kw,
        )
        self._status = status

    def set_status(self, status: str) -> None:
        if status == self._status:
            return
        bg, fg = self._STATUS_COLOR.get(status, self._STATUS_COLOR["never"])
        from ui.theme import STATUS_LABELS
        label = STATUS_LABELS.get(status, status.capitalize())
        self.configure(text=f"  {label}  ", fg_color=bg, text_color=fg)
        self._status = status


# ---------------------------------------------------------------------------
# Glowing separator
# ---------------------------------------------------------------------------

class Separator(ctk.CTkFrame):
    def __init__(self, master, orientation: str = "horizontal", **kw) -> None:
        if orientation == "horizontal":
            kw.setdefault("height", 1)
            kw.setdefault("fg_color", T.BORDER)
        else:
            kw.setdefault("width", 1)
            kw.setdefault("fg_color", T.BORDER)
        kw.setdefault("corner_radius", 0)
        super().__init__(master, **kw)


# ---------------------------------------------------------------------------
# Icon button (text-only, ghost style)
# ---------------------------------------------------------------------------

class IconButton(ctk.CTkButton):
    """Ghost-style button – used for sidebar nav and card actions."""

    def __init__(self, master, text: str, command: Callable = None, active: bool = False, **kw) -> None:
        kw.setdefault("corner_radius", T.RADIUS_MD)
        kw.setdefault("font", ctk.CTkFont(size=13))
        kw.setdefault("anchor", "w")
        kw.setdefault("height", 40)
        if active:
            kw.setdefault("fg_color", T.BG_HOVER)
            kw.setdefault("hover_color", T.BG_HOVER)
            kw.setdefault("text_color", T.TEXT)
            kw.setdefault("border_color", T.ACCENT)
            kw.setdefault("border_width", 1)
        else:
            kw.setdefault("fg_color", "transparent")
            kw.setdefault("hover_color", T.BG_HOVER)
            kw.setdefault("text_color", T.TEXT_MUTED)
            kw.setdefault("border_width", 0)
        super().__init__(master, text=text, command=command, **kw)


# ---------------------------------------------------------------------------
# Primary action button
# ---------------------------------------------------------------------------

class PrimaryButton(ctk.CTkButton):
    def __init__(self, master, text: str, command: Callable = None, **kw) -> None:
        kw.setdefault("corner_radius", T.RADIUS_MD)
        kw.setdefault("font", ctk.CTkFont(size=13, weight="bold"))
        kw.setdefault("fg_color", T.ACCENT)
        kw.setdefault("hover_color", T.ACCENT_HOVER)
        kw.setdefault("text_color", "#ffffff")
        kw.setdefault("height", 36)
        super().__init__(master, text=text, command=command, **kw)


# ---------------------------------------------------------------------------
# Danger button
# ---------------------------------------------------------------------------

class DangerButton(ctk.CTkButton):
    def __init__(self, master, text: str, command: Callable = None, **kw) -> None:
        kw.setdefault("corner_radius", T.RADIUS_MD)
        kw.setdefault("font", ctk.CTkFont(size=13))
        kw.setdefault("fg_color", "#450a0a")
        kw.setdefault("hover_color", "#7f1d1d")
        kw.setdefault("text_color", T.ERROR)
        kw.setdefault("border_color", T.ERROR)
        kw.setdefault("border_width", 1)
        kw.setdefault("height", 36)
        super().__init__(master, text=text, command=command, **kw)


# ---------------------------------------------------------------------------
# Labelled entry row
# ---------------------------------------------------------------------------

class LabelledEntry(ctk.CTkFrame):
    """A label + CTkEntry stacked vertically."""

    def __init__(self, master, label: str, placeholder: str = "", show: str = "", **kw) -> None:
        kw.setdefault("fg_color", "transparent")
        super().__init__(master, **kw)

        ctk.CTkLabel(
            self,
            text=label,
            font=ctk.CTkFont(size=12),
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=2, pady=(0, 3))

        self.entry = ctk.CTkEntry(
            self,
            placeholder_text=placeholder,
            fg_color=T.BG_INPUT,
            border_color=T.BORDER,
            text_color=T.TEXT,
            placeholder_text_color=T.TEXT_DIM,
            corner_radius=T.RADIUS_SM,
            show=show,
        )
        self.entry.pack(fill="x")

    def get(self) -> str:
        return self.entry.get()

    def set(self, value: str) -> None:
        self.entry.delete(0, "end")
        self.entry.insert(0, value)


# ---------------------------------------------------------------------------
# Log text viewer
# ---------------------------------------------------------------------------

class LogViewer(ctk.CTkTextbox):
    """Scrollable text box for sync log output."""

    MAX_LINES = 2000

    def __init__(self, master, **kw) -> None:
        kw.setdefault("fg_color", T.BG_ROOT)
        kw.setdefault("text_color", T.TEXT_MUTED)
        kw.setdefault("font", ctk.CTkFont(family="Courier New", size=12))
        kw.setdefault("corner_radius", T.RADIUS_MD)
        kw.setdefault("border_color", T.BORDER)
        kw.setdefault("border_width", 1)
        kw.setdefault("wrap", "word")
        super().__init__(master, **kw)
        self.configure(state="disabled")

        # Tag colours
        self._text_widget().tag_configure("info",    foreground=T.TEXT_MUTED)
        self._text_widget().tag_configure("copy",    foreground=T.INFO)
        self._text_widget().tag_configure("delete",  foreground=T.WARNING)
        self._text_widget().tag_configure("skip",    foreground=T.TEXT_DIM)
        self._text_widget().tag_configure("error",   foreground=T.ERROR)
        self._text_widget().tag_configure("success", foreground=T.SUCCESS)
        self._text_widget().tag_configure("warning", foreground=T.WARNING)
        self._text_widget().tag_configure("ts",      foreground=T.TEXT_DIM)

    def _text_widget(self) -> tk.Text:
        # customtkinter wraps an internal tk.Text
        return self._textbox  # type: ignore[attr-defined]

    def append(self, text: str, tag: str = "info") -> None:
        tw = self._text_widget()
        self.configure(state="normal")
        # Prune if too long
        lines = int(tw.index("end-1c").split(".")[0])
        if lines > self.MAX_LINES:
            tw.delete("1.0", f"{lines - self.MAX_LINES}.0")
        tw.insert("end", text + "\n", tag)
        self.configure(state="disabled")
        self.see("end")

    def clear(self) -> None:
        self.configure(state="normal")
        self.delete("1.0", "end")
        self.configure(state="disabled")


# ---------------------------------------------------------------------------
# Stat tile (number + label)
# ---------------------------------------------------------------------------

class StatTile(GlassCard):
    def __init__(self, master, label: str, value: str = "0", color: str = T.ACCENT, **kw) -> None:
        kw.setdefault("width", 160)
        kw.setdefault("height", 80)
        super().__init__(master, **kw)
        self.grid_propagate(False)

        ctk.CTkLabel(
            self,
            text=value,
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=color,
        ).place(relx=0.5, rely=0.38, anchor="center")

        ctk.CTkLabel(
            self,
            text=label,
            font=ctk.CTkFont(size=11),
            text_color=T.TEXT_MUTED,
        ).place(relx=0.5, rely=0.75, anchor="center")

        self._val_label = self.winfo_children()[0]  # type: ignore[index]

    def set_value(self, value: str) -> None:
        self._val_label.configure(text=value)


# ---------------------------------------------------------------------------
# Colour picker (palette swatch row)
# ---------------------------------------------------------------------------

class ColourPicker(ctk.CTkFrame):
    """Row of colour swatches; calls *on_select(colour)* when clicked."""

    COLOURS = [
        "#3b82f6", "#8b5cf6", "#14b8a6", "#22c55e",
        "#f97316", "#ef4444", "#ec4899", "#eab308",
    ]

    def __init__(self, master, on_select: Callable[[str], None], selected: str = "#3b82f6", **kw) -> None:
        kw.setdefault("fg_color", "transparent")
        super().__init__(master, **kw)
        self._on_select = on_select
        self._selected = selected
        self._buttons: List[ctk.CTkButton] = []
        for colour in self.COLOURS:
            btn = ctk.CTkButton(
                self,
                text="",
                width=28,
                height=28,
                corner_radius=14,
                fg_color=colour,
                hover_color=colour,
                border_width=3 if colour == selected else 0,
                border_color="#ffffff",
                command=lambda c=colour: self._pick(c),
            )
            btn.pack(side="left", padx=3)
            self._buttons.append(btn)

    def _pick(self, colour: str) -> None:
        self._selected = colour
        for btn in self._buttons:
            btn.configure(border_width=3 if btn.cget("fg_color") == colour else 0)
        self._on_select(colour)

    def get(self) -> str:
        return self._selected

    def set(self, colour: str) -> None:
        self._pick(colour)
