"""SQLite implementation of the ReferenceEventRepository port."""

import contextlib
import sqlite3
import uuid
from collections.abc import Callable
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

    def save_confirmation(self, event: ConfirmedReferenceEvent, *, is_revoke: bool = False) -> None:
        conn = get_connection(self._db_path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            self._save_confirmation_in_conn(conn, event, is_revoke=is_revoke)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def save_confirmation_in_conn(
        self, conn: object, event: ConfirmedReferenceEvent, *, is_revoke: bool = False
    ) -> None:
        """Persist inside an existing transaction (caller owns commit)."""
        self._save_confirmation_in_conn(conn, event, is_revoke=is_revoke)  # type: ignore[arg-type]

    @staticmethod
    def _save_confirmation_in_conn(
        conn: sqlite3.Connection,
        event: ConfirmedReferenceEvent,
        *,
        is_revoke: bool = False,
    ) -> None:
        """Execute INSERT within an existing connection (caller owns commit)."""
        confirmed_date_str = event.confirmed_date.isoformat() if event.confirmed_date else None
        supersedes_str = (
            str(event.supersedes_confirmation_id) if event.supersedes_confirmation_id else None
        )
        is_revoke_int = 1 if is_revoke else 0

        conn.execute(
            """
            INSERT INTO confirmed_reference_events
                (confirmation_id, candidate_id, document_id, deadline_candidate_index,
                 event_type, confirmed_date, source_type, confirmation_method,
                 confirmed_at, confirmed_by, evidence_note, supersedes_confirmation_id,
                 is_revoke)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                is_revoke_int,
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
        # Active = most recent unsuperseded, non-revoked record
        row = conn.execute(
            """
            SELECT * FROM confirmed_reference_events
            WHERE document_id = ?
              AND deadline_candidate_index = ?
              AND is_revoke = 0
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
        payload_digest: str = "",
    ) -> IdempotencyRecord:
        """Atomically claim an idempotency key (legacy — standalone conn).

        Prefer ``execute_atomic_with_idempotency`` for new callers.
        """
        conn = get_connection(self._db_path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            record = self._claim_idempotency_key_in_conn(
                conn,
                idempotency_key,
                operation_type,
                document_id,
                deadline_candidate_index,
                payload_digest,
            )
            conn.commit()
            return record
        except sqlite3.IntegrityError:
            conn.rollback()
            raise IdempotencyKeyConflictError(idempotency_key) from None
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def _claim_idempotency_key_in_conn(
        conn: sqlite3.Connection,
        idempotency_key: str,
        operation_type: str,
        document_id: uuid.UUID,
        deadline_candidate_index: int,
        payload_digest: str = "",
    ) -> IdempotencyRecord:
        """INSERT idempotency claim inside an existing transaction.

        Caller owns BEGIN / COMMIT / ROLLBACK.
        """
        now = datetime.now(UTC).isoformat()
        conn.execute(
            """
            INSERT INTO idempotency_records
                (idempotency_key, operation_type, target_document_id,
                 target_candidate_index, payload_digest, status,
                 created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, 'processing', ?, datetime('now', '+1 day'))
            """,
            (
                idempotency_key,
                operation_type,
                str(document_id),
                deadline_candidate_index,
                payload_digest,
                now,
            ),
        )
        return IdempotencyRecord(
            idempotency_key=idempotency_key,
            operation_type=operation_type,
            target_document_id=str(document_id),
            target_candidate_index=deadline_candidate_index,
            payload_digest=payload_digest,
            status="processing",
            result_confirmation_id=None,
            created_at=now,
            completed_at=None,
            expires_at="",
        )

    def get_idempotency_record(self, idempotency_key: str) -> IdempotencyRecord | None:
        conn = get_connection(self._db_path)
        try:
            return self._get_idempotency_record_in_conn(conn, idempotency_key)
        finally:
            conn.close()

    @staticmethod
    def _get_idempotency_record_in_conn(
        conn: sqlite3.Connection, idempotency_key: str
    ) -> IdempotencyRecord | None:
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
            payload_digest=row["payload_digest"] or "",
            status=row["status"],
            result_confirmation_id=row["result_confirmation_id"],
            created_at=row["created_at"],
            completed_at=row["completed_at"],
            expires_at=row["expires_at"],
        )

    def complete_idempotency_key(self, idempotency_key: str, result_confirmation_id: str) -> None:
        conn = get_connection(self._db_path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            self._complete_idempotency_key_in_conn(conn, idempotency_key, result_confirmation_id)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def _complete_idempotency_key_in_conn(
        conn: sqlite3.Connection, idempotency_key: str, result_confirmation_id: str
    ) -> None:
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

    def mark_idempotency_conflict(self, idempotency_key: str) -> None:
        conn = get_connection(self._db_path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            self._mark_idempotency_conflict_in_conn(conn, idempotency_key)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def _mark_idempotency_conflict_in_conn(conn: sqlite3.Connection, idempotency_key: str) -> None:
        now = datetime.now(UTC).isoformat()
        conn.execute(
            """
            UPDATE idempotency_records
            SET status = 'conflict', completed_at = ?
            WHERE idempotency_key = ?
            """,
            (now, idempotency_key),
        )

    # ── Atomic transaction orchestration ───────────────────────────

    def execute_atomic_with_idempotency(
        self,
        *,
        idempotency_key: str,
        operation_type: str,
        payload_digest: str,
        document_id: uuid.UUID,
        deadline_candidate_index: int,
        perform_mutation: Callable[[sqlite3.Connection, object | None], ConfirmedReferenceEvent],
    ) -> tuple[ConfirmedReferenceEvent, bool]:
        """Execute a domain mutation inside a single atomic transaction.

        Sequence:
            1. BEGIN IMMEDIATE
            2. Claim idempotency key (INSERT → serialises concurrent attempts)
            3. Load currently-active confirmation (TOCTOU-safe: same TX)
            4. Perform domain mutation (caller-supplied)
            5. Mark idempotency as completed
            6. COMMIT

        On IntegrityError from the idempotency INSERT:
            - Reads existing record (outside TX)
            - If completed + payload matches → replay (returns existing result)
            - If completed + payload mismatch → raises 409
            - If still processing / conflict → raises 409

        Returns:
            (event, was_replay) — ``was_replay`` is True when the result
            comes from a previously completed idempotency record.
        """
        conn = get_connection(self._db_path)
        try:
            conn.execute("BEGIN IMMEDIATE")

            # Step 1: Claim idempotency key (INSERT)
            try:
                self._claim_idempotency_key_in_conn(
                    conn,
                    idempotency_key,
                    operation_type,
                    document_id,
                    deadline_candidate_index,
                    payload_digest,
                )
            except sqlite3.IntegrityError:
                conn.rollback()
                # Read the existing record to decide how to respond
                return self._handle_existing_idempotency(
                    idempotency_key, payload_digest, operation_type
                )

            # Step 2: Load active confirmation (same TX → TOCTOU-safe)
            active = self._get_active_confirmation_in_conn(
                conn, document_id, deadline_candidate_index
            )

            # Step 3: Perform domain mutation (caller-supplied)
            try:
                event = perform_mutation(conn, active)
            except Exception:
                conn.rollback()
                # Best-effort: mark idempotency as conflict (separate conn)
                with contextlib.suppress(Exception):
                    self.mark_idempotency_conflict(idempotency_key)
                raise

            # Step 4: Mark idempotency as completed
            self._complete_idempotency_key_in_conn(
                conn, idempotency_key, str(event.confirmation_id)
            )

            conn.commit()
            return event, False

        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _handle_existing_idempotency(
        self,
        idempotency_key: str,
        expected_payload_digest: str,
        operation_type: str,
    ) -> tuple[ConfirmedReferenceEvent, bool]:
        """Inspect an existing idempotency record and respond accordingly.

        Returns (event, was_replay) on successful replay.
        Raises IdempotencyKeyConflictError on mismatch or non-completed state.
        """
        existing = self.get_idempotency_record(idempotency_key)

        if existing is None:
            raise IdempotencyKeyConflictError(idempotency_key)

        if existing.status != "completed":
            raise IdempotencyKeyConflictError(idempotency_key)

        # Payload binding — reject if the digest doesn't match
        if existing.payload_digest and existing.payload_digest != expected_payload_digest:
            raise IdempotencyKeyConflictError(idempotency_key)

        # Operation type must also match
        if existing.operation_type != operation_type:
            raise IdempotencyKeyConflictError(idempotency_key)

        result_id = existing.result_confirmation_id
        if result_id:
            original = self.get_confirmation(uuid.UUID(result_id))
            if original:
                return original, True

        raise IdempotencyKeyConflictError(idempotency_key)

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
            is_revoke=bool(row["is_revoke"]) if "is_revoke" in row else False,
        )
