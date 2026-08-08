"""
Settings panel – application-wide preferences (PyQt6).
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import TYPE_CHECKING, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from ui_qt import theme as T
from ui_qt.widgets import (
    DimLabel,
    GlassCard,
    GhostButton,
    HSeparator,
    MutedLabel,
    PrimaryButton,
    ScrollArea,
    SectionLabel,
    attach_tooltip,
)

if TYPE_CHECKING:
    from ui_qt.app import QueekSyncApp


class SettingsPanel(QWidget):
    def __init__(self, app: "QueekSyncApp", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._app = app

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._scroll = ScrollArea(self)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        host = QWidget()
        layout = QVBoxLayout(host)
        layout.setContentsMargins(T.PAD_LG, T.PAD_MD, T.PAD_LG, T.PAD_MD)
        layout.setSpacing(T.PAD_SM)
        self._scroll.setWidget(host)

        root.addWidget(self._scroll)

        cfg = self._app.config_mgr.config

        # ── Appearance ─────────────────────────────────────────────────
        layout.addWidget(SectionLabel("Appearance"))
        app_card = GlassCard(host)
        app_grid = QGridLayout(app_card)
        app_grid.setContentsMargins(T.PAD_MD, T.PAD_MD, T.PAD_MD, T.PAD_MD)
        app_grid.setHorizontalSpacing(T.PAD_MD)
        app_grid.setVerticalSpacing(T.PAD_SM)

        theme_lbl = MutedLabel("Theme")
        app_grid.addWidget(theme_lbl, 0, 0, Qt.AlignmentFlag.AlignVCenter)

        self._theme_combo = QComboBox()
        self._theme_combo.addItems(["dark", "light", "system"])
        idx = self._theme_combo.findText(cfg.theme)
        self._theme_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._theme_combo.currentTextChanged.connect(self._apply_theme)
        app_grid.addWidget(self._theme_combo, 0, 1)
        attach_tooltip(
            self._theme_combo,
            "Choose the app appearance mode. Example: dark for low-light setups, "
            "light for bright rooms, or system to follow your OS theme.",
        )
        layout.addWidget(app_card)

        # ── Behaviour ──────────────────────────────────────────────────
        layout.addWidget(SectionLabel("Behaviour"))
        beh_card = GlassCard(host)
        beh_grid = QGridLayout(beh_card)
        beh_grid.setContentsMargins(T.PAD_MD, T.PAD_MD, T.PAD_MD, T.PAD_MD)
        beh_grid.setHorizontalSpacing(T.PAD_MD)
        beh_grid.setVerticalSpacing(T.PAD_SM)

        notif_lbl = MutedLabel("Show Notifications")
        beh_grid.addWidget(notif_lbl, 0, 0)
        self._notif_cb = QCheckBox()
        self._notif_cb.setChecked(cfg.show_notifications)
        beh_grid.addWidget(self._notif_cb, 0, 1)
        attach_tooltip(self._notif_cb, "Enable or disable desktop notifications for sync events.")

        min_lbl = MutedLabel("Start Minimized")
        beh_grid.addWidget(min_lbl, 1, 0)
        self._minimized_cb = QCheckBox()
        self._minimized_cb.setChecked(cfg.start_minimized)
        beh_grid.addWidget(self._minimized_cb, 1, 1)
        attach_tooltip(self._minimized_cb, "Start the application minimized to the system tray on login.")
        layout.addWidget(beh_card)

        # ── Logging ────────────────────────────────────────────────────
        layout.addWidget(SectionLabel("Logging"))
        log_card = GlassCard(host)
        log_grid = QGridLayout(log_card)
        log_grid.setContentsMargins(T.PAD_MD, T.PAD_MD, T.PAD_MD, T.PAD_MD)
        log_grid.setHorizontalSpacing(T.PAD_MD)
        log_grid.setVerticalSpacing(T.PAD_SM)

        level_lbl = MutedLabel("Log Level")
        log_grid.addWidget(level_lbl, 0, 0, Qt.AlignmentFlag.AlignVCenter)
        self._level_combo = QComboBox()
        self._level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        idx = self._level_combo.findText(str(cfg.log_level).upper())
        self._level_combo.setCurrentIndex(idx if idx >= 0 else 1)
        log_grid.addWidget(self._level_combo, 0, 1)
        attach_tooltip(self._level_combo, "Set the verbosity of the application log.")

        open_log_btn = GhostButton("Open Log File", log_card, command=self._open_log_file)
        open_log_btn.setFixedSize(140, 30)
        log_grid.addWidget(open_log_btn, 1, 0)
        layout.addWidget(log_card)

        # ── Storage ────────────────────────────────────────────────────
        layout.addWidget(SectionLabel("Storage"))
        stor_card = GlassCard(host)
        stor_layout = QVBoxLayout(stor_card)
        stor_layout.setContentsMargins(T.PAD_MD, T.PAD_MD, T.PAD_MD, T.PAD_MD)
        stor_layout.setSpacing(T.PAD_SM)

        log_path = self._app.get_log_file_path()
        info = DimLabel(
            f"Profiles directory:\n{self._app.profile_mgr.directory}\n\n"
            + (f"Log file:\n{log_path}" if log_path else "Log file:\n(disabled or unavailable)")
        )
        stor_layout.addWidget(info)

        open_dir_btn = GhostButton("Open in File Manager", stor_card, command=self._open_profiles_dir)
        open_dir_btn.setFixedSize(180, 30)
        stor_layout.addWidget(open_dir_btn)
        layout.addWidget(stor_card)

        # ── About ──────────────────────────────────────────────────────
        layout.addWidget(SectionLabel("About"))
        about_card = GlassCard(host)
        about_layout = QVBoxLayout(about_card)
        about_layout.setContentsMargins(T.PAD_MD, T.PAD_MD, T.PAD_MD, T.PAD_MD)
        about = DimLabel(
            "QueekSync\n"
            "Cross-platform file synchronisation with glass UI.\n\n"
            "Supports local and SFTP (SSH) endpoints.\n"
            "Built with Python · PyQt6 · paramiko · watchdog"
        )
        about_layout.addWidget(about)
        layout.addWidget(about_card)

        # ── Save button ────────────────────────────────────────────────
        save_btn = PrimaryButton("  Save Settings  ", host, command=self._save)
        save_btn.setFixedWidth(170)
        layout.addWidget(save_btn)
        attach_tooltip(save_btn, "Apply and save these global preferences.")

        layout.addStretch()

    # ------------------------------------------------------------------

    def _apply_theme(self, value: str) -> None:
        self._app.set_theme(value)

    def _save(self) -> None:
        cfg = self._app.config_mgr.config
        cfg.theme = self._theme_combo.currentText()
        cfg.show_notifications = self._notif_cb.isChecked()
        cfg.start_minimized = self._minimized_cb.isChecked()
        cfg.log_to_file = True
        cfg.log_level = self._level_combo.currentText()
        self._app.config_mgr.save()
        self._app.refresh_file_logging()
        QMessageBox.information(self, "Settings", "Settings saved successfully.")

    def _open_profiles_dir(self) -> None:
        self._open_path(self._app.profile_mgr.directory)

    def _open_log_file(self) -> None:
        self._open_path(self._app.get_log_file_path())

    @staticmethod
    def _open_path(path: str) -> None:
        if not path:
            return
        try:
            if sys.platform == "win32":
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as exc:
            QMessageBox.critical(None, "Error", str(exc))
