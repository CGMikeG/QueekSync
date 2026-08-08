"""
Monitor panel – live sync progress, per-profile log stream, and history.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional

import customtkinter as ctk

from core.syncer import SyncEvent
from ui import theme as T
from ui.components import GlassCard, LogViewer, Separator

if TYPE_CHECKING:
    from ui.app import QueekSyncApp


class ActiveSyncCard(GlassCard):
    """Shows live progress for one running sync job."""

    def __init__(self, master, profile_id: str, profile_name: str, color: str, app: "QueekSyncApp", **kw) -> None:
        super().__init__(master, **kw)
        self._pid = profile_id
        self._app = app
        self._done = False

        self.grid_columnconfigure(0, weight=1)

        # Header row
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=T.PAD_MD, pady=(T.PAD_SM, 2))

        # Accent dot
        ctk.CTkFrame(hdr, fg_color=color, width=10, height=10, corner_radius=5).pack(
            side="left", padx=(0, T.PAD_SM)
        )

        ctk.CTkLabel(
            hdr,
            text=profile_name,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=T.TEXT,
        ).pack(side="left")

        self._status_lbl = ctk.CTkLabel(
            hdr, text="Running…", font=ctk.CTkFont(size=11), text_color=T.ACCENT,
        )
        self._status_lbl.pack(side="right")

        self._cancel_btn = ctk.CTkButton(
            hdr, text="✕ Cancel", width=80, height=26,
            corner_radius=T.RADIUS_SM, fg_color="transparent",
            hover_color=T.BG_HOVER, text_color=T.TEXT_MUTED,
            border_color=T.BORDER, border_width=1,
            command=self._cancel,
        )
        self._cancel_btn.pack(side="right", padx=T.PAD_SM)

        self._pause_btn = ctk.CTkButton(
            hdr, text="Pause", width=70, height=26,
            corner_radius=T.RADIUS_SM, fg_color="transparent",
            hover_color=T.BG_HOVER, text_color=T.TEXT_MUTED,
            border_color=T.BORDER, border_width=1,
            command=self._toggle_pause,
        )
        self._pause_btn.pack(side="right")

        # Progress bar
        self._progress = ctk.CTkProgressBar(
            self,
            fg_color=T.BG_INPUT,
            progress_color=color,
            corner_radius=4,
            height=6,
            mode="indeterminate",
        )
        self._progress.grid(row=1, column=0, sticky="ew", padx=T.PAD_MD, pady=2)
        self._progress.start()

        # Current file label
        self._file_lbl = ctk.CTkLabel(
            self, text="Scanning…", font=ctk.CTkFont(size=11),
            text_color=T.TEXT_DIM, anchor="w",
        )
        self._file_lbl.grid(row=2, column=0, sticky="ew", padx=T.PAD_MD, pady=(2, T.PAD_SM))

    # ------------------------------------------------------------------

    def update_event(self, event: SyncEvent) -> None:
        detail = (event.message or event.rel_path or "Working…")[:100]

        if event.kind in ("success", "error", "warning"):
            self._done = True
            self._progress.stop()
            self._cancel_btn.configure(state="disabled")
            self._pause_btn.configure(state="disabled")
            if event.kind == "success":
                self._progress.configure(progress_color=T.SUCCESS, mode="determinate")
                self._progress.set(1.0)
                self._status_lbl.configure(text="Completed ✔", text_color=T.SUCCESS)
            elif event.kind == "error":
                self._progress.configure(progress_color=T.ERROR, mode="determinate")
                self._progress.set(1.0)
                self._status_lbl.configure(text="Error ✖", text_color=T.ERROR)
            else:
                self._status_lbl.configure(text="Cancelled", text_color=T.WARNING)
            self._file_lbl.configure(text=detail)
            return

        if event.progress > 0:
            self._progress.stop()
            self._progress.configure(mode="determinate")
            self._progress.set(event.progress)

        engine = self._app.get_engine(self._pid)
        paused = bool(engine and engine.is_paused())
        self._pause_btn.configure(text="Resume" if paused else "Pause")

        status_text = {
            "info": "Working…",
            "compare": "Comparing…",
            "copy": "Copying…",
            "delete": "Deleting…",
            "skip": "Up-to-date",
        }.get(event.kind, "Running…")
        status_color = T.WARNING if event.kind == "delete" else T.ACCENT
        if paused:
            status_text = "Paused"
            status_color = T.WARNING
        if event.progress > 0:
            status_text = f"{status_text} {event.progress*100:.0f}%"
        self._status_lbl.configure(text=status_text, text_color=status_color)
        self._file_lbl.configure(text=detail)

    def _cancel(self) -> None:
        self._app.cancel_sync(self._pid)

    def _toggle_pause(self) -> None:
        self._app.toggle_pause_sync(self._pid)


# ---------------------------------------------------------------------------

class MonitorPanel(ctk.CTkFrame):
    def __init__(self, master, app: "QueekSyncApp", **kw) -> None:
        kw.setdefault("fg_color", "transparent")
        super().__init__(master, **kw)
        self._app = app
        self._active_cards: Dict[str, ActiveSyncCard] = {}
        self._log_entries: List[tuple] = []   # (timestamp, pid, kind, message)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build()

        # Bind mouse wheel to scrollable frames
        self._cards_frame.bind("<MouseWheel>", self._on_mousewheel)
        self._cards_frame.bind("<Button-4>", self._on_mousewheel)
        self._cards_frame.bind("<Button-5>", self._on_mousewheel)
        self._log.bind("<MouseWheel>", self._on_mousewheel)
        self._log.bind("<Button-4>", self._on_mousewheel)
        self._log.bind("<Button-5>", self._on_mousewheel)

    def _on_mousewheel(self, event) -> None:
        """Route mouse wheel events to the appropriate scrollable widget."""
        try:
            # Determine which widget has focus or is under the mouse
            widget = self._get_widget_under_mouse(event)
            if widget:
                # Delegate to the widget's own scroll handling
                if hasattr(widget, '_text_widget'):
                    # It's a LogViewer - let it handle itself
                    widget._on_mousewheel(event)
                elif hasattr(widget, '_parent_canvas'):
                    # It's a CTkScrollableFrame - use canvas directly
                    canvas = widget._parent_canvas
                    delta = 1
                    if hasattr(event, 'delta'):
                        delta = -int(event.delta / 6) if event.delta > 0 else 1
                    else:
                        delta = 1 if event.num == 5 else -1
                    
                    current = canvas.yview()
                    if current != (0.0, 1.0):
                        canvas.yview_scroll(delta, "units")
                return
            
            # Fallback: scroll the cards frame if it exists
            if hasattr(self, '_cards_frame') and self._cards_frame:
                if hasattr(self._cards_frame, '_parent_canvas'):
                    canvas = self._cards_frame._parent_canvas
                    delta = 1
                    if hasattr(event, 'delta'):
                        delta = -int(event.delta / 6) if event.delta > 0 else 1
                    else:
                        delta = 1 if event.num == 5 else -1
                    
                    current = canvas.yview()
                    if current != (0.0, 1.0):
                        canvas.yview_scroll(delta, "units")
        except:
            pass

    def _get_widget_under_mouse(self, event) -> Optional[object]:
        """Get the widget under the mouse cursor."""
        try:
            x, y = event.x_root, event.y_root
            widget = self.winfo_containing(x, y)
            # Walk up to find a scrollable frame or log viewer
            while widget:
                if widget == self._cards_frame or widget == self._log:
                    return widget
                # Check if it's inside one of our scrollable areas
                parent = widget.master
                while parent:
                    if parent == self._cards_frame or parent == self._log:
                        return parent
                    parent = parent.master if hasattr(parent, 'master') else None
                widget = parent
        except:
            pass
        return None

    # ------------------------------------------------------------------

    def _build(self) -> None:
        # Top: active jobs
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="nsew", padx=T.PAD_LG, pady=T.PAD_MD)
        top.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(top, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew")

        ctk.CTkLabel(
            hdr, text="Active Jobs",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=T.TEXT_MUTED,
        ).pack(side="left")

        ctk.CTkButton(
            hdr, text="Clear Log", width=90, height=28,
            corner_radius=T.RADIUS_SM, fg_color="transparent",
            hover_color=T.BG_HOVER, text_color=T.TEXT_DIM,
            border_color=T.BORDER, border_width=1,
            command=self._clear_log,
        ).pack(side="right")

        self._cards_frame = ctk.CTkScrollableFrame(
            top, fg_color="transparent", height=160,
            scrollbar_button_color=T.BORDER,
            scrollbar_button_hover_color=T.BORDER_BRIGHT,
        )
        self._cards_frame.grid(row=1, column=0, sticky="ew", pady=(T.PAD_SM, 0))
        self._cards_frame.grid_columnconfigure(0, weight=1)

        self._no_active_lbl = ctk.CTkLabel(
            self._cards_frame,
            text="No active sync jobs.  Start one from the Dashboard or Profiles.",
            font=ctk.CTkFont(size=12),
            text_color=T.TEXT_DIM,
        )
        self._no_active_lbl.pack(pady=30)

        Separator(self).grid(row=1, column=0, sticky="ew", padx=T.PAD_LG)

        # Bottom: log viewer
        log_frame = ctk.CTkFrame(self, fg_color="transparent")
        log_frame.grid(row=2, column=0, sticky="nsew", padx=T.PAD_LG, pady=T.PAD_SM)
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            log_frame, text="Sync Log",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        self._log = LogViewer(log_frame)
        self._log.grid(row=1, column=0, sticky="nsew", pady=(T.PAD_SM, 0))

        # Replay buffered events (if panel was created after sync started)
        for ts, pid, kind, msg in self._log_entries:
            self._log.append(f"[{ts}] [{pid[:8]}] {msg}", tag=kind)

    # ------------------------------------------------------------------

    def on_sync_event(self, event: SyncEvent) -> None:
        pid = getattr(event, "_profile_id", "unknown")
        profile = self._app.profile_mgr.get(pid)
        pname = profile.name if profile else pid[:8]
        color = profile.color if profile else T.ACCENT

        # If there is already a card for this profile in a terminal state
        # (done/cancelled/error) and a new sync event arrives that is not
        # itself terminal, the old card belongs to a previous run — discard
        # it so a fresh card is created for the new run.
        existing = self._active_cards.get(pid)
        if (
            existing is not None
            and getattr(existing, "_done", False)
            and event.kind not in ("success", "error", "warning")
        ):
            existing.destroy()
            del self._active_cards[pid]

        # Ensure card exists for this profile
        if pid not in self._active_cards:
            if hasattr(self, "_no_active_lbl") and self._no_active_lbl.winfo_exists():
                self._no_active_lbl.pack_forget()
            card = ActiveSyncCard(
                self._cards_frame, pid, pname, color, self._app,
            )
            card.pack(fill="x", pady=(0, T.CARD_GAP // 2))
            self._active_cards[pid] = card

        self._active_cards[pid].update_event(event)

        # Log
        ts = event.timestamp.strftime("%H:%M:%S")
        self._log.append(f"[{ts}]  {pname}  ›  {event.message}", tag=event.kind)

        # Buffer
        self._log_entries.append((ts, pid, event.kind, event.message))
        if len(self._log_entries) > 2000:
            self._log_entries = self._log_entries[-1000:]

        # Remove card after short delay when done (all terminal kinds)
        if event.kind in ("success", "error", "warning"):
            self.after(8000, lambda p=pid: self._remove_card(p))

    def _remove_card(self, profile_id: str) -> None:
        card = self._active_cards.pop(profile_id, None)
        if card and card.winfo_exists():
            card.destroy()
        if not self._active_cards:
            self._no_active_lbl = ctk.CTkLabel(
                self._cards_frame,
                text="No active sync jobs.  Start one from the Dashboard or Profiles.",
                font=ctk.CTkFont(size=12),
                text_color=T.TEXT_DIM,
            )
            self._no_active_lbl.pack(pady=30)

    def _clear_log(self) -> None:
        self._log.clear()
        self._log_entries.clear()
