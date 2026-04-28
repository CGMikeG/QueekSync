"""
Core synchronisation engine.

Supports:
  - Local ↔ Local
  - Local ↔ SFTP (upload)
  - SFTP ↔ Local (download)
  - SFTP ↔ SFTP  (via temp file)

Sync modes:
  one_way  – copy source → destination (never delete)
  mirror   – one_way + delete files in destination that are absent from source
  two_way  – bidirectional: copy newer file to the other side
"""

from __future__ import annotations

import fnmatch
import hashlib
import os
import shutil
import tempfile
import threading
from datetime import datetime
from enum import Enum, auto
from typing import Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Status & event types
# ---------------------------------------------------------------------------

class SyncStatus(Enum):
    IDLE = auto()
    SCANNING = auto()
    SYNCING = auto()
    COMPLETED = auto()
    ERROR = auto()
    CANCELLED = auto()


class SyncEvent:
    """A single progress / log event emitted by the engine."""

    def __init__(
        self,
        kind: str,           # "info" | "copy" | "delete" | "skip" | "error" | "success" | "warning"
        message: str,
        rel_path: str = "",
        progress: float = 0.0,
        bytes_done: int = 0,
        bytes_total: int = 0,
    ) -> None:
        self.kind = kind
        self.message = message
        self.rel_path = rel_path
        self.progress = progress          # 0.0 – 1.0
        self.bytes_done = bytes_done
        self.bytes_total = bytes_total
        self.timestamp = datetime.now()

    def __repr__(self) -> str:  # noqa: D105
        return f"[{self.kind.upper()}] {self.message}"


# ---------------------------------------------------------------------------
# File info
# ---------------------------------------------------------------------------

class FileInfo:
    __slots__ = ("abs_path", "rel_path", "size", "mtime", "is_dir", "_checksum")

    def __init__(
        self,
        abs_path: str,
        rel_path: str,
        size: int,
        mtime: float,
        is_dir: bool = False,
    ) -> None:
        self.abs_path = abs_path
        self.rel_path = rel_path
        self.size = size
        self.mtime = mtime
        self.is_dir = is_dir
        self._checksum: Optional[str] = None

    def checksum(self) -> str:
        if self._checksum is None:
            h = hashlib.md5()
            with open(self.abs_path, "rb") as fh:
                for chunk in iter(lambda: fh.read(65536), b""):
                    h.update(chunk)
            self._checksum = h.hexdigest()
        return self._checksum


# ---------------------------------------------------------------------------
# Local filesystem
# ---------------------------------------------------------------------------

