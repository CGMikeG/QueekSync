"""
Profile editor dialog – tabbed form for creating / editing a sync profile.
"""

from __future__ import annotations

import os
from tkinter import filedialog
from typing import Callable, List, Optional

import customtkinter as ctk

from core.profile import FilterConfig, Profile, PROFILE_COLOURS, ScheduleConfig
from ui import theme as T
from ui.components import ColourPicker, GlassCard, LabelledEntry, PrimaryButton, Separator


class ProfileEditorDialog(ctk.CTkToplevel):
    """Modal dialog for creating or editing a Profile."""

    def __init__(
        self,
        parent,
        profile: Profile,
        on_save: Callable[[Profile], None],
    ) -> None:
        super().__init__(parent)
        self._profile = profile
        self._on_save = on_save
        self._working = Profile.from_dict(profile.to_dict())  # working copy

        self.title("Edit Profile" if profile.name != "New Profile" else "New Profile")
        self.geometry("720x580")
        self.minsize(640, 520)
        self.configure(fg_color=T.BG_PANEL)

        # Center over parent before building content
        self.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width() - 720) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - 580) // 2
        self.geometry(f"720x580+{px}+{py}")

        self._build()

        # grab_set must be called after the window is fully mapped
        self.after(100, self._make_modal)

    # ==================================================================
    # Layout
    # ==================================================================

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Tab view
        tabs = ctk.CTkTabview(
            self,
            fg_color=T.BG_CARD,
            segmented_button_fg_color=T.BG_PANEL,
            segmented_button_selected_color=T.ACCENT,
            segmented_button_selected_hover_color=T.ACCENT_HOVER,
            segmented_button_unselected_color=T.BG_PANEL,
            segmented_button_unselected_hover_color=T.BG_HOVER,
            text_color=T.TEXT,
            border_color=T.BORDER,
            border_width=1,
            corner_radius=T.RADIUS_LG,
        )
        tabs.grid(row=0, column=0, sticky="nsew", padx=T.PAD_LG, pady=(T.PAD_LG, 0))

        for tab_name in ("General", "Source", "Destination", "Options", "Schedule", "Filters"):
            tabs.add(tab_name)
            tabs.tab(tab_name).configure(fg_color="transparent")

        self._build_general(tabs.tab("General"))
        self._build_endpoint(tabs.tab("Source"), is_source=True)
        self._build_endpoint(tabs.tab("Destination"), is_source=False)
        self._build_options(tabs.tab("Options"))
        self._build_schedule(tabs.tab("Schedule"))
        self._build_filters(tabs.tab("Filters"))

        # Bottom buttons
        btn_bar = ctk.CTkFrame(self, fg_color="transparent")
        btn_bar.grid(row=1, column=0, sticky="ew", padx=T.PAD_LG, pady=T.PAD_MD)

        ctk.CTkButton(
            btn_bar,
            text="Cancel",
            height=36,
            corner_radius=T.RADIUS_MD,
            fg_color="transparent",
            hover_color=T.BG_HOVER,
            text_color=T.TEXT_MUTED,
            border_color=T.BORDER,
            border_width=1,
            command=self.destroy,
        ).pack(side="right", padx=(T.PAD_SM, 0))

        PrimaryButton(btn_bar, text="  Save Profile  ", command=self._save).pack(side="right")

    # ==================================================================
    # Modal helper
    # ==================================================================

    def _make_modal(self) -> None:
        """Called after the window is mapped so grab_set() succeeds."""
        try:
            self.grab_set()
        except Exception:
            pass
        self.focus_set()

    # ==================================================================
    # Tab: General
    # ==================================================================

    def _build_general(self, parent) -> None:
        parent.grid_columnconfigure(0, weight=1)

        frm = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        frm.pack(fill="both", expand=True, padx=T.PAD_SM)
        frm.grid_columnconfigure(0, weight=1)

        # Name
        self._name_entry = LabelledEntry(frm, "Profile Name", placeholder="e.g. Home Backup")
        self._name_entry.set(self._working.name)
        self._name_entry.pack(fill="x", pady=(T.PAD_MD, T.PAD_SM))

        # Description
        ctk.CTkLabel(
            frm, text="Description", font=ctk.CTkFont(size=12),
            text_color=T.TEXT_MUTED, anchor="w",
        ).pack(fill="x", padx=2, pady=(T.PAD_SM, 3))
        self._desc_box = ctk.CTkTextbox(
            frm, height=60,
            fg_color=T.BG_INPUT, border_color=T.BORDER, border_width=1,
            text_color=T.TEXT, corner_radius=T.RADIUS_SM,
        )
        self._desc_box.pack(fill="x")
        self._desc_box.insert("1.0", self._working.description)

        # Colour
        ctk.CTkLabel(
            frm, text="Accent Colour", font=ctk.CTkFont(size=12),
            text_color=T.TEXT_MUTED, anchor="w",
        ).pack(fill="x", padx=2, pady=(T.PAD_MD, 6))
        self._colour_picker = ColourPicker(frm, on_select=self._on_colour, selected=self._working.color)
        self._colour_picker.pack(anchor="w")

        # Enabled toggle
        self._enabled_var = ctk.BooleanVar(value=self._working.enabled)
        ctk.CTkCheckBox(
            frm,
            text="Profile enabled",
            variable=self._enabled_var,
            checkbox_height=18, checkbox_width=18,
            corner_radius=4,
            fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER,
            text_color=T.TEXT,
        ).pack(anchor="w", pady=T.PAD_MD)

    def _on_colour(self, colour: str) -> None:
        self._working.color = colour

    # ==================================================================
    # Tab: Source / Destination (shared)
    # ==================================================================

    def _build_endpoint(self, parent, is_source: bool) -> None:
        cfg = self._working.source if is_source else self._working.destination

        frm = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        frm.pack(fill="both", expand=True, padx=T.PAD_SM)
        frm.grid_columnconfigure((0, 1), weight=1)

        # Type selector
        ctk.CTkLabel(
            frm, text="Connection Type", font=ctk.CTkFont(size=12),
            text_color=T.TEXT_MUTED, anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=2, pady=(T.PAD_MD, 3))

        type_var = ctk.StringVar(value=cfg.type)

        type_seg = ctk.CTkSegmentedButton(
            frm,
            values=["local", "sftp"],
            variable=type_var,
            fg_color=T.BG_INPUT,
            selected_color=T.ACCENT,
            selected_hover_color=T.ACCENT_HOVER,
            unselected_color=T.BG_INPUT,
            unselected_hover_color=T.BG_HOVER,
            text_color=T.TEXT,
            corner_radius=T.RADIUS_SM,
        )
        type_seg.grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, T.PAD_SM))

        # Local path row
        local_frame = ctk.CTkFrame(frm, fg_color="transparent")
        local_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=T.PAD_XS)
        local_frame.grid_columnconfigure(0, weight=1)

        if is_source:
            path_entry_holder = LabelledEntry(local_frame, "Local Path", placeholder="/path/to/source")
        else:
            path_entry_holder = LabelledEntry(local_frame, "Local Path", placeholder="/path/to/destination")
        path_entry_holder.set(cfg.path if cfg.type == "local" else "")
        path_entry_holder.grid(row=0, column=0, sticky="ew")

        ctk.CTkButton(
            local_frame, text="Browse…", width=90, height=30,
            corner_radius=T.RADIUS_SM, fg_color=T.BG_HOVER,
            hover_color=T.BORDER_BRIGHT, text_color=T.TEXT,
            command=lambda: self._browse(path_entry_holder),
        ).grid(row=0, column=1, sticky="s", padx=(T.PAD_SM, 0))

        # SFTP fields
        sftp_frame = ctk.CTkFrame(frm, fg_color="transparent")
        sftp_frame.grid(row=3, column=0, columnspan=2, sticky="ew")
        sftp_frame.grid_columnconfigure((0, 1), weight=1)

        host_entry = LabelledEntry(sftp_frame, "Host", placeholder="192.168.1.100 or hostname")
        host_entry.set(cfg.host)
        host_entry.grid(row=0, column=0, sticky="ew", padx=(0, T.PAD_SM), pady=T.PAD_XS)

        port_entry = LabelledEntry(sftp_frame, "Port", placeholder="22")
        port_entry.set(str(cfg.port))
        port_entry.grid(row=0, column=1, sticky="ew", pady=T.PAD_XS)

        user_entry = LabelledEntry(sftp_frame, "Username")
        user_entry.set(cfg.username)
        user_entry.grid(row=1, column=0, sticky="ew", padx=(0, T.PAD_SM), pady=T.PAD_XS)

        pass_entry = LabelledEntry(sftp_frame, "Password", show="●")
        pass_entry.set(cfg.password)
        pass_entry.grid(row=1, column=1, sticky="ew", pady=T.PAD_XS)

        key_entry = LabelledEntry(sftp_frame, "SSH Key File (optional)", placeholder="~/.ssh/id_rsa")
        key_entry.set(cfg.key_file)
        key_entry.grid(row=2, column=0, columnspan=2, sticky="ew", pady=T.PAD_XS)

        # Remote path row with Browse button
        sftp_path_row = ctk.CTkFrame(sftp_frame, fg_color="transparent")
        sftp_path_row.grid(row=3, column=0, columnspan=2, sticky="ew", pady=T.PAD_XS)
        sftp_path_row.grid_columnconfigure(0, weight=1)

        sftp_path_entry = LabelledEntry(sftp_path_row, "Remote Path", placeholder="/home/user/data")
        sftp_path_entry.set(cfg.path if cfg.type == "sftp" else "")
        sftp_path_entry.grid(row=0, column=0, sticky="ew")

        ctk.CTkButton(
            sftp_path_row, text="📁  Browse…", width=110, height=30,
            corner_radius=T.RADIUS_SM, fg_color=T.BG_HOVER,
            hover_color=T.BORDER_BRIGHT, text_color=T.TEXT,
            command=lambda: self._browse_remote(
                host_entry, port_entry, user_entry, pass_entry, key_entry, sftp_path_entry
            ),
        ).grid(row=0, column=1, sticky="s", padx=(T.PAD_SM, 0))

        # Test connection button
        test_label = ctk.CTkLabel(sftp_frame, text="", font=ctk.CTkFont(size=11), text_color=T.TEXT_MUTED)
        test_label.grid(row=4, column=1, sticky="w")

        test_btn = ctk.CTkButton(
            sftp_frame, text="⟳  Test Connection", width=160, height=30,
            corner_radius=T.RADIUS_SM, fg_color="transparent",
            hover_color=T.BG_HOVER, text_color=T.ACCENT,
            border_color=T.ACCENT, border_width=1,
            command=lambda lbl=test_label: self._test_sftp(host_entry, port_entry, user_entry, pass_entry, key_entry, lbl),
        )
        test_btn.grid(row=4, column=0, sticky="w", pady=T.PAD_SM)

        # Show/hide frames based on type
        def _update_type(*_):
            t = type_var.get()
            if t == "local":
                local_frame.grid()
                sftp_frame.grid_remove()
            else:
                local_frame.grid_remove()
                sftp_frame.grid()

        type_var.trace_add("write", _update_type)
        _update_type()

        # Store references for save
        if is_source:
            self._src_type = type_var
            self._src_local_path = path_entry_holder
            self._src_host = host_entry
            self._src_port = port_entry
            self._src_user = user_entry
            self._src_pass = pass_entry
            self._src_key = key_entry
            self._src_sftp_path = sftp_path_entry
        else:
            self._dst_type = type_var
            self._dst_local_path = path_entry_holder
            self._dst_host = host_entry
            self._dst_port = port_entry
            self._dst_user = user_entry
            self._dst_pass = pass_entry
            self._dst_key = key_entry
            self._dst_sftp_path = sftp_path_entry

    def _browse(self, entry: LabelledEntry) -> None:
        path = filedialog.askdirectory(title="Select folder")
        if path:
            entry.set(path)

    def _browse_remote(
        self,
        host_entry,
        port_entry,
        user_entry,
        pass_entry,
        key_entry,
        path_entry: LabelledEntry,
    ) -> None:
        host = host_entry.get().strip()
        if not host:
            from tkinter import messagebox
            messagebox.showwarning(
                "SFTP Browser",
                "Please fill in the Host field before browsing.",
                parent=self,
            )
            return
        try:
            port = int(port_entry.get() or 22)
        except ValueError:
            port = 22

        from ui.sftp_browser import SFTPBrowserDialog

        def _on_select(selected_path: str) -> None:
            path_entry.set(selected_path)

        SFTPBrowserDialog(
            parent=self,
            host=host,
            port=port,
            username=user_entry.get(),
            password=pass_entry.get(),
            key_file=key_entry.get(),
            initial_path=path_entry.get() or "/",
            on_select=_on_select,
        )

    def _test_sftp(self, host, port, user, pw, key, label) -> None:
        import threading

        label.configure(text="Connecting…", text_color=T.TEXT_MUTED)

        def _try():
            try:
                import paramiko  # type: ignore[import]
                c = paramiko.SSHClient()
                c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                c.connect(
                    hostname=host.get(),
                    port=int(port.get() or 22),
                    username=user.get(),
                    password=pw.get() or None,
                    key_filename=os.path.expanduser(key.get()) if key.get() else None,
                    timeout=8,
                )
                c.close()
                self.after(0, lambda: label.configure(text="✔ Connected", text_color=T.SUCCESS))
            except Exception as exc:
                msg = str(exc)[:60]
                self.after(0, lambda: label.configure(text=f"✖ {msg}", text_color=T.ERROR))

        threading.Thread(target=_try, daemon=True).start()

    # ==================================================================
    # Tab: Options
    # ==================================================================

    def _build_options(self, parent) -> None:
        frm = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        frm.pack(fill="both", expand=True, padx=T.PAD_SM)

        opts = self._working.options

        # Sync mode
        ctk.CTkLabel(
            frm, text="Sync Mode", font=ctk.CTkFont(size=12),
            text_color=T.TEXT_MUTED, anchor="w",
        ).pack(fill="x", padx=2, pady=(T.PAD_MD, 4))

        self._mode_var = ctk.StringVar(value=opts.mode)
        mode_frame = ctk.CTkFrame(frm, fg_color="transparent")
        mode_frame.pack(fill="x")

        modes = [
            ("one_way", "→  One-way",  "Copy source → destination only"),
            ("mirror",  "⬡  Mirror",   "One-way + delete files absent from source"),
            ("two_way", "⇄  Two-way",  "Sync in both directions"),
        ]
        for val, lbl, tip in modes:
            row = ctk.CTkFrame(mode_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkRadioButton(
                row, text=lbl, value=val, variable=self._mode_var,
                fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER, text_color=T.TEXT,
            ).pack(side="left")
            ctk.CTkLabel(
                row, text=tip, font=ctk.CTkFont(size=11), text_color=T.TEXT_DIM,
            ).pack(side="left", padx=T.PAD_SM)

        Separator(frm).pack(fill="x", pady=T.PAD_MD)

        # Boolean options
        bool_opts = [
            ("_opt_delete",    "Delete extra files in destination",  opts.delete_extra),
            ("_opt_ts",        "Preserve file timestamps",           opts.preserve_timestamps),
            ("_opt_symlinks",  "Follow symbolic links",              opts.follow_symlinks),
            ("_opt_checksum",  "Verify file checksums (slower)",     opts.verify_checksums),
        ]
        for attr, label, default in bool_opts:
            var = ctk.BooleanVar(value=default)
            setattr(self, attr, var)
            ctk.CTkCheckBox(
                frm, text=label, variable=var,
                checkbox_height=18, checkbox_width=18, corner_radius=4,
                fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER, text_color=T.TEXT,
            ).pack(anchor="w", pady=3)

        Separator(frm).pack(fill="x", pady=T.PAD_MD)

        # Bandwidth limit
        bw_frame = ctk.CTkFrame(frm, fg_color="transparent")
        bw_frame.pack(fill="x")
        ctk.CTkLabel(
            bw_frame, text="Bandwidth limit (KB/s, 0 = unlimited):",
            font=ctk.CTkFont(size=12), text_color=T.TEXT_MUTED,
        ).pack(side="left")
        self._bw_entry = ctk.CTkEntry(
            bw_frame, width=80,
            fg_color=T.BG_INPUT, border_color=T.BORDER, text_color=T.TEXT,
            corner_radius=T.RADIUS_SM,
        )
        self._bw_entry.insert(0, str(opts.bandwidth_limit_kbps))
        self._bw_entry.pack(side="left", padx=T.PAD_SM)

    # ==================================================================
    # Tab: Schedule
    # ==================================================================

    def _build_schedule(self, parent) -> None:
        frm = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        frm.pack(fill="both", expand=True, padx=T.PAD_SM, pady=T.PAD_MD)

        sched = self._working.schedule

        self._sched_enabled = ctk.BooleanVar(value=sched.enabled)

        ctk.CTkCheckBox(
            frm,
            text="Enable automatic sync on schedule",
            variable=self._sched_enabled,
            checkbox_height=20, checkbox_width=20, corner_radius=4,
            fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER, text_color=T.TEXT,
            font=ctk.CTkFont(size=13),
        ).pack(anchor="w", pady=(T.PAD_MD, T.PAD_LG))

        Separator(frm).pack(fill="x", pady=T.PAD_SM)

        ctk.CTkLabel(
            frm, text="Run every (minutes):",
            font=ctk.CTkFont(size=12), text_color=T.TEXT_MUTED,
        ).pack(anchor="w", pady=(T.PAD_MD, 4))

        self._interval_slider = ctk.CTkSlider(
            frm, from_=1, to=1440, number_of_steps=143,
            fg_color=T.BORDER, button_color=T.ACCENT,
            button_hover_color=T.ACCENT_HOVER, progress_color=T.ACCENT,
            command=self._update_interval_label,
        )
        self._interval_slider.set(sched.interval_minutes)
        self._interval_slider.pack(fill="x", pady=(0, T.PAD_XS))

        self._interval_label = ctk.CTkLabel(
            frm,
            text=self._format_interval(sched.interval_minutes),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=T.ACCENT,
        )
        self._interval_label.pack(anchor="w")

        ctk.CTkLabel(
            frm,
            text="Note: also watches source folder for changes when enabled.",
            font=ctk.CTkFont(size=11), text_color=T.TEXT_DIM,
        ).pack(anchor="w", pady=(T.PAD_LG, 0))

    def _update_interval_label(self, value) -> None:
        self._interval_label.configure(text=self._format_interval(int(value)))

    @staticmethod
    def _format_interval(minutes: int) -> str:
        if minutes < 60:
            return f"{minutes} minute(s)"
        h = minutes // 60
        m = minutes % 60
        return f"{h}h {m}m" if m else f"{h} hour(s)"

    # ==================================================================
    # Tab: Filters
    # ==================================================================

    def _build_filters(self, parent) -> None:
        frm = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        frm.pack(fill="both", expand=True, padx=T.PAD_SM, pady=T.PAD_SM)
        frm.grid_columnconfigure((0, 1), weight=1)

        flt = self._working.filters

        def _make_pattern_box(label: str, default: List[str], row: int) -> ctk.CTkTextbox:
            ctk.CTkLabel(
                frm, text=label, font=ctk.CTkFont(size=12, weight="bold"),
                text_color=T.TEXT_MUTED, anchor="w",
            ).grid(row=row * 2, column=row % 2, sticky="w", padx=T.PAD_SM, pady=(T.PAD_MD, 3))
            box = ctk.CTkTextbox(
                frm, height=130,
                fg_color=T.BG_INPUT, border_color=T.BORDER, border_width=1,
                text_color=T.TEXT, corner_radius=T.RADIUS_SM,
                font=ctk.CTkFont(family="Courier New", size=12),
            )
            box.grid(row=row * 2 + 1, column=row % 2, sticky="nsew", padx=T.PAD_SM, pady=(0, T.PAD_SM))
            box.insert("1.0", "\n".join(default))
            return box

        self._include_box = _make_pattern_box("Include Patterns (fnmatch)", flt.include_patterns, 0)
        self._exclude_box = _make_pattern_box("Exclude Patterns (fnmatch)", flt.exclude_patterns, 1)

        ctk.CTkLabel(
            frm,
            text="One pattern per line. Examples:  *.txt   docs/**   .git",
            font=ctk.CTkFont(size=11), text_color=T.TEXT_DIM,
        ).grid(row=4, column=0, columnspan=2, sticky="w", padx=T.PAD_SM)

    # ==================================================================
    # Save
    # ==================================================================

    def _save(self) -> None:
        p = self._working

        # General
        p.name = self._name_entry.get().strip() or "Unnamed Profile"
        p.description = self._desc_box.get("1.0", "end-1c").strip()
        p.enabled = self._enabled_var.get()

        # Source
        src = p.source
        src.type = self._src_type.get()
        if src.type == "local":
            src.path = self._src_local_path.get()
        else:
            src.host = self._src_host.get()
            src.port = int(self._src_port.get() or 22)
            src.username = self._src_user.get()
            src.password = self._src_pass.get()
            src.key_file = self._src_key.get()
            src.path = self._src_sftp_path.get()

        # Destination
        dst = p.destination
        dst.type = self._dst_type.get()
        if dst.type == "local":
            dst.path = self._dst_local_path.get()
        else:
            dst.host = self._dst_host.get()
            dst.port = int(self._dst_port.get() or 22)
            dst.username = self._dst_user.get()
            dst.password = self._dst_pass.get()
            dst.key_file = self._dst_key.get()
            dst.path = self._dst_sftp_path.get()

        # Options
        p.options.mode = self._mode_var.get()
        p.options.delete_extra = self._opt_delete.get()
        p.options.preserve_timestamps = self._opt_ts.get()
        p.options.follow_symlinks = self._opt_symlinks.get()
        p.options.verify_checksums = self._opt_checksum.get()
        try:
            p.options.bandwidth_limit_kbps = max(0, int(self._bw_entry.get() or 0))
        except ValueError:
            p.options.bandwidth_limit_kbps = 0

        # Schedule
        p.schedule.enabled = self._sched_enabled.get()
        p.schedule.interval_minutes = int(self._interval_slider.get())

        # Filters
        def _lines(box) -> List[str]:
            return [l.strip() for l in box.get("1.0", "end-1c").splitlines() if l.strip()]

        p.filters.include_patterns = _lines(self._include_box)
        p.filters.exclude_patterns = _lines(self._exclude_box)

        # Commit to original
        self._profile.__dict__.update(p.__dict__)

        # Destroy (releases modal grab) before refreshing the panel
        _on_save = self._on_save
        _profile = self._profile
        self.destroy()
        _on_save(_profile)
