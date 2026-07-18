"""SQLite implementation of the ReferenceEventRepository port."""

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

from private_legal_navigator.application.reference_event_repository import (
    ReferenceEventRepository,
)
from private_legal_navigator.domain.reference_event import (
    ConfirmationMethod,
    ConfirmedReferenceEvent,
    EventType,
    SourceType,
)
from private_legal_navigator.infrastructure.database import get_connection, initialize_schema


class SqliteReferenceEventRepository(ReferenceEventRepository):
    """SQLite-backed implementation of ReferenceEventRepository.

    Uses parametrized queries exclusively. Each method opens and closes
    its own connection to avoid threading issues.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def initialize_schema(self) -> None:
        """Idempotent schema initialization (delegates to database.py)."""
        initialize_schema(self._db_path)

    def save_confirmation(self, event: ConfirmedReferenceEvent) -> None:
        conn = get_connection(self._db_path)
        try:
            confirmed_date_str = event.confirmed_date.isoformat() if event.confirmed_date else None
            supersedes_str = (
                str(event.supersedes_confirmation_id) if event.supersedes_confirmation_id else None
            )

            conn.execute(
                """
                INSERT INTO confirmed_reference_events
                    (confirmation_id, candidate_id, document_id, deadline_candidate_index,
                     event_type, confirmed_date, source_type, confirmation_method,
                     confirmed_at, confirmed_by, evidence_note, supersedes_confirmation_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(event.confirmation_id),
                    str(event.candidate_id) if event.candidate_id else None,
                    str(event.document_id),
                    event.deadline_candidate_index,
                    event.event_type.value,
                    confirmed_date_str,
                    event.source_type.value,
                    event.confirmation_method.value,
                    event.confirmed_at.isoformat(),
                    event.confirmed_by,
                    event.evidence_note,
                    supersedes_str,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_confirmation(self, confirmation_id: uuid.UUID) -> ConfirmedReferenceEvent | None:
        conn = get_connection(self._db_path)
        try:
            row = conn.execute(
                """
                SELECT * FROM confirmed_reference_events
                WHERE confirmation_id = ?
                """,
                (str(confirmation_id),),
            ).fetchone()
            if row is None:
                return None
            return self._row_to_event(row)
        finally:
            conn.close()

    def get_history_for_candidate(
        self, document_id: uuid.UUID, deadline_candidate_index: int
    ) -> list[ConfirmedReferenceEvent]:
        conn = get_connection(self._db_path)
        try:
            rows = conn.execute(
                """
                SELECT * FROM confirmed_reference_events
                WHERE document_id = ? AND deadline_candidate_index = ?
                ORDER BY
                    CASE WHEN evidence_note != '' THEN 0 ELSE 1 END,
                    confirmed_at DESC
                """,
                (str(document_id), deadline_candidate_index),
            ).fetchall()
            return [self._row_to_event(row) for row in rows]
        finally:
            conn.close()

    def get_active_confirmation(
        self, document_id: uuid.UUID, deadline_candidate_index: int
    ) -> ConfirmedReferenceEvent | None:
        conn = get_connection(self._db_path)
        try:
            # Active = most recent CONFIRMED record for this candidate that
            # has NOT been superseded or revoked
            row = conn.execute(
                """
                SELECT * FROM confirmed_reference_events
                WHERE document_id = ?
                  AND deadline_candidate_index = ?
                  AND confirmation_id NOT IN (
                      SELECT COALESCE(supersedes_confirmation_id, '')
                      FROM confirmed_reference_events
                      WHERE supersedes_confirmation_id IS NOT NULL
                  )
                ORDER BY confirmed_at DESC
                LIMIT 1
                """,
                (str(document_id), deadline_candidate_index),
            ).fetchone()
            if row is None:
                return None
            return self._row_to_event(row)
        finally:
            conn.close()

    def delete_by_document(self, document_id: uuid.UUID) -> None:
        conn = get_connection(self._db_path)
        try:
            conn.execute(
                "DELETE FROM confirmed_reference_events WHERE document_id = ?",
                (str(document_id),),
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> ConfirmedReferenceEvent:
        """Convert a SQLite row to a ConfirmedReferenceEvent."""
        confirmed_date = (
            datetime.strptime(row["confirmed_date"], "%Y-%m-%d").date()
            if row["confirmed_date"]
            else None
        )
        confirmed_at = datetime.fromisoformat(row["confirmed_at"])

        candidate_id = uuid.UUID(row["candidate_id"]) if row["candidate_id"] else None
        supersedes_id = (
            uuid.UUID(row["supersedes_confirmation_id"])
            if row["supersedes_confirmation_id"]
            else None
        )

        return ConfirmedReferenceEvent(
            confirmation_id=uuid.UUID(row["confirmation_id"]),
            document_id=uuid.UUID(row["document_id"]),
            deadline_candidate_index=row["deadline_candidate_index"],
            event_type=EventType(row["event_type"]),
            confirmed_at=confirmed_at,
            confirmed_date=confirmed_date,
            source_type=SourceType(row["source_type"]),
            confirmation_method=ConfirmationMethod(row["confirmation_method"]),
            candidate_id=candidate_id,
            confirmed_by=row["confirmed_by"],
            evidence_note=row["evidence_note"],
            supersedes_confirmation_id=supersedes_id,
        )
