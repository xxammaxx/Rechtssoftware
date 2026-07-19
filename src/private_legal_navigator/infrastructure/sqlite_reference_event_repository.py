"""SQLite implementation of the ReferenceEventRepository port."""

import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from private_legal_navigator.application.reference_event_repository import (
    IdempotencyKeyConflictError,
    IdempotencyRecord,
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

    Uses parametrized queries exclusively. Supports optional shared
    connection parameter for transactional atomicity.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def initialize_schema(self) -> None:
        """Idempotent schema initialization (delegates to database.py)."""
        initialize_schema(self._db_path)

    def save_confirmation(self, event: ConfirmedReferenceEvent) -> None:
        conn = get_connection(self._db_path)
        try:
            self._save_confirmation_in_conn(conn, event)
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _save_confirmation_in_conn(
        conn: sqlite3.Connection, event: ConfirmedReferenceEvent
    ) -> None:
        """Execute INSERT within an existing connection (caller owns commit)."""
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

    def get_confirmation(self, confirmation_id: uuid.UUID) -> ConfirmedReferenceEvent | None:
        conn = get_connection(self._db_path)
        try:
            return self._get_confirmation_in_conn(conn, confirmation_id)
        finally:
            conn.close()

    @staticmethod
    def _get_confirmation_in_conn(
        conn: sqlite3.Connection, confirmation_id: uuid.UUID
    ) -> ConfirmedReferenceEvent | None:
        row = conn.execute(
            """
            SELECT * FROM confirmed_reference_events
            WHERE confirmation_id = ?
            """,
            (str(confirmation_id),),
        ).fetchone()
        if row is None:
            return None
        return SqliteReferenceEventRepository._row_to_event(row)

    def get_history_for_candidate(
        self, document_id: uuid.UUID, deadline_candidate_index: int
    ) -> list[ConfirmedReferenceEvent]:
        conn = get_connection(self._db_path)
        try:
            return self._get_history_in_conn(conn, document_id, deadline_candidate_index)
        finally:
            conn.close()

    @staticmethod
    def _get_history_in_conn(
        conn: sqlite3.Connection, document_id: uuid.UUID, deadline_candidate_index: int
    ) -> list[ConfirmedReferenceEvent]:
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
        return [SqliteReferenceEventRepository._row_to_event(row) for row in rows]

    def get_active_confirmation(
        self, document_id: uuid.UUID, deadline_candidate_index: int
    ) -> ConfirmedReferenceEvent | None:
        conn = get_connection(self._db_path)
        try:
            return self._get_active_confirmation_in_conn(
                conn, document_id, deadline_candidate_index
            )
        finally:
            conn.close()

    @staticmethod
    def _get_active_confirmation_in_conn(
        conn: sqlite3.Connection, document_id: uuid.UUID, deadline_candidate_index: int
    ) -> ConfirmedReferenceEvent | None:
        # Active = most recent unsuperseded record
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
        return SqliteReferenceEventRepository._row_to_event(row)

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

    # ── Idempotency methods ──────────────────────────────────────────

    def claim_idempotency_key(
        self,
        idempotency_key: str,
        operation_type: str,
        document_id: uuid.UUID,
        deadline_candidate_index: int,
    ) -> IdempotencyRecord:
        """Atomically claim an idempotency key.

        Uses INSERT with PRIMARY KEY constraint as natural race-condition guard.
        Must be called within an existing transaction.
        """
        conn = get_connection(self._db_path)
        try:
            now = datetime.now(UTC).isoformat()

            conn.execute(
                """
                INSERT INTO idempotency_records
                    (idempotency_key, operation_type, target_document_id,
                     target_candidate_index, status, created_at, expires_at)
                VALUES (?, ?, ?, ?, 'processing', ?, datetime('now', '+1 day'))
                """,
                (
                    idempotency_key,
                    operation_type,
                    str(document_id),
                    deadline_candidate_index,
                    now,
                ),
            )
            conn.commit()
            return IdempotencyRecord(
                idempotency_key=idempotency_key,
                operation_type=operation_type,
                target_document_id=str(document_id),
                target_candidate_index=deadline_candidate_index,
                status="processing",
                result_confirmation_id=None,
                created_at=now,
                completed_at=None,
                expires_at="",
            )
        except sqlite3.IntegrityError:
            raise IdempotencyKeyConflictError(idempotency_key) from None
        finally:
            conn.close()

    def get_idempotency_record(self, idempotency_key: str) -> IdempotencyRecord | None:
        conn = get_connection(self._db_path)
        try:
            row = conn.execute(
                "SELECT * FROM idempotency_records WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            if row is None:
                return None
            return IdempotencyRecord(
                idempotency_key=row["idempotency_key"],
                operation_type=row["operation_type"],
                target_document_id=row["target_document_id"],
                target_candidate_index=row["target_candidate_index"],
                status=row["status"],
                result_confirmation_id=row["result_confirmation_id"],
                created_at=row["created_at"],
                completed_at=row["completed_at"],
                expires_at=row["expires_at"],
            )
        finally:
            conn.close()

    def complete_idempotency_key(self, idempotency_key: str, result_confirmation_id: str) -> None:
        conn = get_connection(self._db_path)
        try:
            now = datetime.now(UTC).isoformat()
            conn.execute(
                """
                UPDATE idempotency_records
                SET status = 'completed',
                    result_confirmation_id = ?,
                    completed_at = ?
                WHERE idempotency_key = ?
                """,
                (result_confirmation_id, now, idempotency_key),
            )
            conn.commit()
        finally:
            conn.close()

    def mark_idempotency_conflict(self, idempotency_key: str) -> None:
        conn = get_connection(self._db_path)
        try:
            now = datetime.now(UTC).isoformat()
            conn.execute(
                """
                UPDATE idempotency_records
                SET status = 'conflict', completed_at = ?
                WHERE idempotency_key = ?
                """,
                (now, idempotency_key),
            )
            conn.commit()
        finally:
            conn.close()

    def cleanup_expired_idempotency_records(self) -> int:
        conn = get_connection(self._db_path)
        try:
            cursor = conn.execute(
                "DELETE FROM idempotency_records WHERE expires_at < datetime('now')"
            )
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    # ── Internal helpers ─────────────────────────────────────────────

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
