"""
Dashboard panel – overview of all profiles with quick-sync cards (PyQt6).
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui_qt import theme as T
from ui_qt.widgets import (
    DimLabel,
    GlassCard,
    GhostButton,
    HSeparator,
    IconButton,
    MutedLabel,
    PrimaryButton,
    ScrollArea,
    StatTile,
    StatusBadge,
    attach_tooltip,
)

if TYPE_CHECKING:
    from ui_qt.app import QueekSyncApp

_MODE_MAP = {"one_way": "→ One-way", "mirror": "↔ Mirror", "two_way": "⇄ Two-way"}


class ProfileCard(GlassCard):
    """Card widget showing a single profile's summary."""

    def __init__(self, profile, app: "QueekSyncApp", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._profile = profile
        self._app = app
        self.set_hover_border(True)
        self.setMinimumWidth(280)
        self.setMaximumWidth(460)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(6)

        # ── Colour accent bar (left edge) ──────────────────────────────
        accent = QFrame(self)
        accent.setFixedWidth(4)
        accent.setStyleSheet(f"background-color: {profile.color}; border: none;")
        accent.setParent(self)

        # ── Name + status row ──────────────────────────────────────────
        top = QHBoxLayout()
        name_lbl = QLabel(profile.name)
        f = QFont()
        f.setPointSize(13)
        f.setBold(True)
        name_lbl.setFont(f)
        top.addWidget(name_lbl, 1)
        badge = StatusBadge(profile.last_sync_status)
        top.addWidget(badge, 0, Qt.AlignmentFlag.AlignRight)
        layout.addLayout(top)

        # ── Paths ──────────────────────────────────────────────────────
        src_label = profile.source.display_label() or "(source not set)"
        dst_label = profile.destination.display_label() or "(destination not set)"
        src_lbl = MutedLabel(f"▲  {src_label}")
        src_lbl.setWordWrap(True)
        dst_lbl = MutedLabel(f"▼  {dst_label}")
        dst_lbl.setWordWrap(True)
        layout.addWidget(src_lbl)
        layout.addWidget(dst_lbl)

        # ── Meta (last sync + mode) ────────────────────────────────────
        last_sync_txt = "Never"
        if profile.last_sync:
            try:
                dt = datetime.fromisoformat(profile.last_sync)
                last_sync_txt = dt.strftime("%Y-%m-%d  %H:%M")
            except Exception:
                last_sync_txt = profile.last_sync
        meta_lbl = DimLabel(f"Last sync:  {last_sync_txt}")
        layout.addWidget(meta_lbl)

        mode_lbl = QLabel(_MODE_MAP.get(profile.options.mode, profile.options.mode))
        mode_lbl.setStyleSheet(f"color: {T.ACCENT}; font-size: 12px;")
        layout.addWidget(mode_lbl)

        layout.addSpacing(4)

        # ── Buttons ────────────────────────────────────────────────────
        sync_btn = PrimaryButton("▶  Sync Now", self, command=self._sync)
        sync_btn.setFixedHeight(30)
        layout.addWidget(sync_btn)
        attach_tooltip(
            sync_btn,
            "Start this profile immediately. Example: use this after dropping new files "
            "into the source folder and wanting the destination updated now.",
        )

        actions = QHBoxLayout()
        actions.setSpacing(6)
        compare_btn = GhostButton("≋  Compare", self, command=self._compare)
        compare_btn.setFixedHeight(28)
        actions.addWidget(compare_btn)
        attach_tooltip(
            compare_btn,
            "Compare source vs destination and report which side looks more up-to-date.",
        )

        edit_btn = IconButton("✎", self, command=self._edit)
        dup_btn = IconButton("⧉", self, command=self._duplicate)
        del_btn = IconButton("✕", self, command=self._delete)
        del_btn.setStyleSheet(
            "QPushButton { background-color: #450a0a; color: #ef4444; border: 1px solid #ef4444; "
            "border-radius: 6px; padding: 4px 8px; }"
            "QPushButton:hover { background-color: #7f1d1d; }"
        )
        actions.addWidget(compare_btn)
        actions.addWidget(edit_btn)
        actions.addWidget(dup_btn)
        actions.addWidget(del_btn)
        actions.addStretch()
        layout.addLayout(actions)

        attach_tooltip(edit_btn, "Open this profile in the editor.")
        attach_tooltip(dup_btn, "Create a copy of this profile.")
        attach_tooltip(del_btn, "Delete this profile permanently.")

    # ------------------------------------------------------------------

    def _sync(self) -> None:
        self._app.start_sync(self._profile.id)

    def _compare(self) -> None:
        self._app.start_compare(self._profile.id)

    def _edit(self) -> None:
        from ui_qt.profile_editor import ProfileEditorDialog
        dlg = ProfileEditorDialog(self._app, profile=self._profile, on_save=self._app.save_profile)
        dlg.exec()

    def _duplicate(self) -> None:
        try:
            self._app.profile_mgr.duplicate_profile(self._profile.id)
            self._app.refresh_panel("dashboard")
            self._app.refresh_panel("profiles")
        except ValueError as exc:
            QMessageBox.critical(self, "Error", str(exc))

    def _delete(self) -> None:
        if QMessageBox.question(
            self,
            "Delete Profile",
            f"Delete profile  '{self._profile.name}'?\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return
        self._app._scheduler.remove_profile(self._profile.id)
        self._app._watcher_mgr.remove(self._profile.id)
        self._app.profile_mgr.delete(self._profile.id)
        self._app.refresh_panel("dashboard")
        self._app.refresh_panel("profiles")


# ---------------------------------------------------------------------------

class DashboardPanel(QWidget):
    """Home screen: stat tiles + responsive grid of profile cards."""

    MIN_CARD_W = 280
    MAX_COLS = 4

    def __init__(self, app: "QueekSyncApp", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._app = app
        self._resize_timer: Optional[QTimer] = None
        self._current_cols = 3

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Stats row ──────────────────────────────────────────────────
        stats = QWidget(self)
        stats_layout = QHBoxLayout(stats)
        stats_layout.setContentsMargins(T.PAD_LG, T.PAD_LG, T.PAD_LG, 0)
        stats_layout.setSpacing(T.CARD_GAP)

        profiles = self._app.profile_mgr.all()
        total = len(profiles)
        running = sum(1 for p in profiles if p.last_sync_status == "running")
        ok = sum(1 for p in profiles if p.last_sync_status == "success")

        self._total_tile = StatTile("Total Profiles", str(total), T.ACCENT)
        self._running_tile = StatTile("Running", str(running), T.WARNING)
        self._ok_tile = StatTile("Last OK", str(ok), T.SUCCESS)
        stats_layout.addWidget(self._total_tile)
        stats_layout.addWidget(self._running_tile)
        stats_layout.addWidget(self._ok_tile)
        stats_layout.addStretch()

        new_btn = PrimaryButton("＋  New Profile", self, command=self._new_profile)
        new_btn.setFixedSize(150, 38)
        stats_layout.addWidget(new_btn)
        attach_tooltip(
            new_btn,
            "Create a new profile from the dashboard. Example: use this when you want "
            "to add another backup job without switching to the Profiles page first.",
        )
        root.addWidget(stats)

        sep = HSeparator(self)
        sep.setContentsMargins(T.PAD_LG, T.PAD_SM, T.PAD_LG, T.PAD_SM)
        root.addWidget(sep)

        # ── Scrollable card grid ───────────────────────────────────────
        self._scroll = ScrollArea(self)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._grid_host = QWidget()
        self._grid = QGridLayout(self._grid_host)
        self._grid.setContentsMargins(T.PAD_LG, T.PAD_SM, T.PAD_LG, T.PAD_SM)
        self._grid.setHorizontalSpacing(T.CARD_GAP)
        self._grid.setVerticalSpacing(T.CARD_GAP)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._grid_host.setLayout(self._grid)
        self._scroll.setWidget(self._grid_host)

        root.addWidget(self._scroll, 1)

        # Empty state
        if not profiles:
            empty = QLabel("No profiles yet.\nClick  ＋ New Profile  to get started.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(f"color: {T.TEXT_DIM}; font-size: 14px; padding: 60px;")
            self._grid.addWidget(empty, 0, 0)
        else:
            self._populate_grid(profiles)

        # Reflow on resize
        self._scroll.viewport().installEventFilter(self)

    # ------------------------------------------------------------------

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        from PyQt6.QtCore import QEvent
        if obj is self._scroll.viewport() and event.type() == QEvent.Type.Resize:
            if self._resize_timer is None:
                self._resize_timer = QTimer(self)
                self._resize_timer.setSingleShot(True)
                self._resize_timer.timeout.connect(self._recalculate_grid)
            self._resize_timer.start(200)
        return super().eventFilter(obj, event)

    # ------------------------------------------------------------------

    def _populate_grid(self, profiles: List) -> None:
        # Clear existing cards (keep everything else)
        while self._grid.count():
            item = self._grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        col_count = self._calculate_columns(self._scroll.viewport().width())
        self._current_cols = col_count

        sorted_profiles = sorted(profiles, key=lambda p: p.name)
        for idx, profile in enumerate(sorted_profiles):
            row = idx // col_count
            col = idx % col_count
            card = ProfileCard(profile, self._app)
            card.setMinimumWidth(self.MIN_CARD_W)
            self._grid.addWidget(card, row, col, Qt.AlignmentFlag.AlignTop)

        # Stretch the last column so cards left-align
        self._grid.setColumnStretch(col_count, 1)

    def _calculate_columns(self, width: int) -> int:
        if width <= 0:
            return 3
        gap = T.CARD_GAP
        per = self.MIN_CARD_W + gap
        cols = max(1, min(self.MAX_COLS, (width - gap) // per))
        return cols

    def _recalculate_grid(self) -> None:
        profiles = self._app.profile_mgr.all()
        if not profiles:
            return
        cols = self._calculate_columns(self._scroll.viewport().width())
        if cols != self._current_cols:
            self._populate_grid(profiles)

    def refresh(self) -> None:
        """Rebuild from current profile data."""
        profiles = self._app.profile_mgr.all()
        self._total_tile.set_value(str(len(profiles)))
        self._running_tile.set_value(str(sum(1 for p in profiles if p.last_sync_status == "running")))
        self._ok_tile.set_value(str(sum(1 for p in profiles if p.last_sync_status == "success")))
        self._populate_grid(profiles)

    def _new_profile(self) -> None:
        from core.profile import Profile
        from ui_qt.profile_editor import ProfileEditorDialog
        dlg = ProfileEditorDialog(self._app, profile=Profile(), on_save=self._app.save_profile)
        dlg.exec()
