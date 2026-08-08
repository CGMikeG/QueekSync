"""
Settings panel – application-wide preferences.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

from ui import theme as T
from ui.components import GlassCard, PrimaryButton, attach_tooltip

if TYPE_CHECKING:
    from ui.app import QueekSyncApp


class SettingsPanel(ctk.CTkFrame):
    def __init__(self, master, app: "QueekSyncApp", **kw) -> None:
        kw.setdefault("fg_color", "transparent")
        super().__init__(master, **kw)
        self._app = app
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build()

    def _on_mousewheel(self, event) -> None:
        """Route mouse wheel events to the scrollable frame."""
        try:
            for child in self.winfo_children():
                if isinstance(child, ctk.CTkScrollableFrame):
                    delta = 1 if event.num == 5 else -1
                    if hasattr(event, 'delta'):
                        delta = -int(event.delta / 6) if event.delta > 0 else 1
                    
                    if hasattr(child, '_parent_canvas'):
                        canvas = child._parent_canvas
                        current = canvas.yview()
                        if current != (0.0, 1.0):
                            canvas.yview_scroll(delta, "units")
                    return
        except:
            pass

    def _build(self) -> None:
        scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=T.BORDER,
            scrollbar_button_hover_color=T.BORDER_BRIGHT,
        )
        scroll.grid(row=0, column=0, sticky="nsew", padx=T.PAD_LG, pady=T.PAD_MD)
        scroll.grid_columnconfigure(0, weight=1)

        # Bind mouse wheel
        scroll.bind("<MouseWheel>", self._on_mousewheel)
        scroll.bind("<Button-4>", self._on_mousewheel)
        scroll.bind("<Button-5>", self._on_mousewheel)

        cfg = self._app.config_mgr.config

        # ---- Appearance -------------------------------------------
        self._section(scroll, "Appearance", row=0)

        app_card = GlassCard(scroll)
        app_card.grid(row=1, column=0, sticky="ew", pady=(0, T.PAD_MD))
        app_card.grid_columnconfigure(1, weight=1)

        theme_label = ctk.CTkLabel(
            app_card, text="Theme",
            font=ctk.CTkFont(size=12), text_color=T.TEXT_MUTED,
        )
        theme_label.grid(row=0, column=0, sticky="w", padx=T.PAD_MD, pady=T.PAD_MD)

        self._theme_var = ctk.StringVar(value=cfg.theme)
        theme_seg = ctk.CTkSegmentedButton(
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
        )
        theme_seg.grid(row=0, column=1, sticky="w", padx=T.PAD_MD)
        attach_tooltip(
            theme_label,
            theme_seg,
            text="Choose the app appearance mode. Example: dark for low-light setups, light for bright rooms, or system to follow your operating system theme automatically."
        )

        # ---- Behaviour -------------------------------------------
        self._section(scroll, "Behaviour", row=2)

        beh_card = GlassCard(scroll)
        beh_card.grid(row=3, column=0, sticky="ew", pady=(0, T.PAD_MD))
        beh_card.grid_columnconfigure(1, weight=1)

        notif_label = ctk.CTkLabel(
            beh_card, text="Show Notifications",
            font=ctk.CTkFont(size=12), text_color=T.TEXT_MUTED,
        )
        notif_label.grid(row=0, column=0, sticky="w", padx=T.PAD_MD, pady=T.PAD_MD)

        self._notif_var = ctk.BooleanVar(value=cfg.show_notifications)
        notif_cb = ctk.CTkCheckBox(
            beh_card, variable=self._notif_var,
            fg_color=T.ACCENT,
            hover_color=T.ACCENT_HOVER,
            border_color=T.BORDER,
        )
        notif_cb.grid(row=0, column=1, padx=T.PAD_MD)
        attach_tooltip(notif_label, notif_cb, text="Enable or disable desktop notifications for sync events.")

        min_label = ctk.CTkLabel(
            beh_card, text="Start Minimized",
            font=ctk.CTkFont(size=12), text_color=T.TEXT_MUTED,
        )
        min_label.grid(row=1, column=0, sticky="w", padx=T.PAD_MD, pady=(T.PAD_SM, 0))

        self._minimized_var = ctk.BooleanVar(value=cfg.start_minimized)
        min_cb = ctk.CTkCheckBox(
            beh_card, variable=self._minimized_var,
            fg_color=T.ACCENT,
            hover_color=T.ACCENT_HOVER,
            border_color=T.BORDER,
        )
        min_cb.grid(row=1, column=1, padx=T.PAD_MD, pady=(T.PAD_SM, 0))
        attach_tooltip(min_label, min_cb, text="Start the application minimized to the system tray on login.")

        # ---- Logging -------------------------------------------
        self._section(scroll, "Logging", row=4)

        log_card = GlassCard(scroll)
        log_card.grid(row=5, column=0, sticky="ew", pady=(0, T.PAD_MD))
        log_card.grid_columnconfigure(1, weight=1)

        log_level_label = ctk.CTkLabel(
            log_card, text="Log Level",
            font=ctk.CTkFont(size=12), text_color=T.TEXT_MUTED,
        )
        log_level_label.grid(row=0, column=0, sticky="w", padx=T.PAD_MD, pady=T.PAD_MD)

        self._log_level_var = ctk.StringVar(value=cfg.log_level)
        log_seg = ctk.CTkSegmentedButton(
            log_card,
            values=["DEBUG", "INFO", "WARNING", "ERROR"],
            variable=self._log_level_var,
            fg_color=T.BG_INPUT,
            selected_color=T.ACCENT,
            selected_hover_color=T.ACCENT_HOVER,
            unselected_color=T.BG_INPUT,
            unselected_hover_color=T.BG_HOVER,
            text_color=T.TEXT,
            corner_radius=T.RADIUS_SM,
        )
        log_seg.grid(row=0, column=1, sticky="w", padx=T.PAD_MD)
        attach_tooltip(log_level_label, log_seg, text="Set the verbosity of the application log.")

        open_log_btn = ctk.CTkButton(
            log_card, text="Open Log File", width=120, height=32,
            corner_radius=T.RADIUS_SM,
            fg_color=T.BG_INPUT,
            hover_color=T.BG_HOVER,
            text_color=T.TEXT,
            border_color=T.BORDER,
            border_width=1,
            command=self._open_log_file,
        )
        open_log_btn.grid(row=1, column=0, sticky="w", padx=T.PAD_MD, pady=(T.PAD_SM, 0))
        attach_tooltip(
            open_log_btn,
            text="Open the log.txt file that captures sync errors and progress."
        )

        # ---- Storage -------------------------------------------
        self._section(scroll, "Storage", row=6)

        stor_card = GlassCard(scroll)
        stor_card.grid(row=7, column=0, sticky="ew", pady=(0, T.PAD_MD))
        stor_card.grid_columnconfigure(0, weight=1)

        log_path = self._app.get_log_file_path()
        storage_label = ctk.CTkLabel(
            stor_card,
            text=(
                f"Profiles directory:\n{self._app.profile_mgr.directory}\n\n"
                + (f"Log file:\n{log_path}" if log_path else "Log file:\n(disabled or unavailable)")
            ),
            font=ctk.CTkFont(size=12),
            text_color=T.TEXT_MUTED,
            justify="left",
            anchor="w",
        )
        storage_label.grid(row=0, column=0, sticky="w", padx=T.PAD_MD, pady=T.PAD_MD)

        open_dir_btn = ctk.CTkButton(
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
        )
        open_dir_btn.grid(row=1, column=0, sticky="w", padx=T.PAD_MD, pady=(0, T.PAD_MD))

        # ---- About -------------------------------------------
        self._section(scroll, "About", row=8)

        about_card = GlassCard(scroll)
        about_card.grid(row=9, column=0, sticky="ew", pady=(0, T.PAD_MD))

        ctk.CTkLabel(
            about_card,
            text=(
                "QueekSync\n"
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
        save_btn = PrimaryButton(
            scroll, text="  Save Settings  ", command=self._save,
        )
        save_btn.grid(row=10, column=0, sticky="w", pady=T.PAD_MD)
        attach_tooltip(
            save_btn,
            text="Apply and save these global preferences."
        )

        # CRITICAL: Update root to calculate canvas scrollregion AFTER content is added
        self._app.root.update_idletasks()

    @staticmethod
    def _section(parent, title: str, row: int) -> None:
        ctk.CTkLabel(
            parent,
            text=title.upper(),
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=T.TEXT_DIM,
            anchor="w",
        ).grid(row=row, column=0, sticky="w", pady=(T.PAD_MD, T.PAD_XS))

    def _apply_theme(self, value: str) -> None:
        mode = value if value in ("dark", "light") else "system"
        ctk.set_appearance_mode(mode)

    def _save(self) -> None:
        cfg = self._app.config_mgr.config
        cfg.theme = self._theme_var.get()
        cfg.show_notifications = self._notif_var.get()
        cfg.start_minimized = self._minimized_var.get()
        cfg.log_to_file = True
        cfg.log_level = self._log_level_var.get()
        self._app.config_mgr.save()
        self._app.refresh_file_logging()
        self._app.refresh_panel("settings")

        from tkinter import messagebox
        messagebox.showinfo("Settings", "Settings saved successfully.", parent=self._app.root)

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

    def _open_log_file(self) -> None:
        import os
        import subprocess
        import sys

        path = self._app.get_log_file_path()
        if not path:
            return
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
