"""SQLite persistence and duplicate detection."""

import hashlib
import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DEFAULT_DB = os.getenv("LEAD_FINDER_DB", "data/leads.db")


def connect(db_path: str = DEFAULT_DB) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str = DEFAULT_DB) -> None:
    with connect(db_path) as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            category TEXT NOT NULL DEFAULT 'other',
            intent TEXT NOT NULL DEFAULT 'unclear',
            source TEXT NOT NULL,
            source_name TEXT NOT NULL,
            url TEXT,
            contact TEXT,
            budget TEXT,
            language TEXT NOT NULL DEFAULT 'unknown',
            score INTEGER NOT NULL DEFAULT 0 CHECK(score BETWEEN 0 AND 100),
            status TEXT NOT NULL DEFAULT 'LOW',
            published_at TEXT,
            found_at TEXT NOT NULL,
            fingerprint TEXT NOT NULL UNIQUE
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_leads_url
        ON leads(url) WHERE url IS NOT NULL AND url <> '';
        CREATE TABLE IF NOT EXISTS sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL,
            url TEXT,
            enabled INTEGER NOT NULL DEFAULT 1,
            last_checked TEXT
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """)


def fingerprint(title: str, description: str) -> str:
    normalized = " ".join(f"{title} {description}".lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def add_lead(data: dict, db_path: str = DEFAULT_DB) -> tuple[bool, int | None]:
    now = datetime.now(timezone.utc).isoformat()
    fp = fingerprint(data["title"], data.get("description", ""))
    try:
        with connect(db_path) as conn:
            cur = conn.execute("""
                INSERT INTO leads (
                    title, description, category, intent, source, source_name,
                    url, contact, budget, language, score, status,
                    published_at, found_at, fingerprint
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data["title"], data.get("description", ""), data.get("category", "other"),
                data.get("intent", "unclear"), data.get("source", "manual"),
                data.get("source_name", "Manual"), data.get("url"), data.get("contact"),
                data.get("budget"), data.get("language", "unknown"), data.get("score", 0),
                data.get("status", "LOW"), data.get("published_at"), now, fp,
            ))
            return True, cur.lastrowid
    except sqlite3.IntegrityError:
        return False, None


def list_leads(hot_only: bool = False, limit: int = 30, db_path: str = DEFAULT_DB):
    query = "SELECT * FROM leads"
    params = []
    if hot_only:
        query += " WHERE status = ?"
        params.append("HOT")
    query += " ORDER BY score DESC, found_at DESC LIMIT ?"
    params.append(limit)
    with connect(db_path) as conn:
        return conn.execute(query, params).fetchall()


def get_stats(db_path: str = DEFAULT_DB) -> dict:
    with connect(db_path) as conn:
        total = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        rows = conn.execute("SELECT status, COUNT(*) n FROM leads GROUP BY status").fetchall()
        return {"total": total, **{row["status"].lower(): row["n"] for row in rows}}
