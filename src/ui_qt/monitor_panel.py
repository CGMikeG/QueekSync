"""
Monitor panel – live sync progress, per-profile log stream (PyQt6).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.syncer import SyncEvent
from ui_qt import theme as T
from ui_qt.widgets import GhostButton, HSeparator, LogViewer, MutedLabel, ProgressBar, ScrollArea, attach_tooltip

if TYPE_CHECKING:
    from ui_qt.app import QueekSyncApp


class ActiveSyncCard(QFrame):
    """Shows live progress for one running sync job."""

    def __init__(
        self,
        profile_id: str,
        profile_name: str,
        color: str,
        app: "QueekSyncApp",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("GlassCard")
        self._pid = profile_id
        self._app = app
        self._done = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(T.PAD_MD, T.PAD_SM, T.PAD_MD, T.PAD_SM)
        layout.setSpacing(4)

        # ── Header row ─────────────────────────────────────────────────
        hdr = QHBoxLayout()
        dot = QFrame(self)
        dot.setFixedSize(10, 10)
        dot.setStyleSheet(f"background-color: {color}; border-radius: 5px; border: none;")
        hdr.addWidget(dot)

        name_lbl = QLabel(profile_name)
        f = QFont()
        f.setPointSize(13)
        f.setBold(True)
        name_lbl.setFont(f)
        hdr.addWidget(name_lbl)
        hdr.addStretch()

        self._pause_btn = GhostButton("Pause", self, command=self._toggle_pause)
        self._pause_btn.setFixedSize(70, 26)
        hdr.addWidget(self._pause_btn)

        self._cancel_btn = GhostButton("✕ Cancel", self, command=self._cancel)
        self._cancel_btn.setFixedSize(80, 26)
        hdr.addWidget(self._cancel_btn)

        self._status_lbl = QLabel("Running…")
        self._status_lbl.setStyleSheet(f"color: {T.ACCENT}; font-size: 11px;")
        hdr.addWidget(self._status_lbl)
        layout.addLayout(hdr)

        # ── Progress bar ───────────────────────────────────────────────
        self._progress = ProgressBar(color=color, parent=self)
        layout.addWidget(self._progress)
        self._progress.start_indeterminate()

        # ── Current file label ─────────────────────────────────────────
        self._file_lbl = MutedLabel("Scanning…")
        layout.addWidget(self._file_lbl)

    # ------------------------------------------------------------------

    def update_event(self, event: SyncEvent) -> None:
        detail = (event.message or event.rel_path or "Working…")[:120]

        if event.kind in ("success", "error", "warning"):
            self._done = True
            self._progress.stop_indeterminate()
            self._cancel_btn.setEnabled(False)
            self._pause_btn.setEnabled(False)
            if event.kind == "success":
                self._progress.set_determinate(1.0)
                self._progress.setStyleSheet(
                    f"QProgressBar {{ background-color: {T.BG_INPUT}; border: none; border-radius: 3px; }}"
                    f"QProgressBar::chunk {{ background-color: {T.SUCCESS}; border-radius: 3px; }}"
                )
                self._status_lbl.setText("Completed ✔")
                self._status_lbl.setStyleSheet(f"color: {T.SUCCESS}; font-size: 11px;")
            elif event.kind == "error":
                self._progress.set_determinate(1.0)
                self._progress.setStyleSheet(
                    f"QProgressBar {{ background-color: {T.BG_INPUT}; border: none; border-radius: 3px; }}"
                    f"QProgressBar::chunk {{ background-color: {T.ERROR}; border-radius: 3px; }}"
                )
                self._status_lbl.setText("Error ✖")
                self._status_lbl.setStyleSheet(f"color: {T.ERROR}; font-size: 11px;")
            else:
                self._status_lbl.setText("Cancelled")
                self._status_lbl.setStyleSheet(f"color: {T.WARNING}; font-size: 11px;")
            self._file_lbl.setText(detail)
            return

        if event.progress > 0:
            self._progress.stop_indeterminate()
            self._progress.set_determinate(event.progress)

        engine = self._app.get_engine(self._pid)
        paused = bool(engine and engine.is_paused())
        self._pause_btn.setText("Resume" if paused else "Pause")

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
        self._status_lbl.setText(status_text)
        self._status_lbl.setStyleSheet(f"color: {status_color}; font-size: 11px;")
        self._file_lbl.setText(detail)

    def _cancel(self) -> None:
        self._app.cancel_sync(self._pid)

    def _toggle_pause(self) -> None:
        self._app.toggle_pause_sync(self._pid)


# ---------------------------------------------------------------------------

class MonitorPanel(QWidget):
    def __init__(self, app: "QueekSyncApp", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._app = app
        self._active_cards: Dict[str, ActiveSyncCard] = {}
        self._log_entries: List[tuple] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Active jobs (fixed-height scroll area) ─────────────────────
        top = QWidget(self)
        top_layout = QVBoxLayout(top)
        top_layout.setContentsMargins(T.PAD_LG, T.PAD_MD, T.PAD_LG, T.PAD_SM)
        top_layout.setSpacing(T.PAD_SM)

        hdr = QHBoxLayout()
        title = QLabel("Active Jobs")
        f = QFont()
        f.setPointSize(13)
        f.setBold(True)
        title.setFont(f)
        title.setStyleSheet(f"color: {T.TEXT_MUTED};")
        hdr.addWidget(title)
        hdr.addStretch()
        clear_btn = GhostButton("Clear Log", self, command=self._clear_log)
        clear_btn.setFixedSize(90, 28)
        hdr.addWidget(clear_btn)
        top_layout.addLayout(hdr)

        self._cards_scroll = ScrollArea(top)
        self._cards_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._cards_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._cards_scroll.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._cards_scroll.setFixedHeight(170)

        self._cards_host = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_host)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(8)
        self._cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._cards_scroll.setWidget(self._cards_host)
        top_layout.addWidget(self._cards_scroll)

        self._no_active_lbl = MutedLabel("No active sync jobs.  Start one from the Dashboard or Profiles.")
        self._no_active_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._no_active_lbl.setStyleSheet(f"color: {T.TEXT_DIM}; padding: 20px;")
        self._cards_layout.addWidget(self._no_active_lbl)

        root.addWidget(top)

        sep = HSeparator(self)
        sep.setContentsMargins(T.PAD_LG, 0, T.PAD_LG, 0)
        root.addWidget(sep)

        # ── Log viewer ─────────────────────────────────────────────────
        log_frame = QWidget(self)
        log_layout = QVBoxLayout(log_frame)
        log_layout.setContentsMargins(T.PAD_LG, T.PAD_SM, T.PAD_LG, T.PAD_SM)
        log_layout.setSpacing(T.PAD_SM)

        log_title = QLabel("Sync Log")
        log_title.setFont(f)
        log_title.setStyleSheet(f"color: {T.TEXT_MUTED};")
        log_layout.addWidget(log_title)

        self._log = LogViewer(log_frame)
        log_layout.addWidget(self._log, 1)
        root.addWidget(log_frame, 1)

        # Replay buffered events (if panel created after sync started)
        for ts, pid, kind, msg in self._log_entries:
            self._log.append(f"[{ts}] [{pid[:8]}] {msg}", tag=kind)

    # ------------------------------------------------------------------

    def on_sync_event(self, event: SyncEvent) -> None:
        pid = getattr(event, "_profile_id", "unknown")
        profile = self._app.profile_mgr.get(pid)
        pname = profile.name if profile else pid[:8]
        color = profile.color if profile else T.ACCENT

        existing = self._active_cards.get(pid)
        if (
            existing is not None
            and getattr(existing, "_done", False)
            and event.kind not in ("success", "error", "warning")
        ):
            existing.deleteLater()
            del self._active_cards[pid]

        if pid not in self._active_cards:
            if self._no_active_lbl is not None:
                self._no_active_lbl.hide()
            card = ActiveSyncCard(pid, pname, color, self._app)
            self._cards_layout.addWidget(card)
            self._active_cards[pid] = card

        self._active_cards[pid].update_event(event)

        # Log
        ts = event.timestamp.strftime("%H:%M:%S")
        self._log.append(f"[{ts}]  {pname}  ›  {event.message}", tag=event.kind)

        # Buffer
        self._log_entries.append((ts, pid, event.kind, event.message))
        if len(self._log_entries) > 2000:
            self._log_entries = self._log_entries[-1000:]

        # Remove card after short delay when done
        if event.kind in ("success", "error", "warning"):
            QTimer.singleShot(8000, lambda p=pid: self._remove_card(p))

    def _remove_card(self, profile_id: str) -> None:
        card = self._active_cards.pop(profile_id, None)
        if card is not None:
            card.deleteLater()
        if not self._active_cards:
            if self._no_active_lbl is not None:
                self._no_active_lbl.show()

    def _clear_log(self) -> None:
        self._log.clear()
        self._log_entries.clear()
