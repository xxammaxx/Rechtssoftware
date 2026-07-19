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

CREATE_CONFIRMED_REFERENCE_EVENTS_TABLE = """
CREATE TABLE IF NOT EXISTS confirmed_reference_events (
    confirmation_id TEXT PRIMARY KEY,
    candidate_id TEXT,
    document_id TEXT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
    deadline_candidate_index INTEGER NOT NULL DEFAULT 0,
    event_type TEXT NOT NULL,
    confirmed_date TEXT,
    source_type TEXT NOT NULL DEFAULT 'auto_detected',
    confirmation_method TEXT NOT NULL DEFAULT 'auto_suggested',
    confirmed_at TEXT NOT NULL,
    confirmed_by TEXT NOT NULL DEFAULT '',
    evidence_note TEXT NOT NULL DEFAULT '',
    supersedes_confirmation_id TEXT
)
"""

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status)",
    "CREATE INDEX IF NOT EXISTS idx_cases_created_at ON cases(created_at)",
    "CREATE INDEX IF NOT EXISTS idx_cre_doc ON confirmed_reference_events(document_id)",
]

CREATE_IDEMPOTENCY_RECORDS_TABLE = """
CREATE TABLE IF NOT EXISTS idempotency_records (
    idempotency_key TEXT PRIMARY KEY,
    operation_type TEXT NOT NULL,
    target_document_id TEXT NOT NULL,
    target_candidate_index INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'processing',
    result_confirmation_id TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    expires_at TEXT NOT NULL
)
"""

CREATE_IDEMPOTENCY_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_idempotency_expires ON idempotency_records(expires_at)",
    "CREATE INDEX IF NOT EXISTS idx_idempotency_target "
    "ON idempotency_records(target_document_id, target_candidate_index)",
]


def get_connection(db_path: Path) -> sqlite3.Connection:
    """Create a new SQLite connection with recommended pragmas."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = sqlite3.Row
    return conn


def initialize_schema(db_path: Path) -> None:
    """Create the database schema if it doesn't exist (idempotent)."""
    conn = get_connection(db_path)
    try:
        conn.execute(CREATE_CASES_TABLE)
        conn.execute(CREATE_CONFIRMED_REFERENCE_EVENTS_TABLE)
        conn.execute(CREATE_IDEMPOTENCY_RECORDS_TABLE)
        for index_sql in CREATE_INDEXES:
            conn.execute(index_sql)
        for index_sql in CREATE_IDEMPOTENCY_INDEXES:
            conn.execute(index_sql)
        conn.commit()
    finally:
        conn.close()
