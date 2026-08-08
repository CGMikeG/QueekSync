"""
Profiles panel – list view with CRUD operations (PyQt6).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui_qt import theme as T
from ui_qt.widgets import (
    DangerButton,
    GlassCard,
    GhostButton,
    HSeparator,
    IconButton,
    MutedLabel,
    PrimaryButton,
    ScrollArea,
    StatusBadge,
    attach_tooltip,
)

if TYPE_CHECKING:
    from ui_qt.app import QueekSyncApp


class ProfileRow(GlassCard):
    """Single row in the profile list."""

    def __init__(self, profile, app: "QueekSyncApp", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._profile = profile
        self._app = app
        self.setFixedHeight(64)
        self.set_hover_border(True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 12, 8)
        layout.setSpacing(10)

        # Accent stripe
        stripe = QFrame(self)
        stripe.setFixedSize(4, 48)
        stripe.setStyleSheet(f"background-color: {profile.color}; border: none; border-radius: 2px;")
        layout.addWidget(stripe)

        # Left: name + description
        left = QVBoxLayout()
        left.setSpacing(2)
        name_lbl = QLabel(profile.name)
        f = QFont()
        f.setPointSize(13)
        f.setBold(True)
        name_lbl.setFont(f)
        left.addWidget(name_lbl)

        desc = profile.description or f"{profile.source.display_label()}  →  {profile.destination.display_label()}"
        if len(desc) > 90:
            desc = desc[:90] + "…"
        desc_lbl = MutedLabel(desc)
        left.addWidget(desc_lbl)
        layout.addLayout(left, 1)

        # Right: schedule + badge + actions
        if profile.schedule.enabled:
            sched = MutedLabel(f"⏱ every {profile.schedule.interval_minutes}m")
            layout.addWidget(sched)

        badge = StatusBadge(profile.last_sync_status)
        layout.addWidget(badge)

        def _mk(text: str, cmd, danger: bool = False) -> IconButton:
            btn = IconButton(text, self, command=cmd)
            if danger:
                btn.setStyleSheet(
                    "QPushButton { background-color: #450a0a; color: #ef4444; "
                    "border: 1px solid #ef4444; border-radius: 6px; padding: 4px 8px; }"
                    "QPushButton:hover { background-color: #7f1d1d; }"
                )
            return btn

        sync_btn = PrimaryButton("▶", self, command=self._sync)
        sync_btn.setFixedSize(34, 30)
        layout.addWidget(sync_btn)
        attach_tooltip(sync_btn, "Run this profile immediately.")

        layout.addWidget(_mk("≋", self._compare))
        layout.addWidget(_mk("✎", self._edit))
        layout.addWidget(_mk("⧉", self._duplicate))
        layout.addWidget(_mk("✕", self._delete, danger=True))

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
            self._app.refresh_panel("profiles")
            self._app.refresh_panel("dashboard")
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
        self._app.refresh_panel("profiles")
        self._app.refresh_panel("dashboard")


# ---------------------------------------------------------------------------

class ProfilesPanel(QWidget):
    def __init__(self, app: "QueekSyncApp", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._app = app

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Toolbar ────────────────────────────────────────────────────
        toolbar = QWidget(self)
        tb = QHBoxLayout(toolbar)
        tb.setContentsMargins(T.PAD_LG, T.PAD_MD, T.PAD_LG, T.PAD_MD)
        tb.setSpacing(T.PAD_SM)

        self._count_lbl = MutedLabel("")
        tb.addWidget(self._count_lbl)
        tb.addStretch()

        export_btn = GhostButton("⬇  Export", toolbar, command=self._export_profiles)
        tb.addWidget(export_btn)
        import_btn = GhostButton("⬆  Import", toolbar, command=self._import_profiles)
        tb.addWidget(import_btn)
        sync_all_btn = GhostButton("⟳  Sync All", toolbar, command=self._sync_all)
        tb.addWidget(sync_all_btn)
        new_btn = PrimaryButton("＋  New Profile", toolbar, command=self._new_profile)
        tb.addWidget(new_btn)
        root.addWidget(toolbar)

        sep = HSeparator(self)
        sep.setContentsMargins(T.PAD_LG, 0, T.PAD_LG, 0)
        root.addWidget(sep)

        # ── Scrollable list ────────────────────────────────────────────
        self._scroll = ScrollArea(self)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._list_host = QWidget()
        self._list_layout = QVBoxLayout(self._list_host)
        self._list_layout.setContentsMargins(T.PAD_LG, T.PAD_SM, T.PAD_LG, T.PAD_SM)
        self._list_layout.setSpacing(8)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._scroll.setWidget(self._list_host)

        root.addWidget(self._scroll, 1)

        self._rebuild()

    # ------------------------------------------------------------------

    def _rebuild(self) -> None:
        # Clear list
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        profiles = self._app.profile_mgr.all()
        self._count_lbl.setText(f"{len(profiles)} profile(s)")

        if not profiles:
            empty = QLabel("No profiles yet.\nUse  ＋ New Profile  to create your first sync.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(f"color: {T.TEXT_DIM}; font-size: 14px; padding: 60px;")
            self._list_layout.addWidget(empty)
            return

        for p in sorted(profiles, key=lambda x: x.name):
            self._list_layout.addWidget(ProfileRow(p, self._app))

    def refresh(self) -> None:
        self._rebuild()

    # ------------------------------------------------------------------

    def _new_profile(self) -> None:
        from core.profile import Profile
        from ui_qt.profile_editor import ProfileEditorDialog
        dlg = ProfileEditorDialog(self._app, profile=Profile(), on_save=self._app.save_profile)
        dlg.exec()

    @staticmethod
    def _endpoint_kind(endpoint) -> str:
        return "Remote" if endpoint.type == "sftp" else "Local"

    def _sync_direction_label(self, profile) -> str:
        src_kind = self._endpoint_kind(profile.source)
        dst_kind = self._endpoint_kind(profile.destination)
        if profile.options.mode == "two_way":
            return f"{src_kind} <-> {dst_kind}"
        return f"{src_kind} -> {dst_kind}"

    def _sync_all(self) -> None:
        profiles_to_sync = [
            p for p in self._app.profile_mgr.all()
            if p.enabled and not self._app.is_syncing(p.id)
        ]
        if not profiles_to_sync:
            QMessageBox.information(self, "Sync All", "There are no eligible profiles to sync right now.")
            return

        lines = [
            f"- {p.name}: {self._sync_direction_label(p)}"
            for p in sorted(profiles_to_sync, key=lambda p: p.name.lower())
        ]
        prompt = "The following profiles will be synced:\n\n" + "\n".join(lines) + "\n\nContinue with Sync All?"
        if QMessageBox.question(
            self, "Confirm Sync All", prompt,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return
        for p in profiles_to_sync:
            self._app.start_sync(p.id)

    def _export_profiles(self) -> None:
        profiles = self._app.profile_mgr.all()
        if not profiles:
            QMessageBox.information(self, "Export Profiles", "There are no profiles to export.")
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export profiles to…", "queeksync_profiles.json", "JSON files (*.json);;All files (*)"
        )
        if not filepath:
            return
        try:
            count = self._app.profile_mgr.export_profiles(filepath)
            QMessageBox.information(self, "Export Successful", f"Exported {count} profile(s) to:\n{filepath}")
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", str(exc))

    def _import_profiles(self) -> None:
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Import profiles from…", "", "JSON files (*.json);;All files (*)"
        )
        if not filepath:
            return

        overwrite = QMessageBox.question(
            self,
            "Import Profiles",
            "Overwrite existing profiles that share the same ID?\n\n"
            "• Yes – replace duplicates with the imported version.\n"
            "• No  – keep existing profiles and skip duplicates.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        ) == QMessageBox.StandardButton.Yes

        try:
            imported, skipped = self._app.profile_mgr.import_profiles(filepath, overwrite=overwrite)
        except Exception as exc:
            QMessageBox.critical(self, "Import Failed", str(exc))
            return

        self._app.refresh_panel("profiles")
        self._app.refresh_panel("dashboard")
        QMessageBox.information(
            self, "Import Complete", f"Imported: {imported} profile(s)\nSkipped:  {skipped} profile(s)"
        )
