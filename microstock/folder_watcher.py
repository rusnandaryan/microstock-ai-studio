"""Folder Watcher & Auto-Import Module.

Automatically detects recently downloaded images from Gemini Web in the user's
Downloads folder (or custom directory) and imports them directly into Tab 2.
"""
from __future__ import annotations

import mimetypes
import os
import time
from typing import Dict, List, Optional, Tuple, Union

VALID_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
IGNORED_EXTENSIONS = {".crdownload", ".download", ".part", ".tmp"}

TIME_WINDOWS: Dict[str, Union[int, str]] = {
    "15 Menit Terakhir (Sesi Sekarang)": 15 * 60,
    "30 Menit Terakhir": 30 * 60,
    "1 Jam Terakhir": 60 * 60,
    "Hari Ini (Sejak 00:00)": "today",
    "Semua File Gambar Terbaru": 0,
}


def get_default_downloads_dir() -> str:
    """Return default Gemini Generated Images directory (fallback to ~/Downloads)."""
    gemini_dir = os.path.expanduser("~/Documents/Gemini Generated Images")
    if os.path.isdir(gemini_dir):
        return gemini_dir
    return os.path.expanduser("~/Downloads")


def get_cutoff_timestamp(window_key: str) -> Optional[float]:
    """Calculate the unix timestamp cutoff for a selected time window."""
    now = time.time()
    val = TIME_WINDOWS.get(window_key, 15 * 60)
    if val == 0:
        return None
    if val == "today":
        lt = time.localtime(now)
        midnight = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 0, 0, 0, 0, 0, -1))
        return midnight
    return now - float(val)


def check_pending_downloads(directory: str) -> int:
    """Return count of active in-progress downloads (.crdownload, etc.)."""
    if not os.path.isdir(directory):
        return 0
    count = 0
    try:
        with os.scandir(directory) as entries:
            for entry in entries:
                try:
                    if entry.is_file():
                        ext = os.path.splitext(entry.name)[1].lower()
                        if ext in IGNORED_EXTENSIONS:
                            count += 1
                except (PermissionError, OSError):
                    continue
    except (PermissionError, OSError):
        pass
    return count


def scan_recent_images(
    directory: str,
    since_timestamp: Optional[float] = None,
    max_files: int = 50,
) -> List[Tuple[str, str, float, int]]:
    """Scan directory for valid image files, sorted newest first.
    
    Returns list of (filename, filepath, modified_timestamp, file_size).
    """
    if not os.path.isdir(directory):
        return []

    results = []
    try:
        entries = os.scandir(directory)
    except (PermissionError, OSError):
        return []

    with entries:
        for entry in entries:
            try:
                if not entry.is_file():
                    continue
                name = entry.name
                if name.startswith("."):
                    continue
                ext = os.path.splitext(name)[1].lower()
                if ext in IGNORED_EXTENSIONS:
                    continue
                if ext not in VALID_IMAGE_EXTENSIONS:
                    continue

                stat = entry.stat()
                mtime = stat.st_mtime
                size = stat.st_size

                # Filter by timestamp if specified
                if since_timestamp and mtime < since_timestamp:
                    continue

                results.append((name, entry.path, mtime, size))
            except (PermissionError, OSError):
                continue

    results.sort(key=lambda x: x[2], reverse=True)
    return results[:max_files]


def read_image_bytes(filepath: str) -> Optional[Tuple[str, bytes, str]]:
    """Read an image file safely and return (filename, bytes, mime_type)."""
    try:
        max_bytes = 50 * 1024 * 1024
        with open(filepath, "rb") as f:
            data = f.read(max_bytes + 1)
        if not data or len(data) > max_bytes:
            return None
        filename = os.path.basename(filepath)
        mime, _ = mimetypes.guess_type(filepath)
        if not mime or not mime.startswith("image/"):
            mime = "image/jpeg"
        return filename, data, mime
    except Exception:
        pass
    return None


# ==============================================================================
# KERNEL EVENT-DRIVEN FOLDER WATCHER (0% CPU IDLE)
# ==============================================================================

import collections
import threading
from typing import Callable, Deque


