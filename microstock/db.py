"""Embedded SQLite WAL Database Engine for Microstock AI Studio.

Provides persistence for image assets, vision metadata, perceptual hashes,
agency submission logs, and contributor upload credentials.
"""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


def get_default_db_path() -> str:
    """Return default absolute path to local SQLite database in exports/data/."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "exports", "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "studio.db")


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Open a SQLite connection configured with WAL journal mode for high concurrency."""
    path = db_path or get_default_db_path()
    conn = sqlite3.connect(path, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """Initialize database tables, relations, and indexes if they do not exist."""
    with get_connection(db_path) as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS assets (
            id              TEXT PRIMARY KEY,
            file_path       TEXT NOT NULL,
            file_name       TEXT NOT NULL,
            file_size_bytes INTEGER NOT NULL,
            width           INTEGER NOT NULL,
            height          INTEGER NOT NULL,
            aspect_ratio    TEXT NOT NULL,
            phash_hex       TEXT NOT NULL,
            status          TEXT DEFAULT 'ready',
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS asset_metadata (
            asset_id          TEXT PRIMARY KEY REFERENCES assets(id) ON DELETE CASCADE,
            title             TEXT NOT NULL,
            description       TEXT NOT NULL,
            keywords_json     TEXT NOT NULL,
            adobe_category_id INTEGER DEFAULT 8,
            shutterstock_cats TEXT DEFAULT '',
            is_xmp_injected   INTEGER DEFAULT 0,
            updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS agency_accounts (
            id          TEXT PRIMARY KEY,
            agency_name TEXT NOT NULL UNIQUE,
            host        TEXT NOT NULL,
            port        INTEGER DEFAULT 21,
            protocol    TEXT DEFAULT 'ftp',
            username    TEXT NOT NULL,
            password    TEXT NOT NULL,
            is_active   INTEGER DEFAULT 1,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS submission_logs (
            id              TEXT PRIMARY KEY,
            asset_id        TEXT REFERENCES assets(id) ON DELETE SET NULL,
            agency_name     TEXT NOT NULL,
            submission_type TEXT NOT NULL,
            remote_filename TEXT,
            status          TEXT DEFAULT 'uploaded',
            error_message   TEXT,
            uploaded_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_assets_phash ON assets(phash_hex);
        CREATE INDEX IF NOT EXISTS idx_assets_created ON assets(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_submission_agency ON submission_logs(agency_name, uploaded_at DESC);
        """)


def save_asset(
    file_path: str,
    file_name: str,
    file_size_bytes: int,
    width: int,
    height: int,
    aspect_ratio: str,
    phash_hex: str,
    title: str,
    description: str,
    keywords: List[str],
    adobe_category_id: int = 8,
    shutterstock_cats: Optional[List[str]] = None,
    is_xmp_injected: bool = False,
    asset_id: Optional[str] = None,
    db_path: Optional[str] = None,
) -> str:
    """Save an asset and its microstock metadata atomically into the database."""
    uid = asset_id or str(uuid.uuid4())
    cats_str = ",".join(shutterstock_cats or [])
    kw_json = json.dumps(keywords, ensure_ascii=False)
    now = datetime.utcnow().isoformat()

    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO assets (
                id, file_path, file_name, file_size_bytes, width, height, aspect_ratio, phash_hex, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (uid, file_path, file_name, file_size_bytes, width, height, aspect_ratio, phash_hex, now),
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO asset_metadata (
                asset_id, title, description, keywords_json, adobe_category_id, shutterstock_cats, is_xmp_injected, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (uid, title, description, kw_json, int(adobe_category_id), cats_str, int(is_xmp_injected), now),
        )
    return uid


def get_asset(asset_id: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve an asset and its complete metadata by ID."""
    with get_connection(db_path) as conn:
        cur = conn.execute(
            """
            SELECT a.*, m.title, m.description, m.keywords_json, m.adobe_category_id,
                   m.shutterstock_cats, m.is_xmp_injected
            FROM assets a
            LEFT JOIN asset_metadata m ON a.id = m.asset_id
            WHERE a.id = ?
            """,
            (asset_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        data = dict(row)
        if data.get("keywords_json"):
            try:
                data["keywords"] = json.loads(data["keywords_json"])
            except Exception:
                data["keywords"] = []
        else:
            data["keywords"] = []
        return data


def list_recent_assets(limit: int = 50, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """List most recently processed microstock assets."""
    with get_connection(db_path) as conn:
        cur = conn.execute(
            """
            SELECT a.*, m.title, m.description, m.keywords_json, m.adobe_category_id,
                   m.shutterstock_cats, m.is_xmp_injected
            FROM assets a
            LEFT JOIN asset_metadata m ON a.id = m.asset_id
            ORDER BY a.created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        results = []
        for row in cur.fetchall():
            d = dict(row)
            try:
                d["keywords"] = json.loads(d.get("keywords_json") or "[]")
            except Exception:
                d["keywords"] = []
            results.append(d)
        return results


def find_near_duplicates_in_db(
    target_phash: str,
    max_hamming_distance: int = 5,
    limit: int = 10,
    db_path: Optional[str] = None,
) -> List[Tuple[Dict[str, Any], int, float]]:
    """Compare a hash against all stored assets.
    
    Returns list of (asset_dict, hamming_distance, similarity_percent).
    """
    if not target_phash or len(target_phash) != 16:
        return []

    try:
        target_int = int(target_phash, 16)
    except ValueError:
        return []

    matches = []
    with get_connection(db_path) as conn:
        cur = conn.execute("SELECT a.*, m.title FROM assets a LEFT JOIN asset_metadata m ON a.id = m.asset_id")
        for row in cur.fetchall():
            h_str = row["phash_hex"]
            try:
                h_int = int(h_str, 16)
                dist = bin(target_int ^ h_int).count("1")
                if dist <= max_hamming_distance:
                    sim = round((1.0 - (dist / 64.0)) * 100, 1)
                    matches.append((dict(row), dist, sim))
            except Exception:
                continue

    matches.sort(key=lambda x: x[1])
    return matches[:limit]


def log_submission(
    agency_name: str,
    submission_type: str,
    remote_filename: str,
    status: str = "uploaded",
    asset_id: Optional[str] = None,
    error_message: Optional[str] = None,
    db_path: Optional[str] = None,
) -> str:
    """Log an upload event or batch dispatch to stock contributor endpoints."""
    uid = str(uuid.uuid4())
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO submission_logs (
                id, asset_id, agency_name, submission_type, remote_filename, status, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (uid, asset_id, agency_name, submission_type, remote_filename, status, error_message),
        )
    return uid


def list_recent_submissions(limit: int = 50, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """List recent dispatch submissions and upload history."""
    with get_connection(db_path) as conn:
        cur = conn.execute(
            """
            SELECT s.*, a.file_name, a.file_path, a.width, a.height
            FROM submission_logs s
            LEFT JOIN assets a ON s.asset_id = a.id
            ORDER BY s.uploaded_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(r) for r in cur.fetchall()]


def save_agency_account(
    agency_name: str,
    host: str,
    port: int,
    protocol: str,
    username: str,
    password: str,
    db_path: Optional[str] = None,
) -> str:
    """Store or update agency contributor credentials."""
    uid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO agency_accounts (
                id, agency_name, host, port, protocol, username, password, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(agency_name) DO UPDATE SET
                host = excluded.host,
                port = excluded.port,
                protocol = excluded.protocol,
                username = excluded.username,
                password = excluded.password,
                updated_at = excluded.updated_at
            """,
            (uid, agency_name, host, port, protocol, username, password, now),
        )
    return uid


def get_agency_account(agency_name: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve saved credentials for a stock agency."""
    with get_connection(db_path) as conn:
        cur = conn.execute("SELECT * FROM agency_accounts WHERE agency_name = ? AND is_active = 1", (agency_name,))
        row = cur.fetchone()
        return dict(row) if row else None


# Auto-initialize database schema on module load
init_db()

