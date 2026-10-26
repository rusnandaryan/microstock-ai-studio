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
    """Return default ~/Downloads path for the current OS."""
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

    # Sort newest first
    results.sort(key=lambda x: x[2], reverse=True)
    return results[:max_files]


def read_image_bytes(filepath: str) -> Optional[Tuple[str, bytes, str]]:
    """Read an image file safely and return (filename, bytes, mime_type)."""
    try:
        filename = os.path.basename(filepath)
        mime, _ = mimetypes.guess_type(filepath)
        if not mime or not mime.startswith("image/"):
            mime = "image/jpeg"
        with open(filepath, "rb") as f:
            data = f.read()
        if len(data) > 0:
            return filename, data, mime
    except Exception:
        pass
    return None
