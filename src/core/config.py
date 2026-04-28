"""
Application-wide configuration (separate from per-sync profiles).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


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
            self._config_path = Path(base) / "QSync" / "config.json"
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

    def save(self) -> None:
        with open(self._config_path, "w", encoding="utf-8") as fh:
            json.dump(self.config.to_dict(), fh, indent=2, ensure_ascii=False)
