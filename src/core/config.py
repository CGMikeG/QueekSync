"""
Application-wide configuration (separate from per-sync profiles).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


APP_DIR_NAME = "QueekSync"
LEGACY_APP_DIR_NAME = "QSync"


@dataclass
class AppConfig:
    theme: str = "dark"                   # "dark" | "light" | "system"
    accent_color: str = "blue"            # customtkinter colour theme name
    start_minimized: bool = False
    minimize_to_tray: bool = False
    show_notifications: bool = True
    log_level: str = "INFO"               # "DEBUG" | "INFO" | "WARNING" | "ERROR"
    log_to_file: bool = True
    max_log_lines: int = 2000
    window_width: int = 1200
    window_height: int = 750

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AppConfig":
        valid = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid)


class ConfigManager:
    """Reads and writes the global application configuration file."""

    def __init__(self, config_dir: Optional[str] = None) -> None:
        if config_dir is None:
            if os.name == "nt":
                base = os.environ.get("APPDATA", os.path.expanduser("~"))
            else:
                base = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
            self._config_path = self._resolve_config_path(Path(base))
        else:
            self._config_path = Path(config_dir) / "config.json"

        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config = self._load()

    def _load(self) -> AppConfig:
        if self._config_path.exists():
            try:
                with open(self._config_path, "r", encoding="utf-8") as fh:
                    return AppConfig.from_dict(json.load(fh))
            except Exception as exc:
                print(f"[ConfigManager] Failed to load config: {exc}")
        return AppConfig()

    @staticmethod
    def _resolve_config_path(base: Path) -> Path:
        new_path = base / APP_DIR_NAME / "config.json"
        legacy_path = base / LEGACY_APP_DIR_NAME / "config.json"
        if new_path.exists() or not legacy_path.exists():
            return new_path
        return legacy_path

    def save(self) -> None:
        with open(self._config_path, "w", encoding="utf-8") as fh:
            json.dump(self.config.to_dict(), fh, indent=2, ensure_ascii=False)
