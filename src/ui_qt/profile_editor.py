"""
Profile editor dialog – tabbed form for creating / editing a sync profile (PyQt6).
"""

from __future__ import annotations

import os
import threading
import time
from typing import TYPE_CHECKING, Callable, List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.profile import (
    FilterConfig,
    Profile,
    PROFILE_COLOURS,
    ScheduleConfig,
    get_delete_permission_issue,
)
from ui_qt import theme as T
from ui_qt.widgets import (
    ColourPicker,
    GhostButton,
    GlassCard,
    LabelledEntry,
    MutedLabel,
    PrimaryButton,
    ScrollArea,
    attach_tooltip,
)

if TYPE_CHECKING:
    from ui_qt.app import QueekSyncApp


class ProfileEditorDialog(QDialog):
    """Modal dialog for creating or editing a Profile."""

    def __init__(
        self,
        app: "QueekSyncApp",
        profile: Profile,
        on_save: Callable[[Profile], None],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._app = app
        self._profile = profile
        self._on_save = on_save
        self._working = Profile.from_dict(profile.to_dict())  # working copy
        self._working_schedule = ScheduleConfig(
            enabled=profile.schedule.enabled,
            interval_minutes=profile.schedule.interval_minutes,
        )

        self.setWindowTitle("Edit Profile" if profile.name != "New Profile" else "New Profile")
        self.resize(760, 620)
        self.setMinimumSize(660, 540)

        self._build()

    # ==================================================================
    # Layout
    # ==================================================================

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(T.PAD_LG, T.PAD_LG, T.PAD_LG, T.PAD_MD)
        root.setSpacing(T.PAD_SM)

        self._tabs = QTabWidget(self)
        root.addWidget(self._tabs, 1)

        self._build_general()
        self._build_endpoint(is_source=True)
        self._build_endpoint(is_source=False)
        self._build_options()
        self._build_schedule()
        self._build_filters()

        # ── Bottom buttons ─────────────────────────────────────────────
        btn_bar = QHBoxLayout()
        btn_bar.addStretch()
        cancel_btn = GhostButton("Cancel", self, command=self.reject)
        btn_bar.addWidget(cancel_btn)
        save_btn = PrimaryButton("  Save Profile  ", self, command=self._save)
        btn_bar.addWidget(save_btn)
        root.addLayout(btn_bar)

    def _scroll_tab(self, title: str) -> tuple[QWidget, QScrollArea, QWidget, QVBoxLayout]:
        """Create a tab whose content scrolls (mouse wheel + keys work natively)."""
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        scroll = ScrollArea(page)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        host = QWidget()
        host_layout = QVBoxLayout(host)
        host_layout.setContentsMargins(T.PAD_MD, T.PAD_MD, T.PAD_MD, T.PAD_MD)
        host_layout.setSpacing(8)
        scroll.setWidget(host)
        page_layout.addWidget(scroll)
        self._tabs.addTab(page, title)
        return page, scroll, host, host_layout

    # ==================================================================
    # Tab: General
    # ==================================================================

    def _build_general(self) -> None:
        _, _, host, layout = self._scroll_tab("General")

        # Name
        self._name_entry = LabelledEntry(
            "Profile Name",
            placeholder="e.g. Home Backup",
            tooltip="Give this sync job a clear name. Example: Home Backup, NAS Mirror, or Client Archive.",
        )
        self._name_entry.set(self._working.name)
        layout.addWidget(self._name_entry)

        # Description
        desc_lbl = MutedLabel("Description")
        layout.addWidget(desc_lbl)
        self._desc_box = QTextEdit()
        self._desc_box.setFixedHeight(70)
        self._desc_box.setPlainText(self._working.description)
        layout.addWidget(self._desc_box)

        # Colour
        colour_lbl = MutedLabel("Accent Colour")
        layout.addWidget(colour_lbl)
        self._colour_picker = ColourPicker(
            on_select=self._on_colour, selected=self._working.color, parent=host
        )
        layout.addWidget(self._colour_picker)

        # Enabled
        self._enabled_cb = QCheckBox("Profile enabled")
        self._enabled_cb.setChecked(self._working.enabled)
        layout.addWidget(self._enabled_cb)
        layout.addStretch()

    def _on_colour(self, colour: str) -> None:
        self._working.color = colour

    # ==================================================================
    # Tab: Source / Destination (shared)
    # ==================================================================

    def _build_endpoint(self, is_source: bool) -> None:
        title = "Source" if is_source else "Destination"
        cfg = self._working.source if is_source else self._working.destination
        _, _, host, layout = self._scroll_tab(title)

        # Connection type
        type_lbl = MutedLabel("Connection Type")
        layout.addWidget(type_lbl)
        type_combo = QComboBox()
        type_combo.addItems(["local", "sftp"])
        idx = type_combo.findText(cfg.type)
        type_combo.setCurrentIndex(idx if idx >= 0 else 0)
        layout.addWidget(type_combo)

        # ── Local section ──────────────────────────────────────────────
        local_card = GlassCard(host)
        local_form = QGridLayout(local_card)
        local_form.setContentsMargins(T.PAD_MD, T.PAD_MD, T.PAD_MD, T.PAD_MD)
        local_form.setHorizontalSpacing(T.PAD_SM)
        local_form.setVerticalSpacing(T.PAD_SM)

        local_path = LabelledEntry(
            "Local Path",
            placeholder="/path/to/source" if is_source else "/path/to/destination",
            tooltip="Enter the folder path on this computer.",
        )
        local_path.set(cfg.path if cfg.type == "local" else "")
        local_form.addWidget(local_path, 0, 0)

        browse_btn = GhostButton("Browse…", local_card, command=lambda: self._browse(local_path))
        browse_btn.setFixedSize(90, 30)
        local_form.addWidget(browse_btn, 0, 1, Qt.AlignmentFlag.AlignBottom)

        local_test_lbl = MutedLabel("")
        local_form.addWidget(local_test_lbl, 1, 0)

        local_test_btn = GhostButton(
            "Test Folder Access", local_card,
            command=lambda: self._test_local_path(local_path, local_test_lbl, is_source),
        )
        local_test_btn.setFixedSize(150, 30)
        local_form.addWidget(local_test_btn, 1, 1)

        if not is_source:
            local_dir_lbl = MutedLabel("")
            local_form.addWidget(local_dir_lbl, 2, 0)
            create_dir_btn = GhostButton(
                "Create Test Folder", local_card,
                command=lambda: self._create_local_test_folder(local_path, local_dir_lbl),
            )
            create_dir_btn.setFixedSize(150, 30)
            local_form.addWidget(create_dir_btn, 2, 1)
        layout.addWidget(local_card)

        # ── SFTP section ───────────────────────────────────────────────
        sftp_card = GlassCard(host)
        sftp_form = QGridLayout(sftp_card)
        sftp_form.setContentsMargins(T.PAD_MD, T.PAD_MD, T.PAD_MD, T.PAD_MD)
        sftp_form.setHorizontalSpacing(T.PAD_SM)
        sftp_form.setVerticalSpacing(T.PAD_SM)

        host_entry = LabelledEntry("Host", placeholder="192.168.1.100 or hostname")
        host_entry.set(cfg.host)
        sftp_form.addWidget(host_entry, 0, 0)

        port_entry = LabelledEntry("Port", placeholder="22")
        port_entry.set(str(cfg.port))
        sftp_form.addWidget(port_entry, 0, 1)

        user_entry = LabelledEntry("Username")
        user_entry.set(cfg.username)
        sftp_form.addWidget(user_entry, 1, 0)

        pass_entry = LabelledEntry("Password", show="●")
        pass_entry.set(cfg.password)
        sftp_form.addWidget(pass_entry, 1, 1)

        key_entry = LabelledEntry("SSH Key File (optional)", placeholder="~/.ssh/id_rsa")
        key_entry.set(cfg.key_file)
        sftp_form.addWidget(key_entry, 2, 0, 1, 2)

        sftp_path = LabelledEntry("Remote Path", placeholder="/home/user/data")
        sftp_path.set(cfg.path if cfg.type == "sftp" else "")
        sftp_form.addWidget(sftp_path, 3, 0)

        remote_browse_btn = GhostButton("📁  Browse…", sftp_card, command=lambda: self._browse_remote(
            host_entry, port_entry, user_entry, pass_entry, key_entry, sftp_path
        ))
        remote_browse_btn.setFixedSize(110, 30)
        sftp_form.addWidget(remote_browse_btn, 3, 1, Qt.AlignmentFlag.AlignBottom)

        sftp_test_lbl = MutedLabel("")
        sftp_form.addWidget(sftp_test_lbl, 4, 1)

        test_btn = GhostButton("⟳  Test Connection", sftp_card, command=lambda: self._test_sftp(
            host_entry, port_entry, user_entry, pass_entry, key_entry, sftp_test_lbl
        ))
        test_btn.setFixedSize(160, 30)
        sftp_form.addWidget(test_btn, 4, 0)

        sftp_access_lbl = MutedLabel("")
        sftp_form.addWidget(sftp_access_lbl, 5, 1)

        access_btn = GhostButton("⟳  Test Folder Access", sftp_card, command=lambda: self._test_sftp_path_access(
            host_entry, port_entry, user_entry, pass_entry, key_entry, sftp_path, sftp_access_lbl, is_source
        ))
        access_btn.setFixedSize(180, 30)
        sftp_form.addWidget(access_btn, 5, 0)
        layout.addWidget(sftp_card)

        # Show/hide sections on type change
        def _update_type(value: str) -> None:
            is_local = value == "local"
            local_card.setVisible(is_local)
            sftp_card.setVisible(not is_local)

        type_combo.currentTextChanged.connect(_update_type)
        _update_type(type_combo.currentText())
        layout.addStretch()

        # Store refs for save
        if is_source:
            self._src_type, self._src_local, self._src_host, self._src_port = (
                type_combo, local_path, host_entry, port_entry)
            self._src_user, self._src_pass, self._src_key, self._src_sftp_path = (
                user_entry, pass_entry, key_entry, sftp_path)
        else:
            self._dst_type, self._dst_local, self._dst_host, self._dst_port = (
                type_combo, local_path, host_entry, port_entry)
            self._dst_user, self._dst_pass, self._dst_key, self._dst_sftp_path = (
                user_entry, pass_entry, key_entry, sftp_path)

    # ==================================================================
    # Tab: Options
    # ==================================================================

    def _build_options(self) -> None:
        _, _, host, layout = self._scroll_tab("Options")
        opts = self._working.options

        mode_lbl = MutedLabel("Sync Mode")
        layout.addWidget(mode_lbl)
        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["one_way", "mirror", "two_way"])
        idx = self._mode_combo.findText(opts.mode)
        self._mode_combo.setCurrentIndex(idx if idx >= 0 else 0)
        layout.addWidget(self._mode_combo)
        attach_tooltip(
            self._mode_combo,
            "one_way: copy source → destination (never delete). "
            "mirror: also delete extra files in destination. "
            "two_way: bidirectional – copy newer file to the other side.",
        )

        self._delete_cb = QCheckBox("Delete extra files in destination (mirror)")
        self._delete_cb.setChecked(opts.delete_extra)
        layout.addWidget(self._delete_cb)

        self._ts_cb = QCheckBox("Preserve timestamps")
        self._ts_cb.setChecked(opts.preserve_timestamps)
        layout.addWidget(self._ts_cb)

        self._symlink_cb = QCheckBox("Follow symlinks")
        self._symlink_cb.setChecked(opts.follow_symlinks)
        layout.addWidget(self._symlink_cb)

        self._checksum_cb = QCheckBox("Verify checksums")
        self._checksum_cb.setChecked(opts.verify_checksums)
        layout.addWidget(self._checksum_cb)

        self._rsync_cb = QCheckBox("Prefer rsync over SSH when available")
        self._rsync_cb.setChecked(opts.use_rsync_ssh)
        layout.addWidget(self._rsync_cb)

        bw_row = QHBoxLayout()
        bw_lbl = MutedLabel("Bandwidth limit (kbps, 0 = unlimited)")
        bw_row.addWidget(bw_lbl)
        self._bw_spin = QSpinBox()
        self._bw_spin.setRange(0, 10_000_000)
        self._bw_spin.setValue(opts.bandwidth_limit_kbps)
        bw_row.addWidget(self._bw_spin)
        layout.addLayout(bw_row)
        layout.addStretch()

    # ==================================================================
    # Tab: Schedule
    # ==================================================================

    def _build_schedule(self) -> None:
        _, _, host, layout = self._scroll_tab("Schedule")
        sched = self._working_schedule

        self._sched_cb = QCheckBox("Enable automatic syncing")
        self._sched_cb.setChecked(sched.enabled)
        layout.addWidget(self._sched_cb)

        interval_row = QHBoxLayout()
        interval_lbl = MutedLabel("Interval (minutes)")
        interval_row.addWidget(interval_lbl)
        self._interval_spin = QSpinBox()
        self._interval_spin.setRange(1, 60 * 24 * 7)
        self._interval_spin.setValue(sched.interval_minutes)
        interval_row.addWidget(self._interval_spin)
        interval_row.addStretch()
        layout.addLayout(interval_row)
        layout.addStretch()

    # ==================================================================
    # Tab: Filters
    # ==================================================================

    def _build_filters(self) -> None:
        _, _, host, layout = self._scroll_tab("Filters")
        filters = self._working.filters

        inc_lbl = MutedLabel("Include patterns (fnmatch style)")
        layout.addWidget(inc_lbl)
        self._include_list = QListWidget()
        for pat in filters.include_patterns:
            self._include_list.addItem(pat)
        self._include_list.setFixedHeight(110)
        layout.addWidget(self._include_list)

        inc_row = QHBoxLayout()
        self._include_entry = QLineEdit()
        self._include_entry.setPlaceholderText("e.g. *.jpg")
        inc_row.addWidget(self._include_entry, 1)
        add_inc = GhostButton("Add", host, command=lambda: self._add_pattern(self._include_entry, self._include_list))
        inc_row.addWidget(add_inc)
        layout.addLayout(inc_row)

        exc_lbl = MutedLabel("Exclude patterns (fnmatch style)")
        layout.addWidget(exc_lbl)
        self._exclude_list = QListWidget()
        for pat in filters.exclude_patterns:
            self._exclude_list.addItem(pat)
        self._exclude_list.setFixedHeight(140)
        layout.addWidget(self._exclude_list)

        exc_row = QHBoxLayout()
        self._exclude_entry = QLineEdit()
        self._exclude_entry.setPlaceholderText("e.g. *.tmp")
        exc_row.addWidget(self._exclude_entry, 1)
        add_exc = GhostButton("Add", host, command=lambda: self._add_pattern(self._exclude_entry, self._exclude_list))
        exc_row.addWidget(add_exc)
        layout.addLayout(exc_row)

        remove_btn = GhostButton("Remove Selected", host, command=self._remove_selected_patterns)
        layout.addWidget(remove_btn)
        layout.addStretch()

    @staticmethod
    def _add_pattern(entry: QLineEdit, list_widget: QListWidget) -> None:
        text = entry.text().strip()
        if text:
            list_widget.addItem(text)
            entry.clear()

    def _remove_selected_patterns(self) -> None:
        for item in self._include_list.selectedItems():
            self._include_list.takeItem(self._include_list.row(item))
        for item in self._exclude_list.selectedItems():
            self._exclude_list.takeItem(self._exclude_list.row(item))

    # ==================================================================
    # Browse / test helpers
    # ==================================================================

    def _browse(self, entry: LabelledEntry) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select folder")
        if path:
            entry.set(path)

    def _browse_remote(self, host_entry, port_entry, user_entry, pass_entry, key_entry, sftp_path) -> None:
        host = host_entry.get().strip()
        if not host:
            QMessageBox.warning(self, "SFTP Browser", "Please fill in the Host field before browsing.")
            return
        try:
            port = int(port_entry.get() or 22)
        except ValueError:
            port = 22

        from ui_qt.sftp_browser import SFTPBrowserDialog

        def _on_select(selected_path: str) -> None:
            sftp_path.set(selected_path)

        dlg = SFTPBrowserDialog(
            host=host,
            port=port,
            username=user_entry.get(),
            password=pass_entry.get(),
            key_file=key_entry.get(),
            initial_path=sftp_path.get() or "/",
            on_select=_on_select,
            parent=self,
        )
        dlg.exec()

    def _test_sftp(self, host_entry, port_entry, user_entry, pass_entry, key_entry, label) -> None:
        host_val = host_entry.get().strip()
        try:
            port_val = int(port_entry.get() or 22)
        except ValueError:
            port_val = 22
        user_val = user_entry.get().strip()
        pw_val = pass_entry.get()
        key_val = key_entry.get().strip()

        label.setText("Connecting…")
        label.setStyleSheet(f"color: {T.TEXT_MUTED}; font-size: 11px;")

        def _try() -> None:
            try:
                import paramiko  # type: ignore[import]
                c = paramiko.SSHClient()
                c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                c.connect(
                    hostname=host_val,
                    port=port_val,
                    username=user_val,
                    password=pw_val or None,
                    key_filename=os.path.expanduser(key_val) if key_val else None,
                    timeout=8,
                )
                c.close()
                label.setText("✔ Connected")
                label.setStyleSheet(f"color: {T.SUCCESS}; font-size: 11px;")
            except Exception as exc:
                msg = str(exc)[:60]
                label.setText(f"✖ {msg}")
                label.setStyleSheet(f"color: {T.ERROR}; font-size: 11px;")

        threading.Thread(target=_try, daemon=True).start()

    def _test_local_path(self, entry: LabelledEntry, label: QLabel, is_source: bool) -> None:
        path = os.path.expanduser(entry.get().strip())
        role = "Source" if is_source else "Destination"
        if not path:
            label.setText(f"✖ {role} path is empty")
            label.setStyleSheet(f"color: {T.ERROR}; font-size: 11px;")
            return
        if not os.path.exists(path):
            label.setText(f"✖ {role} folder not found")
            label.setStyleSheet(f"color: {T.ERROR}; font-size: 11px;")
            return
        if not os.path.isdir(path):
            label.setText(f"✖ {role} path is not a folder")
            label.setStyleSheet(f"color: {T.ERROR}; font-size: 11px;")
            return
        try:
            if is_source:
                if not os.access(path, os.R_OK | os.X_OK):
                    raise PermissionError("folder is not readable")
                os.listdir(path)
                label.setText("✔ Source folder exists and is readable")
                label.setStyleSheet(f"color: {T.SUCCESS}; font-size: 11px;")
                return
            if not os.access(path, os.W_OK | os.X_OK):
                raise PermissionError("folder is not writable")
            stamp = time.strftime("%Y%m%d-%H%M%S")
            probe_name = f"foldertest-{stamp}.txt"
            probe_path = os.path.join(path, probe_name)
            with open(probe_path, "w", encoding="utf-8") as fh:
                fh.write(f"QueekSync folder access test\nCreated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            label.setText(f"✔ Destination folder exists and created {probe_name}")
            label.setStyleSheet(f"color: {T.SUCCESS}; font-size: 11px;")
        except Exception as exc:
            label.setText(f"✖ {str(exc)[:80]}")
            label.setStyleSheet(f"color: {T.ERROR}; font-size: 11px;")

    def _create_local_test_folder(self, entry: LabelledEntry, label: QLabel) -> None:
        path = os.path.expanduser(entry.get().strip())
        if not path:
            label.setText("✖ Destination path is empty")
            label.setStyleSheet(f"color: {T.ERROR}; font-size: 11px;")
            return
        if not os.path.isdir(path):
            label.setText("✖ Destination folder not found")
            label.setStyleSheet(f"color: {T.ERROR}; font-size: 11px;")
            return
        try:
            test_dir = os.path.join(path, "testconnection")
            os.makedirs(test_dir, exist_ok=True)
            label.setText("✔ Created destination folder testconnection")
            label.setStyleSheet(f"color: {T.SUCCESS}; font-size: 11px;")
        except Exception as exc:
            label.setText(f"✖ {str(exc)[:80]}")
            label.setStyleSheet(f"color: {T.ERROR}; font-size: 11px;")

    def _test_sftp_path_access(self, host_entry, port_entry, user_entry, pass_entry, key_entry, sftp_path, label, is_source: bool) -> None:
        host_val = host_entry.get().strip()
        try:
            port_val = int(port_entry.get() or 22)
        except ValueError:
            port_val = 22
        user_val = user_entry.get().strip()
        pw_val = pass_entry.get()
        key_val = key_entry.get().strip()
        path_val = sftp_path.get().strip()
        role = "source" if is_source else "destination"

        if not host_val or not user_val or not path_val:
            label.setText("✖ Fill in host, username, and remote path first")
            label.setStyleSheet(f"color: {T.ERROR}; font-size: 11px;")
            return

        label.setText("Testing…")
        label.setStyleSheet(f"color: {T.TEXT_MUTED}; font-size: 11px;")

        def _try() -> None:
            try:
                import paramiko  # type: ignore[import]
                c = paramiko.SSHClient()
                c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                c.connect(
                    hostname=host_val, port=port_val, username=user_val,
                    password=pw_val or None,
                    key_filename=os.path.expanduser(key_val) if key_val else None,
                    timeout=8,
                )
                sftp = c.open_sftp()
                try:
                    sftp.stat(path_val)
                except FileNotFoundError:
                    label.setText(f"✖ {role} folder not found")
                    label.setStyleSheet(f"color: {T.ERROR}; font-size: 11px;")
                    c.close()
                    return
                if is_source:
                    label.setText("✔ Source folder exists on server")
                    label.setStyleSheet(f"color: {T.SUCCESS}; font-size: 11px;")
                else:
                    stamp = time.strftime("%Y%m%d-%H%M%S")
                    probe = f"{path_val.rstrip('/')}/foldertest-{stamp}.txt"
                    with sftp.file(probe, "w") as fh:
                        fh.write("QueekSync folder access test\n")
                    try:
                        sftp.remove(probe)
                    except OSError:
                        pass
                    label.setText("✔ Destination folder exists and is writable")
                    label.setStyleSheet(f"color: {T.SUCCESS}; font-size: 11px;")
                sftp.close()
                c.close()
            except Exception as exc:
                label.setText(f"✖ {str(exc)[:70]}")
                label.setStyleSheet(f"color: {T.ERROR}; font-size: 11px;")

        threading.Thread(target=_try, daemon=True).start()

    # ==================================================================
    # Save
    # ==================================================================

    def _save(self) -> None:
        w = self._working
        w.name = self._name_entry.get().strip() or "Untitled Profile"
        w.description = self._desc_box.toPlainText().strip()
        w.enabled = self._enabled_cb.isChecked()

        # Endpoints
        self._apply_endpoint(w.source, self._src_type, self._src_local, self._src_host,
                             self._src_port, self._src_user, self._src_pass, self._src_key,
                             self._src_sftp_path)
        self._apply_endpoint(w.destination, self._dst_type, self._dst_local, self._dst_host,
                             self._dst_port, self._dst_user, self._dst_pass, self._dst_key,
                             self._dst_sftp_path)

        # Options
        w.options.mode = self._mode_combo.currentText()
        w.options.delete_extra = self._delete_cb.isChecked()
        w.options.preserve_timestamps = self._ts_cb.isChecked()
        w.options.follow_symlinks = self._symlink_cb.isChecked()
        w.options.verify_checksums = self._checksum_cb.isChecked()
        w.options.use_rsync_ssh = self._rsync_cb.isChecked()
        w.options.bandwidth_limit_kbps = self._bw_spin.value()

        # Schedule
        w.schedule.enabled = self._sched_cb.isChecked()
        w.schedule.interval_minutes = self._interval_spin.value()

        # Filters
        w.filters.include_patterns = [
            self._include_list.item(i).text() for i in range(self._include_list.count())
        ]
        w.filters.exclude_patterns = [
            self._exclude_list.item(i).text() for i in range(self._exclude_list.count())
        ]

        # Warn about delete-permission issues on Linux
        issue = get_delete_permission_issue(w)
        if issue:
            QMessageBox.warning(self, "Permission Warning", issue)

        self._on_save(w)
        self.accept()

    @staticmethod
    def _apply_endpoint(cfg, type_combo, local_path, host_entry, port_entry,
                        user_entry, pass_entry, key_entry, sftp_path) -> None:
        """Write the editor widgets for one endpoint back into an EndpointConfig."""
        if type_combo.currentText() == "local":
            cfg.type = "local"
            cfg.path = local_path.get().strip()
            cfg.host = ""
            cfg.port = 22
            cfg.username = ""
            cfg.password = ""
            cfg.key_file = ""
        else:
            cfg.type = "sftp"
            cfg.host = host_entry.get().strip()
            try:
                cfg.port = int(port_entry.get() or 22)
            except ValueError:
                cfg.port = 22
            cfg.username = user_entry.get().strip()
            cfg.password = pass_entry.get()
            cfg.key_file = key_entry.get().strip()
            cfg.path = sftp_path.get().strip()