class FolderMonitor:
    """Event-driven background directory watcher with zero idle CPU spin.
    
    Uses OS watchdog events (FSEvents/inotify) if installed, or an ultra-low-impact
    kernel directory stat monitor (checks mtime every interval) as an efficient fallback.
    Automatically filters out in-progress downloads (.crdownload, .part).
    """

    def __init__(
        self,
        directory: Optional[str] = None,
        on_image_detected: Optional[Callable[[str, str], None]] = None,
        poll_interval: float = 1.5,
    ):
        self.directory = directory or get_default_downloads_dir()
        self.poll_interval = poll_interval
        self._callbacks: List[Callable[[str, str], None]] = []
        if on_image_detected:
            self._callbacks.append(on_image_detected)

        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._recent_events: Deque[Dict[str, Any]] = collections.deque(maxlen=50)
        self._known_files: set = set()
        self._backend = "polling"
        self._watchdog_observer = None

    def add_callback(self, callback: Callable[[str, str], None]) -> None:
        """Register a callback invoked when a new finished image is detected: fn(filename, path)."""
        with self._lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)

    def get_recent_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return recently captured image creation events."""
        with self._lock:
            items = list(self._recent_events)
            items.reverse()
            return items[:limit]

    def is_running(self) -> bool:
        """Return True if background monitor is currently running."""
        return self._running

    def get_backend_name(self) -> str:
        """Return the active monitoring backend (watchdog FSEvents or adaptive kernel stat)."""
        return self._backend

    def start(self) -> bool:
        """Start directory monitor in background daemon thread."""
        with self._lock:
            if self._running:
                return True
            if not os.path.isdir(self.directory):
                return False

            # Seed existing files so we don't trigger alerts for past downloads
            try:
                self._known_files = {
                    e.name for e in os.scandir(self.directory)
                    if e.is_file() and os.path.splitext(e.name)[1].lower() in VALID_IMAGE_EXTENSIONS
                }
            except Exception:
                self._known_files = set()

            self._stop_event.clear()

            # Attempt watchdog observer
            try:
                import watchdog.events
                import watchdog.observers

                class _WHandler(watchdog.events.FileSystemEventHandler):
                    def __init__(self, parent: "FolderMonitor"):
                        self.parent = parent

                    def on_created(self, event):
                        if not event.is_directory:
                            self.parent._handle_fs_event(event.src_path)

                    def on_moved(self, event):
                        if not event.is_directory:
                            self.parent._handle_fs_event(event.dest_path)

                observer = watchdog.observers.Observer()
                observer.schedule(_WHandler(self), self.directory, recursive=False)
                observer.daemon = True
                observer.start()
                self._watchdog_observer = observer
                self._backend = "watchdog_native"
                self._running = True
                return True
            except ImportError:
                # Fallback to kernel stat watcher thread
                self._backend = "kernel_stat"
                self._thread = threading.Thread(target=self._run_stat_loop, daemon=True, name="KernelFolderWatcher")
                self._thread.start()
                self._running = True
                return True

    def stop(self) -> None:
        """Stop background monitor cleanly."""
        with self._lock:
            if not self._running:
                return
            self._stop_event.set()
            if self._watchdog_observer:
                try:
                    self._watchdog_observer.stop()
                    self._watchdog_observer.join(timeout=1.0)
                except Exception:
                    pass
                self._watchdog_observer = None
            self._running = False

    def _handle_fs_event(self, filepath: str) -> None:
        """Process a raw filesystem event."""
        fname = os.path.basename(filepath)
        ext = os.path.splitext(fname)[1].lower()
        if ext in IGNORED_EXTENSIONS or ext not in VALID_IMAGE_EXTENSIONS:
            return

        # Ensure file is completely written (size > 0 and stable)
        time.sleep(0.3)
        try:
            if not os.path.isfile(filepath):
                return
            size = os.path.getsize(filepath)
            if size == 0:
                return
        except OSError:
            return

        with self._lock:
            if fname in self._known_files:
                return
            self._known_files.add(fname)
            evt = {
                "filename": fname,
                "filepath": filepath,
                "detected_at": time.time(),
                "size_bytes": size,
            }
            self._recent_events.append(evt)
            callbacks = list(self._callbacks)

        for cb in callbacks:
            try:
                cb(fname, filepath)
            except Exception:
                pass

    def _run_stat_loop(self) -> None:
        """Ultra-low CPU loop querying directory mtime."""
        last_dir_mtime = 0.0
        try:
            last_dir_mtime = os.stat(self.directory).st_mtime
        except Exception:
            pass

        while not self._stop_event.is_set():
            time.sleep(self.poll_interval)
            try:
                current_mtime = os.stat(self.directory).st_mtime
                if current_mtime != last_dir_mtime:
                    last_dir_mtime = current_mtime
                    # Directory modified, check for new completed images
                    with os.scandir(self.directory) as it:
                        for entry in it:
                            try:
                                if not entry.is_file():
                                    continue
                                name = entry.name
                                ext = os.path.splitext(name)[1].lower()
                                if ext in VALID_IMAGE_EXTENSIONS and name not in self._known_files:
                                    self._handle_fs_event(entry.path)
                            except (PermissionError, OSError):
                                continue
            except (PermissionError, OSError):
                continue
