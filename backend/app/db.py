"""SQLite storage. One file (backend/data/mindbridge.db), zero setup.

PostgreSQL is the production choice; SQLite keeps the prototype portable.
All free text is stored encrypted (see security.py).
"""
from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from typing import Any, Iterator

from . import config

_lock = threading.RLock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    mode TEXT NOT NULL DEFAULT 'text',
    peak_tier TEXT NOT NULL DEFAULT 'LOW',
    avg_distress REAL,
    turns INTEGER NOT NULL DEFAULT 0,
    dominant_emotion TEXT,
    is_demo INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content_enc TEXT NOT NULL,
    created_at TEXT NOT NULL,
    tier TEXT,
    provider TEXT
);
CREATE TABLE IF NOT EXISTS readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    fused REAL,
    confidence REAL,
    smoothed REAL,
    payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    created_at TEXT NOT NULL,
    tier TEXT NOT NULL,
    source TEXT NOT NULL,
    reasons TEXT NOT NULL,
    excerpt_enc TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    note TEXT,
    updated_at TEXT,
    contact_notified INTEGER NOT NULL DEFAULT 0,
    is_demo INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS checkins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    day TEXT NOT NULL,
    mood INTEGER NOT NULL,
    sleep_hours REAL,
    energy INTEGER,
    anxiety INTEGER,
    tags TEXT,
    note_enc TEXT,
    created_at TEXT NOT NULL,
    is_demo INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    channel TEXT NOT NULL,
    recipient TEXT NOT NULL,
    message TEXT NOT NULL,
    status TEXT NOT NULL
);
"""

DEFAULT_SETTINGS: dict[str, Any] = {
    "profile": {"name": "Aarav", "language": "en-IN"},
    "consent": {
        "accepted": False,
        "camera": True,
        "microphone": True,
        "store_history": True,
        "counselor_alerts": True,
        "trusted_contact_alerts": True,
        "share_reports": False,
    },
    "trusted_contact": {"name": "Priya (sister)", "phone": "+91 98XXXXXX21",
                        "email": "priya@example.com"},
    "incognito": False,
}

_conn: sqlite3.Connection | None = None


def connect() -> sqlite3.Connection:
    global _conn
    with _lock:
        if _conn is None:
            config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            _conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
            _conn.row_factory = sqlite3.Row
            _conn.executescript(SCHEMA)
            _conn.commit()
        return _conn


def close() -> None:
    global _conn
    with _lock:
        if _conn is not None:
            _conn.close()
            _conn = None


@contextmanager
def tx() -> Iterator[sqlite3.Connection]:
    with _lock:
        conn = connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def query(sql: str, params: tuple = ()) -> list[dict]:
    with _lock:
        return [dict(r) for r in connect().execute(sql, params).fetchall()]


def one(sql: str, params: tuple = ()) -> dict | None:
    rows = query(sql, params)
    return rows[0] if rows else None


# ---- settings helpers -------------------------------------------------------
def get_setting(key: str) -> Any:
    row = one("SELECT value FROM settings WHERE key = ?", (key,))
    if row is None:
        return json.loads(json.dumps(DEFAULT_SETTINGS.get(key)))
    return json.loads(row["value"])


def set_setting(key: str, value: Any) -> None:
    with tx() as c:
        c.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, json.dumps(value)),
        )


def all_settings() -> dict[str, Any]:
    return {k: get_setting(k) for k in DEFAULT_SETTINGS}


def wipe_all() -> None:
    with tx() as c:
        for table in ("sessions", "messages", "readings", "alerts", "checkins",
                      "notifications", "settings"):
            c.execute(f"DELETE FROM {table}")
    with _lock:
        connect().execute("VACUUM")
