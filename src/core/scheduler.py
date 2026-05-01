"""
Interval-based scheduler that triggers sync jobs for enabled profiles.
Uses a lightweight background thread with the 'schedule' library.
"""

from __future__ import annotations

import threading
import time
from typing import Callable, Dict, Optional

try:
    import schedule  # type: ignore[import]
    _HAS_SCHEDULE = True
except ImportError:
    _HAS_SCHEDULE = False


class SyncScheduler:
    """Runs a background thread that fires per-profile sync callbacks on schedule."""

    def __init__(self, on_trigger: Callable[[str], None]) -> None:
        self._on_trigger = on_trigger
        self._jobs: Dict[str, object] = {}   # profile_id → schedule.Job
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="queeksync-scheduler")
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    # ------------------------------------------------------------------
    def update_profile(self, profile) -> None:
        """Register or update the schedule for *profile*."""
        self.remove_profile(profile.id)

        if not (profile.enabled and profile.schedule.enabled):
            return

        minutes = max(1, profile.schedule.interval_minutes)
        pid = profile.id

        if _HAS_SCHEDULE:
            with self._lock:
                job = (
                    schedule.every(minutes)
                    .minutes.do(self._on_trigger, pid)
                )
                self._jobs[pid] = job
        else:
            # Fallback: simple interval thread
            self._fallback_schedule(pid, minutes)

    def remove_profile(self, profile_id: str) -> None:
        if not _HAS_SCHEDULE:
            return
        with self._lock:
            job = self._jobs.pop(profile_id, None)
            if job:
                try:
                    schedule.cancel_job(job)
                except Exception:
                    pass

    # ------------------------------------------------------------------
    def _loop(self) -> None:
        while not self._stop_event.is_set():
            if _HAS_SCHEDULE:
                with self._lock:
                    schedule.run_pending()
            self._stop_event.wait(timeout=30)

    def _fallback_schedule(self, profile_id: str, interval_minutes: int) -> None:
        """Simple threading.Timer fallback when 'schedule' is not installed."""
        def _fire():
            if not self._stop_event.is_set():
                self._on_trigger(profile_id)
                # Re-schedule
                self._fallback_schedule(profile_id, interval_minutes)

        t = threading.Timer(interval_minutes * 60, _fire)
        t.daemon = True
        t.start()
        self._jobs[profile_id] = t
