"""SQLite persistence for confirmed reference events (M6-A Variant B)."""

import sqlite3
from datetime import date, datetime
from pathlib import Path
from uuid import UUID

from private_legal_navigator.application.event_repository import ReferenceEventRepository
from private_legal_navigator.domain.calendar import (
    ConfirmationMethod,
    ConfirmationStatus,
    ConfirmedReferenceEvent,
    EventType,
    SourceType,
)
from private_legal_navigator.infrastructure.database import get_connection

# Schema V2: includes confirmation_status, deadline_candidate_index, and FK with CASCADE
CREATE_CONFIRMED_REFERENCE_EVENTS_TABLE = """
CREATE TABLE IF NOT EXISTS confirmed_reference_events (
    confirmation_id TEXT PRIMARY KEY,
    candidate_id TEXT,
    document_id TEXT NOT NULL
        REFERENCES documents(document_id) ON DELETE CASCADE,
    deadline_candidate_index INTEGER NOT NULL DEFAULT 0,
    event_type TEXT NOT NULL,
    confirmed_date TEXT,
    source_type TEXT NOT NULL DEFAULT 'auto_detected',
    confirmation_method TEXT NOT NULL,
    confirmation_status TEXT NOT NULL DEFAULT 'unconfirmed',
    confirmed_at TEXT NOT NULL,
    confirmed_by TEXT NOT NULL DEFAULT '',
    supersedes_confirmation_id TEXT
)
"""

CREATE_CONFIRMED_EVENTS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_confirmed_events_document "
    "ON confirmed_reference_events(document_id)",
    "CREATE INDEX IF NOT EXISTS idx_confirmed_events_doc_status "
    "ON confirmed_reference_events(document_id, confirmation_status)",
    "CREATE INDEX IF NOT EXISTS idx_confirmed_events_doc_candidate "
    "ON confirmed_reference_events(document_id, deadline_candidate_index)",
]

# V1→V2 migration: add missing columns if table exists but is V1
MIGRATE_V1_TO_V2 = [
    "ALTER TABLE confirmed_reference_events "
    "ADD COLUMN confirmation_status TEXT NOT NULL DEFAULT 'unconfirmed'",
    "ALTER TABLE confirmed_reference_events "
    "ADD COLUMN deadline_candidate_index INTEGER NOT NULL DEFAULT 0",
]


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    """Check if a column exists in a table."""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row["name"] == column for row in rows)


