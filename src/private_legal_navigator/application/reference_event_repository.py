"""Repository port (interface) for reference event persistence."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from private_legal_navigator.domain.reference_event import (
    ConfirmedReferenceEvent,
)


class IdempotencyKeyConflictError(Exception):
    """Raised when an idempotency key has already been claimed."""

    def __init__(self, idempotency_key: str) -> None:
        super().__init__("Idempotency key already exists")
        self.idempotency_key = idempotency_key


@dataclass
class IdempotencyRecord:
    """Represents a recorded idempotency outcome."""

    idempotency_key: str
    operation_type: str
    target_document_id: str
    target_candidate_index: int
    payload_digest: str
    status: str  # 'processing', 'completed', 'conflict'
    result_confirmation_id: str | None
    created_at: str
    completed_at: str | None
    expires_at: str


class ReferenceEventRepository(ABC):
    """Abstract repository for confirmed reference events.

    Responsible for persisting ConfirmedReferenceEvent records and
    retrieving confirmation history for audit trail purposes.
    """

    @abstractmethod
    def save_confirmation(self, event: ConfirmedReferenceEvent, *, is_revoke: bool = False) -> None:
        """Persist a confirmed reference event.

        Args:
            event: The confirmed reference event to persist.
            is_revoke: True if this event represents a revocation.
        """
        ...

    @abstractmethod
    def save_confirmation_in_conn(
        self, conn: object, event: ConfirmedReferenceEvent, *, is_revoke: bool = False
    ) -> None:
        """Persist a confirmed reference event inside an existing transaction.

        Caller owns BEGIN / COMMIT / ROLLBACK on *conn*.
        """
        ...

    @abstractmethod
    def get_confirmation(self, confirmation_id: UUID) -> ConfirmedReferenceEvent | None:
        """Retrieve a confirmation by its ID.

        Args:
            confirmation_id: The confirmation identifier.

        Returns:
            ConfirmedReferenceEvent if found, None otherwise.
        """
        ...

    @abstractmethod
    def get_history_for_candidate(
        self, document_id: UUID, deadline_candidate_index: int
    ) -> list[ConfirmedReferenceEvent]:
        """Get full confirmation history for a deadline candidate.

        Returns all confirmations sorted by confirmed_at descending,
        including CONFIRMED, SUPERSEDED, REJECTED, and REVOKED records.

        Args:
            document_id: The document identifier.
            deadline_candidate_index: The M5 deadline candidate index (0-based).

        Returns:
            List of ConfirmedReferenceEvent records (may be empty).
        """
        ...

    @abstractmethod
    def get_active_confirmation(
        self, document_id: UUID, deadline_candidate_index: int
    ) -> ConfirmedReferenceEvent | None:
        """Get the currently active (CONFIRMED) confirmation.

        Returns None if no active confirmation exists (e.g., all
        are REJECTED, REVOKED, or nothing confirmed yet).

        Args:
            document_id: The document identifier.
            deadline_candidate_index: The M5 deadline candidate index (0-based).

        Returns:
            The active ConfirmedReferenceEvent, or None.
        """
        ...

    @abstractmethod
    def delete_by_document(self, document_id: UUID) -> None:
        """Delete all confirmations for a document (CASCADE DELETE).

        Called when a document is deleted.

        Args:
            document_id: The document identifier.
        """
        ...

    # ── Idempotency methods (M6-UI Slice 2) ──

    @abstractmethod
    def claim_idempotency_key(
        self,
        idempotency_key: str,
        operation_type: str,
        document_id: UUID,
        deadline_candidate_index: int,
        payload_digest: str = "",
    ) -> IdempotencyRecord:
        """Atomically claim an idempotency key.

        INSERTs a new record with status='processing'.
        Raises an exception if the key already exists.

        Args:
            idempotency_key: The unique idempotency key.
            operation_type: 'confirm', 'reject', or 'manual_confirm'.
            document_id: The document this action targets.
            deadline_candidate_index: The candidate index.
            payload_digest: SHA-256 digest of the canonical operation payload.

        Returns:
            The newly created IdempotencyRecord.

        Raises:
            IdempotencyKeyConflict: If the key already exists.
        """
        ...

    @abstractmethod
    def get_idempotency_record(self, idempotency_key: str) -> IdempotencyRecord | None:
        """Retrieve an idempotency record by key.

        Args:
            idempotency_key: The unique idempotency key.

        Returns:
            IdempotencyRecord if found, None otherwise.
        """
        ...

    @abstractmethod
    def complete_idempotency_key(self, idempotency_key: str, result_confirmation_id: str) -> None:
        """Mark an idempotency record as completed.

        Args:
            idempotency_key: The unique idempotency key.
            result_confirmation_id: The confirmation_id of the domain mutation result.
        """
        ...

    @abstractmethod
    def mark_idempotency_conflict(self, idempotency_key: str) -> None:
        """Mark an idempotency record as conflict (non-retryable error).

        Args:
            idempotency_key: The unique idempotency key.
        """
        ...

    @abstractmethod
    def cleanup_expired_idempotency_records(self) -> int:
        """Delete expired idempotency records.

        Returns:
            Number of records deleted.
        """
        ...

    @abstractmethod
    def execute_atomic_with_idempotency(
        self,
        *,
        idempotency_key: str,
        operation_type: str,
        payload_digest: str,
        document_id: UUID,
        deadline_candidate_index: int,
        perform_mutation: Callable[..., Any],
    ) -> tuple[ConfirmedReferenceEvent, bool]:
        """Execute a domain mutation inside a single atomic transaction.

        Sequence: BEGIN → claim → load active → mutate → complete → COMMIT.
        Returns (event, was_replay).
        """
        ...
