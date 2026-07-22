"""SQLite database connection management and schema initialization."""

import sqlite3
from pathlib import Path

# ──────────────────────────────────────────────
# Existing tables (M1–M6)
# ──────────────────────────────────────────────

CREATE_CASES_TABLE = """
CREATE TABLE IF NOT EXISTS cases (
    case_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

CREATE_DOCUMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS documents (
    document_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    storage_path TEXT NOT NULL,
    created_at TEXT NOT NULL,
    text_content TEXT NOT NULL DEFAULT '',
    extraction_error TEXT DEFAULT NULL,
    doc_type TEXT NOT NULL DEFAULT 'sonstiges',
    classification_confidence REAL NOT NULL DEFAULT 0.0,
    matched_patterns TEXT NOT NULL DEFAULT '[]'
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
    supersedes_confirmation_id TEXT,
    is_revoke INTEGER NOT NULL DEFAULT 0
)
"""

# Idempotent migration for M6-UI Slice 3 — add is_revoke column
ADD_IS_REVOKE_COLUMN = """
ALTER TABLE confirmed_reference_events ADD COLUMN is_revoke INTEGER NOT NULL DEFAULT 0
"""

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status)",
    "CREATE INDEX IF NOT EXISTS idx_cases_created_at ON cases(created_at)",
    "CREATE INDEX IF NOT EXISTS idx_cre_doc ON confirmed_reference_events(document_id)",
]

# ──────────────────────────────────────────────
# M7-A: Legal source provenance tables
# ──────────────────────────────────────────────

CREATE_LEGAL_SOURCES_TABLE = """
CREATE TABLE IF NOT EXISTS legal_sources (
    source_id TEXT PRIMARY KEY,
    source_key TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    authority_tier TEXT NOT NULL DEFAULT 'UNKNOWN',
    jurisdiction TEXT NOT NULL DEFAULT 'DE',
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    base_url TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT ''
)
"""

CREATE_LEGAL_SOURCE_SNAPSHOTS_TABLE = """
CREATE TABLE IF NOT EXISTS legal_source_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES legal_sources(source_id),
    source_locator TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    content_type TEXT NOT NULL DEFAULT '',
    byte_size INTEGER NOT NULL DEFAULT 0,
    sha256 TEXT NOT NULL,
    storage_path TEXT NOT NULL DEFAULT '',
    parser_version TEXT NOT NULL DEFAULT '',
    import_status TEXT NOT NULL DEFAULT 'DOWNLOADED',
    error_summary TEXT NOT NULL DEFAULT '',
    immutable INTEGER NOT NULL DEFAULT 1,
    http_etag TEXT NOT NULL DEFAULT '',
    http_last_modified TEXT NOT NULL DEFAULT ''
)
"""