class SqliteEventRepository(ReferenceEventRepository):
    """SQLite-based persistence for confirmed reference events."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def initialize_schema(self) -> None:
        """Create or migrate the confirmed_reference_events table (idempotent)."""
        conn = get_connection(self._db_path)
        try:
            conn.execute(CREATE_CONFIRMED_REFERENCE_EVENTS_TABLE)

            # V1→V2 migration: add confirmation_status and deadline_candidate_index
            # if the table exists from V1 without these columns
            if _column_exists(conn, "confirmed_reference_events", "confirmation_method"):
                if not _column_exists(conn, "confirmed_reference_events", "confirmation_status"):
                    conn.execute(
                        "ALTER TABLE confirmed_reference_events "
                        "ADD COLUMN confirmation_status TEXT NOT NULL DEFAULT 'unconfirmed'"
                    )
                    # Migrate V1 data: infer status from existing columns
                    conn.execute(
                        "UPDATE confirmed_reference_events "
                        "SET confirmation_status = 'confirmed' "
                        "WHERE confirmed_date IS NOT NULL "
                        "AND confirmation_method != 'superseded_marked'"
                    )
                    conn.execute(
                        "UPDATE confirmed_reference_events "
                        "SET confirmation_status = 'rejected' "
                        "WHERE confirmed_date IS NULL "
                        "AND supersedes_confirmation_id IS NULL"
                    )
                    conn.execute(
                        "UPDATE confirmed_reference_events "
                        "SET confirmation_status = 'superseded' "
                        "WHERE confirmation_method = 'superseded_marked'"
                    )
                    conn.execute(
                        "UPDATE confirmed_reference_events "
                        "SET confirmation_status = 'revoked' "
                        "WHERE confirmed_date IS NULL "
                        "AND supersedes_confirmation_id IS NOT NULL"
                    )
                    # Reset superseded_marked from method column
                    conn.execute(
                        "UPDATE confirmed_reference_events "
                        "SET confirmation_method = 'auto_suggested' "
                        "WHERE confirmation_method = 'superseded_marked'"
                    )
                if not _column_exists(
                    conn, "confirmed_reference_events", "deadline_candidate_index"
                ):
                    conn.execute(
                        "ALTER TABLE confirmed_reference_events "
                        "ADD COLUMN deadline_candidate_index INTEGER NOT NULL DEFAULT 0"
                    )

            for index_sql in CREATE_CONFIRMED_EVENTS_INDEXES:
                conn.execute(index_sql)
            conn.commit()
        finally:
            conn.close()

    def save(self, event: ConfirmedReferenceEvent, candidate_index: int = 0) -> None:
        """Store a confirmed reference event.

        If a CONFIRMED event already exists for the same document + candidate_index,
        it is marked as SUPERSEDED first.
        If supersedes_confirmation_id is set, the prior record is marked SUPERSEDED.
        """
        conn = get_connection(self._db_path)
        try:
            # Supersede any existing CONFIRMED confirmation for the same document+candidate
            conn.execute(
                "UPDATE confirmed_reference_events "
                "SET confirmation_status = ? "
                "WHERE document_id = ? "
                "AND deadline_candidate_index = ? "
                "AND confirmation_status = ?",
                (
                    ConfirmationStatus.SUPERSEDED.value,
                    str(event.document_id),
                    candidate_index,
                    ConfirmationStatus.CONFIRMED.value,
                ),
            )

            # If revoking/superseding: mark prior as SUPERSEDED
            if event.supersedes_confirmation_id is not None:
                conn.execute(
                    "UPDATE confirmed_reference_events "
                    "SET confirmation_status = ? "
                    "WHERE confirmation_id = ?",
                    (
                        ConfirmationStatus.SUPERSEDED.value,
                        str(event.supersedes_confirmation_id),
                    ),
                )

            conn.execute(
                "INSERT INTO confirmed_reference_events "
                "(confirmation_id, candidate_id, document_id, deadline_candidate_index, "
                "event_type, confirmed_date, source_type, confirmation_method, "
                "confirmation_status, confirmed_at, confirmed_by, "
                "supersedes_confirmation_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    str(event.confirmation_id),
                    str(event.candidate_id) if event.candidate_id else None,
                    str(event.document_id),
                    candidate_index,
                    event.event_type.value,
                    event.confirmed_date.isoformat() if event.confirmed_date else None,
                    event.source_type.value,
                    event.confirmation_method.value,
                    event.confirmation_status.value,
                    event.confirmed_at.isoformat() if event.confirmed_at else "",
                    event.confirmed_by,
                    str(event.supersedes_confirmation_id)
                    if event.supersedes_confirmation_id
                    else None,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_by_id(self, confirmation_id: UUID) -> ConfirmedReferenceEvent | None:
        """Retrieve a confirmation by its ID."""
        conn = get_connection(self._db_path)
        try:
            row = conn.execute(
                "SELECT * FROM confirmed_reference_events WHERE confirmation_id = ?",
                (str(confirmation_id),),
            ).fetchone()
            if row is None:
                return None
            return self._row_to_domain(row)
        finally:
            conn.close()

    def get_active(
        self, document_id: UUID, candidate_index: int
    ) -> ConfirmedReferenceEvent | None:
        """Get the currently active (CONFIRMED) event for a document and candidate index.

        Returns the most recent CONFIRMED event, or None.
        """
        conn = get_connection(self._db_path)
        try:
            row = conn.execute(
                "SELECT * FROM confirmed_reference_events "
                "WHERE document_id = ? "
                "AND deadline_candidate_index = ? "
                "AND confirmation_status = ? "
                "ORDER BY confirmed_at DESC "
                "LIMIT 1",
                (
                    str(document_id),
                    candidate_index,
                    ConfirmationStatus.CONFIRMED.value,
                ),
            ).fetchone()
            if row is None:
                return None
            return self._row_to_domain(row)
        finally:
            conn.close()

    def get_history(
        self, document_id: UUID, candidate_index: int
    ) -> list[ConfirmedReferenceEvent]:
        """Get full confirmation audit trail, newest first."""
        return self.get_by_candidate_index(document_id, candidate_index)

    def get_by_candidate_index(
        self, document_id: UUID, candidate_index: int
    ) -> list[ConfirmedReferenceEvent]:
        """Get all confirmations for a document+candidate, newest first."""
        conn = get_connection(self._db_path)
        try:
            rows = conn.execute(
                "SELECT * FROM confirmed_reference_events "
                "WHERE document_id = ? "
                "AND deadline_candidate_index = ? "
                "ORDER BY confirmed_at DESC",
                (str(document_id), candidate_index),
            ).fetchall()

            return [self._row_to_domain(row) for row in rows]
        finally:
            conn.close()

    def _row_to_domain(self, row: sqlite3.Row) -> ConfirmedReferenceEvent:
        """Map a database row to a domain object."""
        confirmed_date_str = row["confirmed_date"]
        confirmed_date_val: date | None = (
            date.fromisoformat(confirmed_date_str) if confirmed_date_str else None
        )

        # Parse confirmation_status safely
        try:
            status_str = row["confirmation_status"]
        except (KeyError, IndexError):
            status_str = "unconfirmed"
        try:
            confirmation_status = ConfirmationStatus(status_str)
        except ValueError:
            confirmation_status = ConfirmationStatus.UNCONFIRMED

        # Parse confirmation_method safely (handle legacy "superseded_marked")
        method_str = row["confirmation_method"] or ""
        if method_str == "superseded_marked":
            method_str = ConfirmationMethod.AUTO_SUGGESTED.value
        try:
            confirmation_method = ConfirmationMethod(method_str)
        except ValueError:
            confirmation_method = ConfirmationMethod.AUTO_SUGGESTED

        confirmed_at_str = row["confirmed_at"]
        confirmed_at: datetime | None = (
            datetime.fromisoformat(confirmed_at_str) if confirmed_at_str else None
        )

        return ConfirmedReferenceEvent(
            confirmation_id=UUID(row["confirmation_id"]),
            candidate_id=UUID(row["candidate_id"]) if row["candidate_id"] else None,
            document_id=UUID(row["document_id"]),
            event_type=EventType(row["event_type"]),
            confirmed_date=confirmed_date_val,
            source_type=SourceType(row["source_type"]),
            confirmation_method=confirmation_method,
            confirmation_status=confirmation_status,
            confirmed_at=confirmed_at,
            confirmed_by=row["confirmed_by"] or "",
            supersedes_confirmation_id=(
                UUID(row["supersedes_confirmation_id"])
                if row["supersedes_confirmation_id"]
                else None
            ),
        )