class LocalFS:
    """Operations on the local file system."""

    @staticmethod
    def scan(
        root: str,
        include_patterns: List[str],
        exclude_patterns: List[str],
    ) -> List[FileInfo]:
        root_path = os.path.abspath(root)
        if not os.path.exists(root_path):
            raise FileNotFoundError(f"Source path does not exist: {root_path}")

        files: List[FileInfo] = []
        for dirpath, dirnames, filenames in os.walk(root_path, followlinks=False):
            # Filter out excluded directories in-place
            dirnames[:] = [
                d for d in dirnames
                if not LocalFS._excluded(d, exclude_patterns, include_patterns)
            ]
            for name in filenames:
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, root_path).replace("\\", "/")
                if LocalFS._excluded(name, exclude_patterns, include_patterns, rel):
                    continue
                try:
                    st = os.stat(full)
                    files.append(FileInfo(full, rel, st.st_size, st.st_mtime))
                except OSError:
                    continue

            # Also record directories
            for name in dirnames:
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, root_path).replace("\\", "/")
                try:
                    st = os.stat(full)
                    files.append(FileInfo(full, rel, 0, st.st_mtime, is_dir=True))
                except OSError:
                    continue

        return files

    @staticmethod
    def _excluded(
        name: str,
        exclude: List[str],
        include: List[str],
        rel: str = "",
    ) -> bool:
        for pat in exclude:
            if fnmatch.fnmatch(name, pat) or (rel and fnmatch.fnmatch(rel, pat)):
                return True
        if include:
            for pat in include:
                if fnmatch.fnmatch(name, pat) or (rel and fnmatch.fnmatch(rel, pat)):
                    return False
            return True
        return False

    @staticmethod
    def copy_file(
        src: str,
        dst: str,
        preserve_timestamps: bool = True,
        progress_cb: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        total = os.path.getsize(src)
        done = 0
        with open(src, "rb") as fsrc, open(dst, "wb") as fdst:
            while True:
                chunk = fsrc.read(1 << 20)  # 1 MiB
                if not chunk:
                    break
                fdst.write(chunk)
                done += len(chunk)
                if progress_cb:
                    progress_cb(done, total)
        if preserve_timestamps:
            st = os.stat(src)
            os.utime(dst, (st.st_atime, st.st_mtime))

    @staticmethod
    def delete(path: str) -> None:
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
        else:
            os.remove(path)

    @staticmethod
    def makedirs(path: str) -> None:
        os.makedirs(path, exist_ok=True)


# ---------------------------------------------------------------------------
# SFTP filesystem
# ---------------------------------------------------------------------------

class SFTPFS:
    """Operations on a remote host via SSH/SFTP (requires paramiko)."""

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str = "",
        key_file: str = "",
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.key_file = key_file
        self._ssh = None
        self._sftp = None

    # ------------------------------------------------------------------
    def connect(self) -> None:
        import paramiko  # type: ignore[import]

        self._ssh = paramiko.SSHClient()
        self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        kwargs: dict = {
            "hostname": self.host,
            "port": self.port,
            "username": self.username,
            "timeout": 15,
        }
        if self.key_file:
            kwargs["key_filename"] = os.path.expanduser(self.key_file)
        elif self.password:
            kwargs["password"] = self.password
        self._ssh.connect(**kwargs)
        self._sftp = self._ssh.open_sftp()

    def disconnect(self) -> None:
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
        self._sftp = None
        self._ssh = None

    # ------------------------------------------------------------------
    def scan(
        self,
        root: str,
        include_patterns: List[str],
        exclude_patterns: List[str],
    ) -> List[FileInfo]:
        import stat as stat_mod  # noqa: PLC0415

        files: List[FileInfo] = []

        def _walk(remote_dir: str, rel_base: str) -> None:
            try:
                entries = self._sftp.listdir_attr(remote_dir)
            except Exception:
                return
            for entry in entries:
                rel = f"{rel_base}/{entry.filename}".lstrip("/")
                abs_path = f"{remote_dir}/{entry.filename}"
                is_dir = stat_mod.S_ISDIR(entry.st_mode)
                files.append(
                    FileInfo(abs_path, rel, entry.st_size or 0, entry.st_mtime or 0, is_dir)
                )
                if is_dir:
                    _walk(abs_path, rel)

        _walk(root.rstrip("/"), "")
        return files

    def upload(
        self,
        local: str,
        remote: str,
        preserve_timestamps: bool = True,
        progress_cb: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        self._mkdir_p(remote.rsplit("/", 1)[0])
        self._sftp.put(local, remote, callback=progress_cb)
        if preserve_timestamps:
            st = os.stat(local)
            self._sftp.utime(remote, (st.st_atime, st.st_mtime))

    def download(
        self,
        remote: str,
        local: str,
        preserve_timestamps: bool = True,
        progress_cb: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        os.makedirs(os.path.dirname(local), exist_ok=True)
        self._sftp.get(remote, local, callback=progress_cb)

    def delete(self, path: str, is_dir: bool = False) -> None:
        if is_dir:
            try:
                self._sftp.rmdir(path)
            except Exception:
                pass
        else:
            self._sftp.remove(path)

    def _mkdir_p(self, path: str) -> None:
        parts = [p for p in path.split("/") if p]
        current = "" if path.startswith("/") else "."
        if path.startswith("/"):
            current = ""
        for part in parts:
            current = f"{current}/{part}" if current else part
            try:
                self._sftp.mkdir(current)
            except Exception:
                pass  # already exists or no permission – try anyway


# ---------------------------------------------------------------------------
# Sync engine
# ---------------------------------------------------------------------------

class SyncEngine:
    """Drives a single sync run for one Profile."""

    def __init__(
        self,
        profile,
        event_cb: Optional[Callable[[SyncEvent], None]] = None,
    ) -> None:
        self.profile = profile
        self.event_cb = event_cb
        self.status = SyncStatus.IDLE
        self._cancel = False
        self._thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    def start(self, blocking: bool = False) -> None:
        if self.status == SyncStatus.SYNCING:
            return
        self._cancel = False
        if blocking:
            self._run()
        else:
            self._thread = threading.Thread(target=self._run, daemon=True, name="qsync-worker")
            self._thread.start()

    def cancel(self) -> None:
        self._cancel = True

    def is_running(self) -> bool:
        return self.status in (SyncStatus.SCANNING, SyncStatus.SYNCING)

    # ------------------------------------------------------------------
    def _emit(
        self,
        kind: str,
        message: str,
        rel_path: str = "",
        progress: float = 0.0,
        bytes_done: int = 0,
        bytes_total: int = 0,
    ) -> None:
        if self.event_cb:
            self.event_cb(
                SyncEvent(kind, message, rel_path, progress, bytes_done, bytes_total)
            )

    # ------------------------------------------------------------------
    def _run(self) -> None:
        self.status = SyncStatus.SCANNING
        try:
            self._emit("info", f"Starting: {self.profile.name}")
            src_cfg = self.profile.source
            dst_cfg = self.profile.destination

            src_fs = self._make_fs(src_cfg)
            dst_fs = self._make_fs(dst_cfg)

            if isinstance(src_fs, SFTPFS):
                self._emit("info", f"Connecting to source {src_cfg.host} …")
                src_fs.connect()
            if isinstance(dst_fs, SFTPFS):
                self._emit("info", f"Connecting to destination {dst_cfg.host} …")
                dst_fs.connect()

            try:
                self._sync(src_fs, src_cfg, dst_fs, dst_cfg)
            finally:
                if isinstance(src_fs, SFTPFS):
                    src_fs.disconnect()
                if isinstance(dst_fs, SFTPFS):
                    dst_fs.disconnect()

            if self._cancel:
                self.status = SyncStatus.CANCELLED
                self._emit("warning", "Sync cancelled by user.")
                self.profile.last_sync_status = "cancelled"
            else:
                self.status = SyncStatus.COMPLETED
                self._emit("success", "Sync completed successfully.")
                self.profile.last_sync = datetime.now().isoformat()
                self.profile.last_sync_status = "success"

        except Exception as exc:
            self.status = SyncStatus.ERROR
            self._emit("error", f"Sync failed: {exc}")
            self.profile.last_sync_status = "error"

    # ------------------------------------------------------------------
    def _make_fs(self, cfg):
        if cfg.type == "local":
            return LocalFS()
        if cfg.type == "sftp":
            return SFTPFS(cfg.host, cfg.port, cfg.username, cfg.password, cfg.key_file)
        raise ValueError(f"Unknown endpoint type: {cfg.type!r}")

    # ------------------------------------------------------------------
    def _sync(self, src_fs, src_cfg, dst_fs, dst_cfg) -> None:
        opts = self.profile.options
        flt = self.profile.filters

        # ---- scan -------------------------------------------------
        self._emit("info", "Scanning source …")
        src_files = src_fs.scan(src_cfg.path, flt.include_patterns, flt.exclude_patterns)
        if self._cancel:
            return

        self._emit("info", "Scanning destination …")
        try:
            dst_files = dst_fs.scan(dst_cfg.path, [], [])
        except FileNotFoundError:
            dst_files = []
        if self._cancel:
            return

        src_map: Dict[str, FileInfo] = {f.rel_path: f for f in src_files}
        dst_map: Dict[str, FileInfo] = {f.rel_path: f for f in dst_files}

        file_entries = [(p, f) for p, f in src_map.items() if not f.is_dir]
        total = len(file_entries)
        done = 0

        self.status = SyncStatus.SYNCING
        self._emit("info", f"Found {total} file(s) in source.")

        # ---- copy source → destination ----------------------------
        for rel, src_f in file_entries:
            if self._cancel:
                return

            dst_f = dst_map.get(rel)
            should_copy = self._needs_copy(src_f, dst_f, opts)

            if should_copy:
                src_abs = src_f.abs_path
                dst_abs = self._join(dst_cfg, rel)
                self._emit("copy", f"Copying  {rel}", rel, done / max(total, 1))
                try:
                    self._transfer(src_fs, src_abs, dst_fs, dst_abs, opts.preserve_timestamps, rel)
                except Exception as exc:
                    self._emit("error", f"Copy failed [{rel}]: {exc}", rel)
            else:
                self._emit("skip", f"Up-to-date {rel}", rel)

            done += 1
            self._emit("info", f"Progress: {done}/{total}", progress=done / max(total, 1))

        # ---- delete extras (mirror mode) -------------------------
        if opts.mode == "mirror" or opts.delete_extra:
            for rel, dst_f in list(dst_map.items()):
                if self._cancel:
                    return
                if rel not in src_map:
                    dst_abs = self._join(dst_cfg, rel)
                    self._emit("delete", f"Deleting {rel}", rel)
                    try:
                        dst_fs.delete(dst_abs, dst_f.is_dir)
                    except Exception as exc:
                        self._emit("error", f"Delete failed [{rel}]: {exc}", rel)

        # ---- two-way: copy dst-only files back to source ----------
        if opts.mode == "two_way":
            dst_only = [(r, f) for r, f in dst_map.items() if r not in src_map and not f.is_dir]
            for rel, dst_f in dst_only:
                if self._cancel:
                    return
                src_abs = self._join(src_cfg, rel)
                self._emit("copy", f"Two-way copy ← {rel}", rel)
                try:
                    self._transfer(dst_fs, dst_f.abs_path, src_fs, src_abs, opts.preserve_timestamps, rel)
                except Exception as exc:
                    self._emit("error", f"Two-way copy failed [{rel}]: {exc}", rel)

    # ------------------------------------------------------------------
    @staticmethod
    def _needs_copy(src: FileInfo, dst: Optional[FileInfo], opts) -> bool:
        if dst is None:
            return True
        if opts.verify_checksums:
            try:
                return src.checksum() != dst.checksum()
            except Exception:
                return True
        # Size or mtime differ
        if src.size != dst.size:
            return True
        if abs(src.mtime - dst.mtime) > 2:
            return True
        return False

    @staticmethod
    def _join(cfg, rel: str) -> str:
        if cfg.type == "sftp":
            return f"{cfg.path.rstrip('/')}/{rel}"
        return os.path.join(cfg.path, rel.replace("/", os.sep))

    @staticmethod
    def _transfer(
        src_fs,
        src_abs: str,
        dst_fs,
        dst_abs: str,
        preserve_ts: bool,
        rel: str,
    ) -> None:
        if isinstance(src_fs, LocalFS) and isinstance(dst_fs, LocalFS):
            LocalFS.copy_file(src_abs, dst_abs, preserve_ts)

        elif isinstance(src_fs, LocalFS) and isinstance(dst_fs, SFTPFS):
            dst_fs.upload(src_abs, dst_abs, preserve_ts)

        elif isinstance(src_fs, SFTPFS) and isinstance(dst_fs, LocalFS):
            src_fs.download(src_abs, dst_abs, preserve_ts)

        elif isinstance(src_fs, SFTPFS) and isinstance(dst_fs, SFTPFS):
            # SFTP → SFTP via temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".qsync_tmp") as tf:
                tmp = tf.name
            try:
                src_fs.download(src_abs, tmp)
                dst_fs.upload(tmp, dst_abs, preserve_ts)
            finally:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
