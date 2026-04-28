"""
Dashboard panel – overview of all profiles with quick-sync cards.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Dict, List

import customtkinter as ctk

from ui import theme as T
from ui.components import GlassCard, PrimaryButton, Separator, StatTile, StatusBadge

if TYPE_CHECKING:
    from ui.app import QSyncApp


class ProfileCard(GlassCard):
    """Card widget showing a single profile's summary."""

    def __init__(self, master, profile, app: "QSyncApp", **kw) -> None:
        kw.setdefault("width", 300)
        kw.setdefault("height", 190)
        super().__init__(master, **kw)
        self.grid_propagate(False)
        self.pack_propagate(False)

        self._profile = profile
        self._app = app
        self._build()

    def _build(self) -> None:
        p = self._profile
        pad = 18

        # ── Colour accent bar (left edge, fixed 4 px wide) ─────────────
        ctk.CTkFrame(
            self,
            fg_color=p.color,
            corner_radius=0,
            width=4,
        ).place(x=0, y=0, relheight=1.0)

        # ── Main content frame (sits to the right of accent bar) ───────
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.place(x=pad, y=0, relwidth=1.0, relheight=1.0)
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(3, weight=1)  # spacer before buttons

        # Name + status row
        top = ctk.CTkFrame(content, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", pady=(14, 2), padx=(0, pad))
        top.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            top,
            text=p.name,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=T.TEXT,
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        StatusBadge(top, status=p.last_sync_status).grid(row=0, column=1, sticky="e", padx=4)

        # Paths
        src_label = p.source.display_label() or "(source not set)"
        dst_label = p.destination.display_label() or "(destination not set)"

        paths = ctk.CTkFrame(content, fg_color="transparent")
        paths.grid(row=1, column=0, sticky="ew", padx=(0, pad))

        ctk.CTkLabel(
            paths,
            text=f"▲  {src_label}",
            font=ctk.CTkFont(size=11),
            text_color=T.TEXT_MUTED,
            anchor="w",
            wraplength=240,
        ).pack(anchor="w")

        ctk.CTkLabel(
            paths,
            text=f"▼  {dst_label}",
            font=ctk.CTkFont(size=11),
            text_color=T.TEXT_MUTED,
            anchor="w",
            wraplength=240,
        ).pack(anchor="w")

        # Last sync + mode
        meta = ctk.CTkFrame(content, fg_color="transparent")
        meta.grid(row=2, column=0, sticky="ew", pady=(4, 0), padx=(0, pad))

        # Last sync
        last_sync_txt = "Never"
        if p.last_sync:
            try:
                dt = datetime.fromisoformat(p.last_sync)
                last_sync_txt = dt.strftime("%Y-%m-%d  %H:%M")
            except Exception:
                last_sync_txt = p.last_sync

        ctk.CTkLabel(
            meta,
            text=f"Last sync:  {last_sync_txt}",
            font=ctk.CTkFont(size=11),
            text_color=T.TEXT_DIM,
            anchor="w",
        ).pack(anchor="w")

        # Mode badge
        mode_map = {"one_way": "→ One-way", "mirror": "↔ Mirror", "two_way": "⇄ Two-way"}
        ctk.CTkLabel(
            meta,
            text=mode_map.get(p.options.mode, p.options.mode),
            font=ctk.CTkFont(size=11),
            text_color=T.ACCENT,
            anchor="w",
        ).pack(anchor="w")

        # Buttons
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.grid(row=4, column=0, sticky="ew", pady=(6, 10), padx=(0, pad))

        PrimaryButton(
            btn_frame,
            text="▶  Sync Now",
            height=30,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._sync,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            btn_frame,
            text="✎  Edit",
            height=30,
            width=70,
            corner_radius=T.RADIUS_MD,
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            hover_color=T.BG_HOVER,
            text_color=T.TEXT_MUTED,
            border_color=T.BORDER,
            border_width=1,
            command=self._edit,
        ).pack(side="left")

    def _sync(self) -> None:
        self._app.start_sync(self._profile.id)

    def _edit(self) -> None:
        from ui.profile_editor import ProfileEditorDialog
        dlg = ProfileEditorDialog(
            self._app.root,
            profile=self._profile,
            on_save=self._on_save,
        )
        dlg.focus()

    def _on_save(self, profile) -> None:
        self._app.profile_mgr.save(profile)
        self._app._scheduler.update_profile(profile)
        self._app._watcher_mgr.update(profile)
        self._app.refresh_panel("dashboard")
        self._app.refresh_panel("profiles")


class DashboardPanel(ctk.CTkFrame):
    def __init__(self, master, app: "QSyncApp", **kw) -> None:
        kw.setdefault("fg_color", "transparent")
        super().__init__(master, **kw)
        self._app = app
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build()

    def _build(self) -> None:
        profiles = self._app.profile_mgr.all()
        total = len(profiles)
        active = sum(1 for p in profiles if p.last_sync_status == "running")
        ok = sum(1 for p in profiles if p.last_sync_status == "success")

        # ---- Stats row -----------------------------------------------
        stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        stats_frame.grid(row=0, column=0, sticky="ew", padx=T.PAD_LG, pady=(T.PAD_LG, 0))

        StatTile(stats_frame, "Total Profiles", str(total), T.ACCENT).pack(side="left", padx=(0, T.CARD_GAP))
        StatTile(stats_frame, "Running",        str(active), T.WARNING).pack(side="left", padx=(0, T.CARD_GAP))
        StatTile(stats_frame, "Last OK",        str(ok),    T.SUCCESS).pack(side="left")

        # Quick-add button
        ctk.CTkButton(
            stats_frame,
            text="＋  New Profile",
            corner_radius=T.RADIUS_MD,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=T.ACCENT,
            hover_color=T.ACCENT_HOVER,
            text_color="#ffffff",
            height=38,
            width=150,
            command=self._new_profile,
        ).pack(side="right")

        Separator(self, "horizontal").grid(
            row=1, column=0, sticky="ew", padx=T.PAD_LG, pady=T.PAD_SM
        )

        # ---- Scrollable profile cards --------------------------------
        scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=T.BORDER,
            scrollbar_button_hover_color=T.BORDER_BRIGHT,
        )
        scroll.grid(row=2, column=0, sticky="nsew", padx=T.PAD_LG, pady=T.PAD_SM)
        self.grid_rowconfigure(2, weight=1)

        if not profiles:
            ctk.CTkLabel(
                scroll,
                text="No profiles yet.\nClick  ＋ New Profile  to get started.",
                font=ctk.CTkFont(size=14),
                text_color=T.TEXT_DIM,
                justify="center",
            ).pack(expand=True, pady=80)
            return

        # 3-column responsive grid of cards
        col_count = 3
        for idx, profile in enumerate(sorted(profiles, key=lambda p: p.name)):
            row_ = idx // col_count
            col_ = idx % col_count
            scroll.grid_columnconfigure(col_, weight=1, pad=T.CARD_GAP)
            card = ProfileCard(scroll, profile, self._app)
            card.grid(row=row_, column=col_, padx=T.CARD_GAP // 2, pady=T.CARD_GAP // 2, sticky="nsew")

    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Rebuild card grid after data changes."""
        for child in self.winfo_children():
            child.destroy()
        self._build()

    def _new_profile(self) -> None:
        from core.profile import Profile
        from ui.profile_editor import ProfileEditorDialog

        new_p = Profile()
        dlg = ProfileEditorDialog(
            self._app.root,
            profile=new_p,
            on_save=self._on_new_save,
        )
        dlg.focus()

    def _on_new_save(self, profile) -> None:
        self._app.profile_mgr.save(profile)
        self._app._scheduler.update_profile(profile)
        self._app._watcher_mgr.update(profile)
        self.refresh()
        self._app.refresh_panel("profiles")
