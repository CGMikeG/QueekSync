"""
SFTP Remote Folder Browser Dialog (PyQt6).
Lets the user navigate the remote filesystem and pick a directory.
"""

from __future__ import annotations

import os
import threading
from typing import Callable, List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui_qt import theme as T
from ui_qt.widgets import GhostButton, MutedLabel, PrimaryButton


class SFTPBrowserDialog(QDialog):
    """A modal dialog that connects to an SFTP server and lets the user
    browse and select a remote directory."""

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        key_file: str,
        initial_path: str,
        on_select: Callable[[str], None],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Browse Remote Folder")
        self.resize(600, 480)
        self.setMinimumSize(480, 380)

        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._key_file = key_file
        self._on_select = on_select
        self._sftp = None
        self._ssh = None
        self._current_path = initial_path.rstrip("/") or "/"
        self._history: List[str] = []

        self._build()

        # Connect in background
        self._connect()

    # ==================================================================
    # Layout
    # ==================================================================

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(T.PAD_MD, T.PAD_MD, T.PAD_MD, T.PAD_MD)
        root.setSpacing(T.PAD_SM)

        # Status bar
        self._status_lbl = MutedLabel(f"Connecting to {self._host}…")
        root.addWidget(self._status_lbl)

        # Path breadcrumb bar
        path_row = QHBoxLayout()
        self._path_edit = QLineEdit(self._current_path)
        path_row.addWidget(self._path_edit, 1)
        go_btn = GhostButton("Go", self, command=self._go_to_path)
        path_row.addWidget(go_btn)
        root.addLayout(path_row)

        # Directory listing
        self._listing = QListWidget()
        self._listing.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._listing.itemDoubleClicked.connect(self._on_item_double_clicked)
        root.addWidget(self._listing, 1)

        # Buttons
        btn_row = QHBoxLayout()
        up_btn = GhostButton("⬆  Up", self, command=self._go_up)
        btn_row.addWidget(up_btn)
        btn_row.addStretch()
        cancel_btn = GhostButton("Cancel", self, command=self.reject)
        btn_row.addWidget(cancel_btn)
        select_btn = PrimaryButton("Select Folder", self, command=self._choose)
        btn_row.addWidget(select_btn)
        root.addLayout(btn_row)

    # ==================================================================
    # Connection
    # ==================================================================

    def _connect(self) -> None:
        def _try() -> None:
            try:
                import paramiko  # type: ignore[import]
                c = paramiko.SSHClient()
                c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                c.connect(
                    hostname=self._host,
                    port=self._port,
                    username=self._username,
                    password=self._password or None,
                    key_filename=os.path.expanduser(self._key_file) if self._key_file else None,
                    timeout=8,
                )
                self._ssh = c
                self._sftp = c.open_sftp()
                self._status_lbl.setText(f"Connected to {self._host}")
                self._status_lbl.setStyleSheet(f"color: {T.SUCCESS}; font-size: 11px;")
                self._list_dir(self._current_path)
            except Exception as exc:
                self._status_lbl.setText(f"✖ Connection failed: {str(exc)[:70]}")
                self._status_lbl.setStyleSheet(f"color: {T.ERROR}; font-size: 11px;")
                QMessageBox.critical(self, "Connection Failed", str(exc))

        threading.Thread(target=_try, daemon=True).start()

    # ==================================================================
    # Listing
    # ==================================================================

    def _list_dir(self, path: str) -> None:
        def _try() -> None:
            try:
                entries = sorted(self._sftp.listdir(path))
                self._current_path = path
                self._path_edit.setText(path)
                self._listing.clear()
                # Parent entry
                if path != "/":
                    parent_item = QListWidgetItem("⬆  ..")
                    parent_item.setData(Qt.ItemDataRole.UserRole, "..")
                    parent_item.setForeground(Qt.GlobalColor.darkGray)
                    self._listing.addItem(parent_item)
                for name in entries:
                    item = QListWidgetItem(name)
                    item.setData(Qt.ItemDataRole.UserRole, name)
                    self._listing.addItem(item)
                self._status_lbl.setText(f"{len(entries)} item(s) in {path}")
                self._status_lbl.setStyleSheet(f"color: {T.TEXT_MUTED}; font-size: 11px;")
            except Exception as exc:
                self._status_lbl.setText(f"✖ {str(exc)[:70]}")
                self._status_lbl.setStyleSheet(f"color: {T.ERROR}; font-size: 11px;")

        threading.Thread(target=_try, daemon=True).start()

    # ==================================================================
    # Navigation
    # ==================================================================

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        name = item.data(Qt.ItemDataRole.UserRole)
        if name == "..":
            self._go_up()
            return
        new_path = f"{self._current_path.rstrip('/')}/{name}"
        # Only descend if it's a directory
        try:
            if self._sftp.stat(new_path).st_mode & 0o170000 == 0o040000:  # S_IFDIR
                self._history.append(self._current_path)
                self._list_dir(new_path)
        except Exception:
            pass

    def _go_up(self) -> None:
        if self._current_path in ("", "/"):
            return
        parent = os.path.dirname(self._current_path) or "/"
        self._list_dir(parent)

    def _go_to_path(self) -> None:
        path = self._path_edit.text().strip() or "/"
        try:
            if self._sftp.stat(path).st_mode & 0o170000 == 0o040000:
                self._history.append(self._current_path)
                self._list_dir(path)
            else:
                self._status_lbl.setText("✖ Not a directory")
                self._status_lbl.setStyleSheet(f"color: {T.ERROR}; font-size: 11px;")
        except Exception as exc:
            self._status_lbl.setText(f"✖ {str(exc)[:70]}")
            self._status_lbl.setStyleSheet(f"color: {T.ERROR}; font-size: 11px;")

    def _choose(self) -> None:
        self._on_select(self._current_path)
        self.accept()

    def done(self, result: int) -> None:  # noqa: N802 (Qt naming)
        try:
            if self._sftp is not None:
                self._sftp.close()
            if self._ssh is not None:
                self._ssh.close()
        except Exception:
            pass
        super().done(result)
