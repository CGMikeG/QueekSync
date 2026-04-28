"""
Settings panel – application-wide preferences.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

from ui import theme as T
from ui.components import GlassCard, PrimaryButton, Separator

if TYPE_CHECKING:
    from ui.app import QSyncApp


class SettingsPanel(ctk.CTkFrame):
    def __init__(self, master, app: "QSyncApp", **kw) -> None:
        kw.setdefault("fg_color", "transparent")
        super().__init__(master, **kw)
        self._app = app
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build()

    # ------------------------------------------------------------------

    def _build(self) -> None:
        scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=T.BORDER,
            scrollbar_button_hover_color=T.BORDER_BRIGHT,
        )
        scroll.grid(row=0, column=0, sticky="nsew", padx=T.PAD_LG, pady=T.PAD_MD)
        scroll.grid_columnconfigure(0, weight=1)

        cfg = self._app.config_mgr.config

        # ---- Appearance -------------------------------------------
        self._section(scroll, "Appearance", row=0)

        app_card = GlassCard(scroll)
        app_card.grid(row=1, column=0, sticky="ew", pady=(0, T.PAD_MD))
        app_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            app_card, text="Theme",
            font=ctk.CTkFont(size=12), text_color=T.TEXT_MUTED,
        ).grid(row=0, column=0, sticky="w", padx=T.PAD_MD, pady=T.PAD_MD)

        self._theme_var = ctk.StringVar(value=cfg.theme)
        ctk.CTkSegmentedButton(
            app_card,
            values=["dark", "light", "system"],
            variable=self._theme_var,
            fg_color=T.BG_INPUT,
            selected_color=T.ACCENT,
            selected_hover_color=T.ACCENT_HOVER,
            unselected_color=T.BG_INPUT,
            unselected_hover_color=T.BG_HOVER,
            text_color=T.TEXT,
            corner_radius=T.RADIUS_SM,
            command=self._apply_theme,
        ).grid(row=0, column=1, sticky="w", padx=T.PAD_MD)

        # ---- Behaviour -------------------------------------------
        self._section(scroll, "Behaviour", row=2)

        beh_card = GlassCard(scroll)
        beh_card.grid(row=3, column=0, sticky="ew", pady=(0, T.PAD_MD))
        beh_card.grid_columnconfigure(0, weight=1)

        self._notif_var = ctk.BooleanVar(value=cfg.show_notifications)
        self._minimized_var = ctk.BooleanVar(value=cfg.start_minimized)
        self._log_file_var = ctk.BooleanVar(value=cfg.log_to_file)

        for row_i, (attr, label) in enumerate([
            ("_notif_var",    "Show desktop notifications"),
            ("_minimized_var","Start minimized"),
            ("_log_file_var", "Write logs to file"),
        ]):
            ctk.CTkCheckBox(
                beh_card,
                text=label,
                variable=getattr(self, attr),
                checkbox_height=18, checkbox_width=18,
                corner_radius=4,
                fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER,
                text_color=T.TEXT,
            ).grid(row=row_i, column=0, sticky="w", padx=T.PAD_MD, pady=(T.PAD_SM if row_i == 0 else T.PAD_XS, T.PAD_XS))

        # Log level
        ctk.CTkLabel(
            beh_card, text="Log Level",
            font=ctk.CTkFont(size=12), text_color=T.TEXT_MUTED,
        ).grid(row=3, column=0, sticky="w", padx=T.PAD_MD, pady=(T.PAD_SM, 3))

        self._log_level_var = ctk.StringVar(value=cfg.log_level)
        ctk.CTkComboBox(
            beh_card,
            values=["DEBUG", "INFO", "WARNING", "ERROR"],
            variable=self._log_level_var,
            fg_color=T.BG_INPUT,
            border_color=T.BORDER,
            button_color=T.BORDER,
            button_hover_color=T.BORDER_BRIGHT,
            text_color=T.TEXT,
            dropdown_fg_color=T.BG_CARD,
            dropdown_hover_color=T.BG_HOVER,
            dropdown_text_color=T.TEXT,
            corner_radius=T.RADIUS_SM,
            width=180,
        ).grid(row=4, column=0, sticky="w", padx=T.PAD_MD, pady=(0, T.PAD_MD))

        # ---- Storage -------------------------------------------------
        self._section(scroll, "Storage", row=4)

        stor_card = GlassCard(scroll)
        stor_card.grid(row=5, column=0, sticky="ew", pady=(0, T.PAD_MD))
        stor_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            stor_card,
            text=f"Profiles directory:\n{self._app.profile_mgr.directory}",
            font=ctk.CTkFont(size=12),
            text_color=T.TEXT_MUTED,
            justify="left",
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=T.PAD_MD, pady=T.PAD_MD)

        ctk.CTkButton(
            stor_card,
            text="Open in File Manager",
            height=30, width=180,
            corner_radius=T.RADIUS_SM,
            fg_color="transparent",
            hover_color=T.BG_HOVER,
            text_color=T.ACCENT,
            border_color=T.ACCENT,
            border_width=1,
            command=self._open_profiles_dir,
        ).grid(row=1, column=0, sticky="w", padx=T.PAD_MD, pady=(0, T.PAD_MD))

        # ---- About ---------------------------------------------------
        self._section(scroll, "About", row=6)

        about_card = GlassCard(scroll)
        about_card.grid(row=7, column=0, sticky="ew", pady=(0, T.PAD_MD))

        ctk.CTkLabel(
            about_card,
            text=(
                "QSync  v1.0\n"
                "Cross-platform file synchronisation with glass UI.\n\n"
                "Supports local and SFTP (SSH) endpoints.\n"
                "Built with Python · customtkinter · paramiko · watchdog"
            ),
            font=ctk.CTkFont(size=12),
            text_color=T.TEXT_MUTED,
            justify="left",
            anchor="w",
        ).pack(anchor="w", padx=T.PAD_MD, pady=T.PAD_MD)

        # ---- Save button --------------------------------------------
        PrimaryButton(
            scroll, text="  Save Settings  ", command=self._save,
        ).grid(row=8, column=0, sticky="w", pady=T.PAD_MD)

    # ------------------------------------------------------------------

    @staticmethod
    def _section(parent, title: str, row: int) -> None:
        ctk.CTkLabel(
            parent,
            text=title.upper(),
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=T.TEXT_DIM,
            anchor="w",
        ).grid(row=row, column=0, sticky="w", pady=(T.PAD_MD, T.PAD_XS))

    # ------------------------------------------------------------------

    def _apply_theme(self, value: str) -> None:
        mode = value if value in ("dark", "light") else "system"
        ctk.set_appearance_mode(mode)

    def _save(self) -> None:
        cfg = self._app.config_mgr.config
        cfg.theme = self._theme_var.get()
        cfg.show_notifications = self._notif_var.get()
        cfg.start_minimized = self._minimized_var.get()
        cfg.log_to_file = self._log_file_var.get()
        cfg.log_level = self._log_level_var.get()
        self._app.config_mgr.save()

        from tkinter import messagebox
        messagebox.showinfo("Settings", "Settings saved successfully.")

    def _open_profiles_dir(self) -> None:
        import os
        import subprocess
        import sys

        path = self._app.profile_mgr.directory
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as exc:
            from tkinter import messagebox
            messagebox.showerror("Error", str(exc))
