"""
Profile data models and persistence manager.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class EndpointConfig:
    """Describes one side of a sync pair (local path or SFTP connection)."""

    type: str = "local"          # "local" | "sftp"
    path: str = ""
    host: str = ""
    port: int = 22
    username: str = ""
    password: str = ""           # stored in plaintext – warn user
    key_file: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "EndpointConfig":
        valid = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid)

    def display_label(self) -> str:
        if self.type == "sftp":
            return f"{self.username}@{self.host}:{self.port}  {self.path}"
        return self.path or "(not set)"


@dataclass
class SyncOptions:
    """Behavioural settings for the sync operation."""

    mode: str = "one_way"               # "one_way" | "mirror" | "two_way"
    delete_extra: bool = False          # remove files that no longer exist in source
    preserve_timestamps: bool = True
    follow_symlinks: bool = False
    verify_checksums: bool = False
    bandwidth_limit_kbps: int = 0       # 0 = unlimited

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SyncOptions":
        valid = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid)


@dataclass
class ScheduleConfig:
    """Automatic scheduling settings for a profile."""

    enabled: bool = False
    interval_minutes: int = 60

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ScheduleConfig":
        valid = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid)


@dataclass
class FilterConfig:
    """File include / exclude filter patterns (fnmatch style)."""

    include_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(
        default_factory=lambda: ["*.tmp", "*.log", ".DS_Store", "Thumbs.db", "__pycache__"]
    )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "FilterConfig":
        obj = cls()
        if "include_patterns" in data:
            obj.include_patterns = list(data["include_patterns"])
        if "exclude_patterns" in data:
            obj.exclude_patterns = list(data["exclude_patterns"])
        return obj


# Accent colour palette offered in the UI
PROFILE_COLOURS = [
    "#3b82f6",  # Blue
    "#8b5cf6",  # Purple
    "#14b8a6",  # Teal
    "#22c55e",  # Green
    "#f97316",  # Orange
    "#ef4444",  # Red
    "#ec4899",  # Pink
    "#eab308",  # Yellow
]


@dataclass
class Profile:
    """A complete sync profile."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "New Profile"
    description: str = ""
    color: str = "#3b82f6"
    enabled: bool = True

    source: EndpointConfig = field(default_factory=EndpointConfig)
    destination: EndpointConfig = field(default_factory=EndpointConfig)
    options: SyncOptions = field(default_factory=SyncOptions)
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    filters: FilterConfig = field(default_factory=FilterConfig)

    last_sync: Optional[str] = None
    last_sync_status: str = "never"   # "never" | "success" | "error" | "running"

    # ------------------------------------------------------------------ #

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "color": self.color,
            "enabled": self.enabled,
            "source": self.source.to_dict(),
            "destination": self.destination.to_dict(),
            "options": self.options.to_dict(),
            "schedule": self.schedule.to_dict(),
            "filters": self.filters.to_dict(),
            "last_sync": self.last_sync,
            "last_sync_status": self.last_sync_status,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Profile":
        p = cls()
        p.id = data.get("id", str(uuid.uuid4()))
        p.name = data.get("name", "New Profile")
        p.description = data.get("description", "")
        p.color = data.get("color", "#3b82f6")
        p.enabled = data.get("enabled", True)
        p.source = EndpointConfig.from_dict(data.get("source", {}))
        p.destination = EndpointConfig.from_dict(data.get("destination", {}))
        p.options = SyncOptions.from_dict(data.get("options", {}))
        p.schedule = ScheduleConfig.from_dict(data.get("schedule", {}))
        p.filters = FilterConfig.from_dict(data.get("filters", {}))
        p.last_sync = data.get("last_sync")
        p.last_sync_status = data.get("last_sync_status", "never")
        return p

    def duplicate(self) -> "Profile":
        copy = Profile.from_dict(self.to_dict())
        copy.id = str(uuid.uuid4())
        copy.name = f"{self.name} (Copy)"
        copy.last_sync = None
        copy.last_sync_status = "never"
        return copy


# ---------------------------------------------------------------------------
# Profile Manager
# ---------------------------------------------------------------------------

class ProfileManager:
    """CRUD interface for Profile objects backed by per-profile JSON files."""

    def __init__(self, profiles_dir: Optional[str] = None) -> None:
        if profiles_dir is None:
            if os.name == "nt":
                base = os.environ.get("APPDATA", os.path.expanduser("~"))
            else:
                base = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
            self.profiles_dir = Path(base) / "QSync" / "profiles"
        else:
            self.profiles_dir = Path(profiles_dir)

        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self._profiles: Dict[str, Profile] = {}
        self._load_all()

    # ------------------------------------------------------------------

    def _load_all(self) -> None:
        self._profiles.clear()
        for json_file in self.profiles_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                profile = Profile.from_dict(data)
                self._profiles[profile.id] = profile
            except Exception as exc:
                print(f"[ProfileManager] Failed to load {json_file}: {exc}")

    def save(self, profile: Profile) -> None:
        self._profiles[profile.id] = profile
        dest = self.profiles_dir / f"{profile.id}.json"
        with open(dest, "w", encoding="utf-8") as fh:
            json.dump(profile.to_dict(), fh, indent=2, ensure_ascii=False)

    def delete(self, profile_id: str) -> None:
        self._profiles.pop(profile_id, None)
        path = self.profiles_dir / f"{profile_id}.json"
        if path.exists():
            path.unlink()

    def get(self, profile_id: str) -> Optional[Profile]:
        return self._profiles.get(profile_id)

    def all(self) -> List[Profile]:
        return list(self._profiles.values())

    def duplicate(self, profile_id: str) -> Optional[Profile]:
        original = self.get(profile_id)
        if original is None:
            return None
        copy = original.duplicate()
        self.save(copy)
        return copy

    @property
    def directory(self) -> str:
        return str(self.profiles_dir)
