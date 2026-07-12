"""SQLite database connection management and schema initialization."""

import sqlite3
from pathlib import Path

CREATE_CASES_TABLE = """
CREATE TABLE IF NOT EXISTS cases (
    case_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status)",
    "CREATE INDEX IF NOT EXISTS idx_cases_created_at ON cases(created_at)",
]


def get_connection(db_path: Path) -> sqlite3.Connection:
    """Create a new SQLite connection with recommended pragmas."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def initialize_schema(db_path: Path) -> None:
    """Create the database schema if it doesn't exist (idempotent)."""
    conn = get_connection(db_path)
    try:
        conn.execute(CREATE_CASES_TABLE)
        for index_sql in CREATE_INDEXES:
            conn.execute(index_sql)
        conn.commit()
    finally:
        conn.close()