CREATE_LEGAL_INSTRUMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS legal_instruments (
    instrument_id TEXT PRIMARY KEY,
    jurisdiction TEXT NOT NULL DEFAULT 'DE',
    instrument_type TEXT NOT NULL DEFAULT 'UNKNOWN',
    official_title TEXT NOT NULL,
    short_title TEXT NOT NULL DEFAULT '',
    abbreviation TEXT NOT NULL DEFAULT '',
    source_identifier TEXT NOT NULL DEFAULT '',
    authority_tier TEXT NOT NULL DEFAULT 'UNKNOWN',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

CREATE_LEGAL_EXPRESSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS legal_expressions (
    expression_id TEXT PRIMARY KEY,
    instrument_id TEXT NOT NULL REFERENCES legal_instruments(instrument_id),
    source_snapshot_id TEXT REFERENCES legal_source_snapshots(snapshot_id),
    published_at TEXT,
    valid_from TEXT,
    valid_to TEXT,
    retrieved_at TEXT,
    temporal_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    historical_completeness TEXT NOT NULL DEFAULT 'CURRENT_ONLY',
    temporal_confidence TEXT NOT NULL DEFAULT 'UNKNOWN',
    source_note TEXT NOT NULL DEFAULT ''
)
"""

CREATE_LEGAL_PROVISIONS_TABLE = """
CREATE TABLE IF NOT EXISTS legal_provisions (
    provision_id TEXT PRIMARY KEY,
    expression_id TEXT NOT NULL REFERENCES legal_expressions(expression_id),
    provision_type TEXT NOT NULL DEFAULT 'PARAGRAPH',
    provision_number TEXT NOT NULL,
    heading TEXT NOT NULL DEFAULT '',
    stable_key TEXT NOT NULL DEFAULT '',
    parent_provision_id TEXT REFERENCES legal_provisions(provision_id),
    sort_key TEXT NOT NULL DEFAULT '',
    text_content TEXT NOT NULL DEFAULT '',
    text_sha256 TEXT NOT NULL DEFAULT ''
)
"""

CREATE_LEGAL_CITATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS legal_citations (
    citation_id TEXT PRIMARY KEY,
    source_entity_type TEXT NOT NULL DEFAULT '',
    source_entity_id TEXT,
    citation_text TEXT NOT NULL,
    resolved_instrument_id TEXT REFERENCES legal_instruments(instrument_id),
    resolved_provision_id TEXT REFERENCES legal_provisions(provision_id),
    resolved_expression_id TEXT REFERENCES legal_expressions(expression_id),
    resolution_status TEXT NOT NULL DEFAULT 'PENDING',
    resolution_confidence TEXT NOT NULL DEFAULT 'UNKNOWN',
    reviewed_at TEXT,
    resolution_detail TEXT NOT NULL DEFAULT ''
)
"""

# ──────────────────────────────────────────────
# M7-A: Case legal timeline tables
# ──────────────────────────────────────────────

CREATE_CASE_LEGAL_EVENTS_TABLE = """
CREATE TABLE IF NOT EXISTS case_legal_events (
    event_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    occurred_at TEXT,
    known_at TEXT,
    recorded_at TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    source_document_id TEXT REFERENCES documents(document_id) ON DELETE SET NULL,
    review_status TEXT NOT NULL DEFAULT 'CANDIDATE',
    confidence TEXT NOT NULL DEFAULT 'LOW',
    previous_event_id TEXT,
    revoked_at TEXT,
    actor TEXT NOT NULL DEFAULT '',
    amount TEXT NOT NULL DEFAULT '',
    legal_effect_note TEXT NOT NULL DEFAULT ''
)
"""

CREATE_EVENT_RELATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS event_relations (
    relation_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    source_event_id TEXT NOT NULL REFERENCES case_legal_events(event_id) ON DELETE CASCADE,
    target_event_id TEXT NOT NULL REFERENCES case_legal_events(event_id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    review_status TEXT NOT NULL DEFAULT 'CANDIDATE',
    created_at TEXT NOT NULL,
    confirmed_at TEXT
)
"""

CREATE_CASE_LEGAL_LINKS_TABLE = """
CREATE TABLE IF NOT EXISTS case_legal_links (
    link_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    document_id TEXT REFERENCES documents(document_id) ON DELETE SET NULL,
    legal_provision_id TEXT NOT NULL REFERENCES legal_provisions(provision_id),
    relevance_note TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'CANDIDATE',
    created_at TEXT NOT NULL,
    confirmed_at TEXT,
    revoked_at TEXT,
    previous_link_id TEXT,
    confirmed_by TEXT NOT NULL DEFAULT ''
)
"""

CREATE_LEGAL_ISSUES_TABLE = """
CREATE TABLE IF NOT EXISTS legal_issues (
    issue_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'OPEN',
    source TEXT NOT NULL DEFAULT 'MANUAL',
    confidence TEXT NOT NULL DEFAULT 'LOW',
    created_at TEXT NOT NULL,
    reviewed_at TEXT
)
"""

# ──────────────────────────────────────────────
# M7-A: SQLite FTS5 full-text search
# ──────────────────────────────────────────────

CREATE_PROVISIONS_FTS_TABLE = """
CREATE VIRTUAL TABLE IF NOT EXISTS legal_provisions_fts USING fts5(
    provision_id UNINDEXED,
    provision_number,
    heading,
    text_content,
    content='legal_provisions',
    content_rowid='rowid'
)
"""

# ──────────────────────────────────────────────
# Indexes
# ──────────────────────────────────────────────

EXISTING_INDEXES = [
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
    payload_digest TEXT NOT NULL DEFAULT '',
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

M7A_INDEXES = [
    # legal sources
    "CREATE INDEX IF NOT EXISTS idx_ls_source_key ON legal_sources(source_key)",
    "CREATE INDEX IF NOT EXISTS idx_ls_authority ON legal_sources(authority_tier)",
    # snapshots
    "CREATE INDEX IF NOT EXISTS idx_lss_source ON legal_source_snapshots(source_id)",
    "CREATE INDEX IF NOT EXISTS idx_lss_sha256 ON legal_source_snapshots(sha256)",
    "CREATE INDEX IF NOT EXISTS idx_lss_status ON legal_source_snapshots(import_status)",
    # instruments
    "CREATE INDEX IF NOT EXISTS idx_li_abbrev ON legal_instruments(abbreviation)",
    "CREATE INDEX IF NOT EXISTS idx_li_jurisdiction ON legal_instruments(jurisdiction)",
    # expressions
    "CREATE INDEX IF NOT EXISTS idx_le_instrument ON legal_expressions(instrument_id)",
    "CREATE INDEX IF NOT EXISTS idx_le_valid_from ON legal_expressions(valid_from)",
    # provisions
    "CREATE INDEX IF NOT EXISTS idx_lp_expression ON legal_provisions(expression_id)",
    "CREATE INDEX IF NOT EXISTS idx_lp_stable_key ON legal_provisions(stable_key)",
    "CREATE INDEX IF NOT EXISTS idx_lp_parent ON legal_provisions(parent_provision_id)",
    # citations
    "CREATE INDEX IF NOT EXISTS idx_lc_resolved ON legal_citations(resolved_provision_id)",
    "CREATE INDEX IF NOT EXISTS idx_lc_status ON legal_citations(resolution_status)",
    # legal events
    "CREATE INDEX IF NOT EXISTS idx_cle_case ON case_legal_events(case_id)",
    "CREATE INDEX IF NOT EXISTS idx_cle_occurred ON case_legal_events(occurred_at)",
    "CREATE INDEX IF NOT EXISTS idx_cle_status ON case_legal_events(review_status)",
    # event relations
    "CREATE INDEX IF NOT EXISTS idx_er_case ON event_relations(case_id)",
    "CREATE INDEX IF NOT EXISTS idx_er_source ON event_relations(source_event_id)",
    "CREATE INDEX IF NOT EXISTS idx_er_target ON event_relations(target_event_id)",
    # legal links
    "CREATE INDEX IF NOT EXISTS idx_cll_case ON case_legal_links(case_id)",
    "CREATE INDEX IF NOT EXISTS idx_cll_provision ON case_legal_links(legal_provision_id)",
    "CREATE INDEX IF NOT EXISTS idx_cll_status ON case_legal_links(status)",
    # legal issues
    "CREATE INDEX IF NOT EXISTS idx_lis_case ON legal_issues(case_id)",
]


def get_connection(db_path: Path) -> sqlite3.Connection:
    """Create a new SQLite connection with recommended pragmas."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = sqlite3.Row
    return conn


def _migrate_add_column(conn: sqlite3.Connection, table: str, column: str, alter_sql: str) -> None:
    """Idempotent column addition — skips if column already exists."""
    try:
        conn.execute(f"SELECT {column} FROM {table} LIMIT 0")
    except sqlite3.OperationalError:
        conn.execute(alter_sql)


def initialize_schema(db_path: Path) -> None:
    """Create the database schema if it doesn't exist (idempotent)."""
    conn = get_connection(db_path)
    try:
        # Existing M1-M6 tables
        conn.execute(CREATE_CASES_TABLE)
        conn.execute(CREATE_DOCUMENTS_TABLE)
        conn.execute(CREATE_CONFIRMED_REFERENCE_EVENTS_TABLE)
        conn.execute(CREATE_IDEMPOTENCY_RECORDS_TABLE)
        for index_sql in EXISTING_INDEXES:
            conn.execute(index_sql)
        for index_sql in CREATE_IDEMPOTENCY_INDEXES:
            conn.execute(index_sql)
        # M6-UI Slice 3 migration — add is_revoke column (idempotent)
        _migrate_add_column(conn, "confirmed_reference_events", "is_revoke", ADD_IS_REVOKE_COLUMN)

        # M7-A legal source provenance
        conn.execute(CREATE_LEGAL_SOURCES_TABLE)
        conn.execute(CREATE_LEGAL_SOURCE_SNAPSHOTS_TABLE)
        conn.execute(CREATE_LEGAL_INSTRUMENTS_TABLE)
        conn.execute(CREATE_LEGAL_EXPRESSIONS_TABLE)
        conn.execute(CREATE_LEGAL_PROVISIONS_TABLE)
        conn.execute(CREATE_LEGAL_CITATIONS_TABLE)

        # M7-A case legal timeline
        conn.execute(CREATE_CASE_LEGAL_EVENTS_TABLE)
        conn.execute(CREATE_EVENT_RELATIONS_TABLE)
        conn.execute(CREATE_CASE_LEGAL_LINKS_TABLE)
        conn.execute(CREATE_LEGAL_ISSUES_TABLE)

        # FTS5 (idempotent — IF NOT EXISTS handles this)
        conn.execute(CREATE_PROVISIONS_FTS_TABLE)

        # All M7-A indexes
        for index_sql in M7A_INDEXES:
            conn.execute(index_sql)
        conn.commit()
    finally:
        conn.close()
