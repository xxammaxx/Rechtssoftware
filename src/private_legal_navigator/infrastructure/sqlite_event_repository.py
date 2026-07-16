"""SQLite persistence for confirmed reference events (M6-A Variant B)."""

import sqlite3
from datetime import date, datetime
from pathlib import Path
from uuid import UUID

from private_legal_navigator.application.event_repository import ReferenceEventRepository
from private_legal_navigator.domain.calendar import (
    ConfirmationMethod,
    ConfirmedReferenceEvent,
    EventType,
    SourceType,
)
from private_legal_navigator.infrastructure.database import get_connection

CREATE_CONFIRMED_REFERENCE_EVENTS_TABLE = """
CREATE TABLE IF NOT EXISTS confirmed_reference_events (
    confirmation_id TEXT PRIMARY KEY,
    candidate_id TEXT,
    document_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    confirmed_date TEXT,
    source_type TEXT NOT NULL DEFAULT 'auto_detected',
    confirmation_method TEXT NOT NULL,
    confirmed_at TEXT NOT NULL,
    confirmed_by TEXT NOT NULL DEFAULT '',
    supersedes_confirmation_id TEXT
)
"""

CREATE_CONFIRMED_EVENTS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_confirmed_events_document "
    "ON confirmed_reference_events(document_id)",
    "CREATE INDEX IF NOT EXISTS idx_confirmed_events_doc_status "
    "ON confirmed_reference_events(document_id, confirmation_method)",
]


class SqliteEventRepository(ReferenceEventRepository):
    """SQLite-based persistence for confirmed reference events."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def initialize_schema(self) -> None:
        """Create the confirmed_reference_events table if it doesn't exist (idempotent)."""
        conn = get_connection(self._db_path)
        try:
            conn.execute(CREATE_CONFIRMED_REFERENCE_EVENTS_TABLE)
            for index_sql in CREATE_CONFIRMED_EVENTS_INDEXES:
                conn.execute(index_sql)
            conn.commit()
        finally:
            conn.close()

    def save(self, event: ConfirmedReferenceEvent) -> None:
        """Store a confirmed reference event.

        If a CONFIRMED event already exists for the same candidate_id,
        it is marked as SUPERSEDED first.
        """
        conn = get_connection(self._db_path)
        try:
            # Supersede any existing CONFIRMED confirmation for the same candidate
            if event.candidate_id is not None:
                conn.execute(
                    "UPDATE confirmed_reference_events "
                    "SET confirmation_method = ? "
                    "WHERE candidate_id = ? "
                    "AND confirmation_method IN (?, ?, ?) "
                    "AND supersedes_confirmation_id IS NULL",
                    (
                        "superseded_marked",
                        str(event.candidate_id),
                        ConfirmationMethod.AUTO_SUGGESTED.value,
                        ConfirmationMethod.MANUALLY_ENTERED.value,
                        ConfirmationMethod.CORRECTED.value,
                    ),
                )
            # If revoking: mark prior as superseded
            if event.supersedes_confirmation_id is not None:
                conn.execute(
                    "UPDATE confirmed_reference_events "
                    "SET confirmation_method = ? "
                    "WHERE confirmation_id = ?",
                    (
                        "superseded_marked",
                        str(event.supersedes_confirmation_id),
                    ),
                )

            conn.execute(
                "INSERT INTO confirmed_reference_events "
                "(confirmation_id, candidate_id, document_id, event_type, "
                "confirmed_date, source_type, confirmation_method, "
                "confirmed_at, confirmed_by, supersedes_confirmation_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    str(event.confirmation_id),
                    str(event.candidate_id) if event.candidate_id else None,
                    str(event.document_id),
                    event.event_type.value,
                    event.confirmed_date.isoformat() if event.confirmed_date else None,
                    event.source_type.value,
                    event.confirmation_method.value,
                    event.confirmed_at.isoformat(),
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

    def get_active(self, document_id: UUID, candidate_index: int) -> ConfirmedReferenceEvent | None:
        """Get the currently active (CONFIRMED) event for a document and candidate.

        Returns the most recent confirmation with a valid confirmed_date,
        superseding those marked as revoked/superseded.
        """
        conn = get_connection(self._db_path)
        try:
            rows = conn.execute(
                "SELECT * FROM confirmed_reference_events "
                "WHERE document_id = ? "
                "AND confirmed_date IS NOT NULL "
                "ORDER BY confirmed_at DESC",
                (str(document_id),),
            ).fetchall()

            if not rows:
                return None

            # Return the most recent row that has a confirmed_date
            # and whose confirmation_method hasn't been superseded
            for row in rows:
                method = row["confirmation_method"] or ""
                # Skip rows that were superseded (marked by save)
                if method == "superseded_marked":
                    continue
                event = self._row_to_domain(row)
                if event.confirmed_date is not None:
                    return event
            return None
        finally:
            conn.close()

    def get_history(self, document_id: UUID, candidate_index: int) -> list[ConfirmedReferenceEvent]:
        """Get full confirmation audit trail, newest first."""
        return self.get_by_candidate_index(document_id, candidate_index)

    def get_by_candidate_index(
        self, document_id: UUID, candidate_index: int
    ) -> list[ConfirmedReferenceEvent]:
        """Get all confirmations for a document, newest first, deduplicating
        superseded rows."""
        conn = get_connection(self._db_path)
        try:
            rows = conn.execute(
                "SELECT * FROM confirmed_reference_events "
                "WHERE document_id = ? "
                "ORDER BY confirmed_at DESC",
                (str(document_id),),
            ).fetchall()

            results: list[ConfirmedReferenceEvent] = []
            seen_superseded: set[str] = set()

            for row in rows:
                method = row["confirmation_method"] or ""
                confirmation_id = row["confirmation_id"]

                # Skip records that were marked as internally superseded
                if method == "superseded_marked":
                    seen_superseded.add(confirmation_id)
                    continue

                event = self._row_to_domain(row)
                results.append(event)

            return results
        finally:
            conn.close()

    def _row_to_domain(self, row: sqlite3.Row) -> ConfirmedReferenceEvent:
        """Map a database row to a domain object."""
        confirmed_date_str = row["confirmed_date"]
        confirmed_date_val: date | None = (
            date.fromisoformat(confirmed_date_str) if confirmed_date_str else None
        )

        return ConfirmedReferenceEvent(
            confirmation_id=UUID(row["confirmation_id"]),
            candidate_id=UUID(row["candidate_id"]) if row["candidate_id"] else None,
            document_id=UUID(row["document_id"]),
            event_type=EventType(row["event_type"]),
            confirmed_date=confirmed_date_val,
            source_type=SourceType(row["source_type"]),
            confirmation_method=ConfirmationMethod(row["confirmation_method"])
            if row["confirmation_method"] not in ("", "superseded_marked")
            else ConfirmationMethod.AUTO_SUGGESTED,
            confirmed_at=datetime.fromisoformat(row["confirmed_at"]),
            confirmed_by=row["confirmed_by"] or "",
            supersedes_confirmation_id=(
                UUID(row["supersedes_confirmation_id"])
                if row["supersedes_confirmation_id"]
                else None
            ),
        )
