"""
File-system watcher that can trigger a sync when the source directory changes.
Uses the 'watchdog' library for cross-platform inotify/FSEvents/ReadDirectory support.
"""

from __future__ import annotations

import threading
import time
from typing import Callable, Dict, Optional


class DebounceTimer:
    """Call *func* after *delay* seconds of silence (resets on each trigger)."""

    def __init__(self, delay: float, func: Callable) -> None:
        self._delay = delay
        self._func = func
        self._timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()

    def trigger(self) -> None:
        with self._lock:
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(self._delay, self._fire)
            self._timer.daemon = True
            self._timer.start()

    def _fire(self) -> None:
        with self._lock:
            self._timer = None
        self._func()

    def cancel(self) -> None:
        with self._lock:
            if self._timer:
                self._timer.cancel()
                self._timer = None


class ProfileWatcher:
    """Watches a single profile's source directory for changes."""

    def __init__(
        self,
        profile_id: str,
        source_path: str,
        on_change: Callable[[str], None],
        debounce_seconds: float = 3.0,
    ) -> None:
        self.profile_id = profile_id
        self.source_path = source_path
        self.on_change = on_change
        self._debounce = DebounceTimer(debounce_seconds, self._fire)
        self._observer = None

    def start(self) -> None:
        try:
            from watchdog.observers import Observer  # type: ignore[import]
            from watchdog.events import FileSystemEventHandler  # type: ignore[import]

            watcher = self

            class _Handler(FileSystemEventHandler):
                def on_any_event(self, event):
                    if not event.is_directory:
                        watcher._debounce.trigger()

            self._observer = Observer()
            self._observer.schedule(_Handler(), self.source_path, recursive=True)
            self._observer.start()
        except Exception as exc:
            print(f"[Watcher] Could not start watcher for {self.source_path}: {exc}")

    def stop(self) -> None:
        self._debounce.cancel()
        if self._observer:
            try:
                self._observer.stop()
                self._observer.join(timeout=3)
            except Exception:
                pass
            self._observer = None

    def _fire(self) -> None:
        self.on_change(self.profile_id)


class WatcherManager:
    """Manages file watchers for all profiles that have watching enabled."""

    def __init__(self, on_change: Callable[[str], None]) -> None:
        self._on_change = on_change
        self._watchers: Dict[str, ProfileWatcher] = {}

    def update(self, profile) -> None:
        """Start or stop watcher for *profile* based on its schedule.enabled flag."""
        pid = profile.id
        currently_watching = pid in self._watchers

        # Only watch local sources
        wants_watch = (
            profile.enabled
            and profile.schedule.enabled
            and profile.source.type == "local"
            and profile.source.path
        )

        if wants_watch and not currently_watching:
            w = ProfileWatcher(pid, profile.source.path, self._on_change)
            w.start()
            self._watchers[pid] = w
        elif not wants_watch and currently_watching:
            self._watchers.pop(pid).stop()
        elif wants_watch and currently_watching:
            # If path changed, restart
            if self._watchers[pid].source_path != profile.source.path:
                self._watchers.pop(pid).stop()
                w = ProfileWatcher(pid, profile.source.path, self._on_change)
                w.start()
                self._watchers[pid] = w

    def remove(self, profile_id: str) -> None:
        if profile_id in self._watchers:
            self._watchers.pop(profile_id).stop()

    def stop_all(self) -> None:
        for w in list(self._watchers.values()):
            w.stop()
        self._watchers.clear()
