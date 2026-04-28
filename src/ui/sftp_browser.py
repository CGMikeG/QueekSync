"""
SFTP Remote Folder Browser Dialog.
Lets the user navigate the remote filesystem and pick a directory.
"""

from __future__ import annotations

import threading
from typing import Callable, List, Optional

import customtkinter as ctk

from ui import theme as T


class SFTPBrowserDialog(ctk.CTkToplevel):
    """A modal dialog that connects to an SFTP server and lets the user
    browse and select a remote directory."""

    def __init__(
        self,
        parent,
        host: str,
        port: int,
        username: str,
        password: str,
        key_file: str,
        initial_path: str,
        on_select: Callable[[str], None],
    ) -> None:
        super().__init__(parent)
        self.title("Browse Remote Folder")
        self.geometry("560x480")
        self.minsize(480, 380)
        self.configure(fg_color=T.BG_PANEL)

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

        # Center over parent
        self.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width() - 560) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - 480) // 2
        self.geometry(f"560x480+{px}+{py}")

        self._build()
        self.after(150, self._make_modal)

        # Connect in background
        self._connect()

    # ==================================================================
    # Layout
    # ==================================================================

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ── Status bar ─────────────────────────────────────────────────
        status_bar = ctk.CTkFrame(self, fg_color=T.BG_CARD, corner_radius=0, height=32)
        status_bar.grid(row=0, column=0, sticky="ew")
        status_bar.grid_propagate(False)

        self._status_lbl = ctk.CTkLabel(
            status_bar, text=f"Connecting to {self._host}…",
            font=ctk.CTkFont(size=11), text_color=T.TEXT_MUTED, anchor="w",
        )
        self._status_lbl.pack(side="left", padx=T.PAD_MD, fill="y")

        # ── Path breadcrumb bar ────────────────────────────────────────
        path_bar = ctk.CTkFrame(self, fg_color=T.BG_CARD, corner_radius=0, height=40)
        path_bar.grid(row=1, column=0, sticky="ew")
        path_bar.grid_columnconfigure(1, weight=1)
        path_bar.grid_propagate(False)

        # Up button
        self._up_btn = ctk.CTkButton(
            path_bar, text="↑  Up", width=72, height=28,
            corner_radius=T.RADIUS_SM,
            fg_color="transparent", hover_color=T.BG_HOVER,
            text_color=T.TEXT_MUTED, border_color=T.BORDER, border_width=1,
            command=self._go_up, state="disabled",
        )
        self._up_btn.grid(row=0, column=0, padx=(T.PAD_SM, 0), pady=T.PAD_XS)

        # Home button
        ctk.CTkButton(
            path_bar, text="⌂", width=32, height=28,
            corner_radius=T.RADIUS_SM,
            fg_color="transparent", hover_color=T.BG_HOVER,
            text_color=T.TEXT_MUTED, border_color=T.BORDER, border_width=1,
            command=self._go_home,
        ).grid(row=0, column=1, padx=T.PAD_XS, pady=T.PAD_XS, sticky="w")

        # Current path label
        self._path_lbl = ctk.CTkLabel(
            path_bar, text=self._current_path,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=T.ACCENT, anchor="w",
        )
        self._path_lbl.grid(row=0, column=2, sticky="ew", padx=T.PAD_SM)
        path_bar.grid_columnconfigure(2, weight=1)

        # ── Directory list ─────────────────────────────────────────────
        list_frame = ctk.CTkFrame(self, fg_color=T.BG_ROOT, corner_radius=0)
        list_frame.grid(row=2, column=0, sticky="nsew")
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)

        self._scrollable = ctk.CTkScrollableFrame(
            list_frame,
            fg_color="transparent",
            scrollbar_button_color=T.BORDER,
            scrollbar_button_hover_color=T.BORDER_BRIGHT,
        )
        self._scrollable.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        self._scrollable.grid_columnconfigure(0, weight=1)

        self._loading_lbl = ctk.CTkLabel(
            self._scrollable, text="Connecting…",
            font=ctk.CTkFont(size=13), text_color=T.TEXT_DIM,
        )
        self._loading_lbl.grid(row=0, column=0, pady=40)

        # ── Bottom buttons ─────────────────────────────────────────────
        btn_bar = ctk.CTkFrame(self, fg_color=T.BG_CARD, corner_radius=0, height=52)
        btn_bar.grid(row=3, column=0, sticky="ew")
        btn_bar.grid_propagate(False)

        ctk.CTkButton(
            btn_bar, text="Cancel", width=90, height=32,
            corner_radius=T.RADIUS_SM,
            fg_color="transparent", hover_color=T.BG_HOVER,
            text_color=T.TEXT_MUTED, border_color=T.BORDER, border_width=1,
            command=self._cancel,
        ).pack(side="right", padx=(T.PAD_SM, T.PAD_MD), pady=T.PAD_SM)

        self._select_btn = ctk.CTkButton(
            btn_bar, text="✔  Select This Folder", width=180, height=32,
            corner_radius=T.RADIUS_SM,
            fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER,
            text_color="#ffffff",
            command=self._confirm,
        )
        self._select_btn.pack(side="right", padx=T.PAD_XS, pady=T.PAD_SM)

        self._selected_label = ctk.CTkLabel(
            btn_bar, text="",
            font=ctk.CTkFont(size=11), text_color=T.TEXT_MUTED, anchor="w",
        )
        self._selected_label.pack(side="left", padx=T.PAD_MD, fill="y")

    # ==================================================================
    # Modal helper
    # ==================================================================

    def _make_modal(self) -> None:
        try:
            self.grab_set()
        except Exception:
            pass
        self.focus_set()

    # ==================================================================
    # SFTP connection
    # ==================================================================

    def _connect(self) -> None:
        def _do():
            try:
                import os
                import paramiko  # type: ignore[import]

                self._ssh = paramiko.SSHClient()
                self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                kwargs: dict = {
                    "hostname": self._host,
                    "port": self._port,
                    "username": self._username,
                    "timeout": 15,
                }
                if self._key_file:
                    kwargs["key_filename"] = os.path.expanduser(self._key_file)
                elif self._password:
                    kwargs["password"] = self._password
                self._ssh.connect(**kwargs)
                self._sftp = self._ssh.open_sftp()
                self.after(0, lambda: self._on_connected())
            except Exception as exc:
                self.after(0, lambda: self._on_error(str(exc)))

        threading.Thread(target=_do, daemon=True).start()

    def _on_connected(self) -> None:
        self._status_lbl.configure(
            text=f"Connected  ·  {self._username}@{self._host}", text_color=T.SUCCESS
        )
        self._list_directory(self._current_path)

    def _on_error(self, msg: str) -> None:
        self._status_lbl.configure(
            text=f"Error: {msg[:80]}", text_color=T.ERROR
        )
        self._loading_lbl.configure(text=f"Connection failed:\n{msg}", text_color=T.ERROR)

    # ==================================================================
    # Directory listing
    # ==================================================================

    def _list_directory(self, path: str) -> None:
        self._status_lbl.configure(text=f"Loading {path} …", text_color=T.TEXT_MUTED)
        self._clear_list()
        self._loading_lbl = ctk.CTkLabel(
            self._scrollable, text="Loading…",
            font=ctk.CTkFont(size=12), text_color=T.TEXT_DIM,
        )
        self._loading_lbl.grid(row=0, column=0, pady=30)

        def _do():
            try:
                import stat as stat_mod
                entries = []
                items = self._sftp.listdir_attr(path)
                for item in sorted(items, key=lambda x: (not stat_mod.S_ISDIR(x.st_mode), x.filename.lower())):
                    is_dir = stat_mod.S_ISDIR(item.st_mode)
                    entries.append((item.filename, is_dir))
                self.after(0, lambda: self._populate_list(path, entries))
            except Exception as exc:
                self.after(0, lambda: self._on_list_error(str(exc)))

        threading.Thread(target=_do, daemon=True).start()

    def _populate_list(self, path: str, entries: list) -> None:
        self._current_path = path
        self._path_lbl.configure(text=path)
        self._update_selected_label()
        self._up_btn.configure(state="normal" if path != "/" else "disabled")
        self._status_lbl.configure(
            text=f"{len(entries)} item(s)  ·  {self._username}@{self._host}", text_color=T.TEXT_MUTED
        )

        self._clear_list()

        if not entries:
            ctk.CTkLabel(
                self._scrollable, text="(empty directory)",
                font=ctk.CTkFont(size=12), text_color=T.TEXT_DIM,
            ).grid(row=0, column=0, pady=20)
            return

        for idx, (name, is_dir) in enumerate(entries):
            icon = "📁  " if is_dir else "📄  "
            color = T.TEXT if is_dir else T.TEXT_DIM
            hover = T.BG_HOVER if is_dir else "transparent"

            row_btn = ctk.CTkButton(
                self._scrollable,
                text=f"{icon}{name}",
                anchor="w",
                height=34,
                corner_radius=T.RADIUS_SM,
                fg_color="transparent",
                hover_color=hover if is_dir else T.BG_CARD,
                text_color=color,
                border_width=0,
                font=ctk.CTkFont(size=12),
                cursor="hand2" if is_dir else "arrow",
            )
            row_btn.grid(row=idx, column=0, sticky="ew", pady=1, padx=4)

            if is_dir:
                full_path = f"{path.rstrip('/')}/{name}"
                row_btn.configure(command=lambda p=full_path: self._navigate(p))

    def _on_list_error(self, msg: str) -> None:
        self._clear_list()
        ctk.CTkLabel(
            self._scrollable, text=f"Error loading directory:\n{msg}",
            font=ctk.CTkFont(size=12), text_color=T.ERROR,
        ).grid(row=0, column=0, pady=20)

    def _clear_list(self) -> None:
        for child in self._scrollable.winfo_children():
            child.destroy()

    # ==================================================================
    # Navigation
    # ==================================================================

    def _navigate(self, path: str) -> None:
        self._history.append(self._current_path)
        self._list_directory(path)

    def _go_up(self) -> None:
        parent = self._current_path.rstrip("/").rsplit("/", 1)[0] or "/"
        self._history.append(self._current_path)
        self._list_directory(parent)

    def _go_home(self) -> None:
        try:
            home = self._sftp.normalize(".")
        except Exception:
            home = "/"
        self._history.append(self._current_path)
        self._list_directory(home)

    def _update_selected_label(self) -> None:
        self._selected_label.configure(
            text=f"Selected:  {self._current_path}"
        )

    # ==================================================================
    # Confirm / cancel
    # ==================================================================

    def _confirm(self) -> None:
        selected = self._current_path
        self._cleanup()
        self._on_select(selected)
        self.destroy()

    def _cancel(self) -> None:
        self._cleanup()
        self.destroy()

    def _cleanup(self) -> None:
        if self._sftp:
            try:
                self._sftp.close()
            except Exception:
                pass
        if self._ssh:
            try:
                self._ssh.close()
            except Exception:
                pass
