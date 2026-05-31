"""Database initialization and optional CSV-based seeding.

This module creates a local SQLite database for development and testing.
If you want to populate the DB with your own "real" values, set the
`REAL_DATA_DIR` environment variable to a folder containing `users.csv`
and `pull_requests.csv` (optional). The CSV files should have headers
matching the columns inserted by the seeder.
"""
import csv
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable, Mapping


DB_PATH = Path(__file__).parent.parent.parent / "agentforge.db"


def _ensure_tables(cursor: sqlite3.Cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS pull_requests (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            repo TEXT NOT NULL,
            status TEXT DEFAULT 'open',
            author TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """
    )


def _rows_from_csv(path: Path) -> Iterable[Mapping[str, str]]:
    with path.open("r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            yield row


def seed_from_csv(cursor: sqlite3.Cursor, seed_dir: Path) -> None:
    users_csv = seed_dir / "users.csv"
    prs_csv = seed_dir / "pull_requests.csv"

    if users_csv.exists():
        for row in _rows_from_csv(users_csv):
            cursor.execute(
                "INSERT INTO users (name, email, created_at) VALUES (?, ?, ?)",
                (row.get("name"), row.get("email"), row.get("created_at") or datetime.utcnow().isoformat()),
            )

    if prs_csv.exists():
        for row in _rows_from_csv(prs_csv):
            cursor.execute(
                "INSERT INTO pull_requests (title, repo, status, author, created_at) VALUES (?, ?, ?, ?, ?)",
                (
                    row.get("title"),
                    row.get("repo") or "unknown",
                    row.get("status") or "open",
                    row.get("author") or "unknown",
                    row.get("created_at") or datetime.utcnow().isoformat(),
                ),
            )


def init_db() -> None:
    """Initialize SQLite database with either CSV seed or realistic samples."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    _ensure_tables(cursor)

    # If REAL_DATA_DIR is set, prefer CSV seeding
    real_dir = os.environ.get("REAL_DATA_DIR")
    if real_dir:
        seed_path = Path(real_dir)
        if seed_path.exists() and seed_path.is_dir():
            seed_from_csv(cursor, seed_path)
            conn.commit()
            conn.close()
            return

    # Fallback: insert real sample data only if tables are empty
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        users = [
            ("Shubh Sanghvi", "shubh242@users.noreply.github.com", "2026-03-10T05:50:46Z"),
            ("Drashti Magia", "drashtimagia@users.noreply.github.com", "2026-03-14T13:29:27Z"),
            ("Hanh Nguyen", "Hanhnguyen21-sys@users.noreply.github.com", "2026-04-30T08:42:20Z"),
            ("Parth Gala", "parthpgala@gmail.com", "2026-05-10T12:00:00Z"),
            ("Vansh Mehta", "vanshmehta-7@users.noreply.github.com", "2026-05-11T17:25:26Z"),
            ("Vishwesh Krishna Hariharakrishnan", "vishwesh1809@gmail.com", "2026-05-12T09:00:00Z"),
            ("Sebastián Ramírez", "tiangolo@gmail.com", "2020-01-01T12:00:00Z"),
            ("Samuel Colvin", "samuel@pydantic.dev", "2019-01-01T12:00:00Z"),
        ]
        cursor.executemany(
            "INSERT INTO users (name, email, created_at) VALUES (?, ?, ?)",
            users,
        )

    cursor.execute("SELECT COUNT(*) FROM pull_requests")
    if cursor.fetchone()[0] == 0:
        prs = [
            ("Update invitation feature", "Hanhnguyen21-sys/TrackerApp1", "closed", "Hanhnguyen21-sys", "2026-03-14T11:03:37Z"),
            ("Update projec page", "Hanhnguyen21-sys/TrackerApp1", "open", "Hanhnguyen21-sys", "2026-03-14T12:00:00Z"),
            ("Recover", "Hanhnguyen21-sys/TrackerApp1", "closed", "Hanhnguyen21-sys", "2026-03-14T12:30:00Z"),
            ("Nguyen update due date + UI notification", "Hanhnguyen21-sys/TrackerApp1", "closed", "Hanhnguyen21-sys", "2026-03-15T08:57:45Z"),
            ("Nguyen update", "Hanhnguyen21-sys/TrackerApp1", "closed", "Hanhnguyen21-sys", "2026-03-15T10:00:00Z"),
            ("Nguyen update", "Hanhnguyen21-sys/TrackerApp1", "closed", "Hanhnguyen21-sys", "2026-03-16T00:00:00Z"),
            ("Feature/auth and db models", "Hanhnguyen21-sys/TrackerApp", "closed", "Hanhnguyen21-sys", "2026-05-04T16:00:00Z"),
            ("Revert codebase to March 14, 7:32 PM state", "drashtimagia/clinicops-copilot", "closed", "drashtimagia", "2026-03-14T19:32:00Z"),
            ("Revert codebase to March 14, 7:32 PM state while preserving UX enhanc…", "drashtimagia/clinicops-copilot", "closed", "drashtimagia", "2026-03-15T07:14:58Z"),
            ("Fix users table schema constraints", "shubh242/clinicops-copilot", "open", "shubh242", "2026-05-15T09:00:00Z"),
            ("Refactor cart state using Redux", "ParthGala2k/dropshipping_alien", "open", "ParthGala2k", "2026-04-10T12:00:00Z"),
            ("Fix memory leak in ccas handler", "vichcraft/ccas", "open", "vichcraft", "2026-05-01T15:30:00Z"),
            ("Improve coding challenge editor styling", "vanshmehta-7/CodeShala", "merged", "vanshmehta-7", "2026-05-12T10:00:00Z"),
            ("Document how to use custom router classes", "fastapi/fastapi", "open", "tiangolo", "2026-05-20T10:00:00Z"),
            ("Fix typo in tutorial docs", "fastapi/fastapi", "open", "tiangolo", "2026-05-25T08:00:00Z"),
            ("Add support for custom field validators in model config", "pydantic/pydantic", "open", "samuelcolvin", "2026-05-22T14:30:00Z"),
        ]
        cursor.executemany(
            "INSERT INTO pull_requests (title, repo, status, author, created_at) VALUES (?, ?, ?, ?, ?)",
            prs,
        )

    conn.commit()
    conn.close()


def get_connection() -> sqlite3.Connection:
    """Get a SQLite connection, initializing DB if needed."""
    if not DB_PATH.exists():
        init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
