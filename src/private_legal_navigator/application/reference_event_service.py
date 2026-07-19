"""Application service for reference event lifecycle management.

Orchestrates the reference event use cases:
  1. List reference event candidates for an M5 deadline candidate
  2. Confirm/reject/revoke a reference event
  3. Get confirmation history
  4. Idempotency-protected confirmation actions (M6-UI)
"""

import contextlib
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime

from private_legal_navigator.application.reference_event_repository import (
    IdempotencyKeyConflictError,
    ReferenceEventRepository,
)
from private_legal_navigator.domain.reference_event import (
    ConfirmationMethod,
    ConfirmedReferenceEvent,
    EventType,
    ReferenceEventCandidate,
    SourceType,
)


@dataclass
class ConfirmationActionResult:
    """Result of a confirmation action with idempotency metadata."""

    event: ConfirmedReferenceEvent
    was_replay: bool
    redirect_path: str
    result_status: str  # 'confirmed', 'rejected'


class ReferenceEventService:
    """Application service for reference event lifecycle management."""

    def __init__(self, repo: ReferenceEventRepository) -> None:
        self._repo = repo

    def get_reference_event_candidates(
        self,
        document_id: uuid.UUID,
        deadline_candidate_index: int,
    ) -> list[ReferenceEventCandidate]:
        """Get reference event candidates for a deadline candidate."""
        return self._detect_candidates(document_id, deadline_candidate_index)

    def confirm(
        self,
        document_id: uuid.UUID,
        deadline_candidate_index: int,
        event_type: EventType,
        confirmed_date: date,
        source_type: SourceType,
        confirmation_method: ConfirmationMethod,
        candidate_id: uuid.UUID | None = None,
        evidence_note: str = "",
        confirmed_by: str = "",
    ) -> ConfirmedReferenceEvent:
        """Confirm a reference event.

        Creates a new ConfirmedReferenceEvent. Supersedes any active
        confirmation for the same candidate.
        """
        now = datetime.now(UTC)
        confirmation_id = uuid.uuid4()

        active = self._repo.get_active_confirmation(document_id, deadline_candidate_index)

        event = ConfirmedReferenceEvent(
            confirmation_id=confirmation_id,
            document_id=document_id,
            deadline_candidate_index=deadline_candidate_index,
            event_type=event_type,
            confirmed_date=confirmed_date,
            source_type=source_type,
            confirmation_method=confirmation_method,
            confirmed_at=now,
            candidate_id=candidate_id,
            evidence_note=evidence_note,
            confirmed_by=confirmed_by,
            supersedes_confirmation_id=active.confirmation_id if active else None,
        )
        self._repo.save_confirmation(event)
        return event

    def reject(
        self,
        document_id: uuid.UUID,
        deadline_candidate_index: int,
        event_type: EventType,
        candidate_id: uuid.UUID | None = None,
        source_type: SourceType = SourceType.AUTO_DETECTED,
        confirmation_method: ConfirmationMethod = ConfirmationMethod.AUTO_SUGGESTED,
    ) -> ConfirmedReferenceEvent:
        """Reject a reference event candidate.

        Creates a REJECTED record and supersedes any existing active
        confirmation. confirmed_date=None marks this as REJECTED.
        """
        now = datetime.now(UTC)

        # Supersede existing active confirmation if any
        active = self._repo.get_active_confirmation(document_id, deadline_candidate_index)

        rejection = ConfirmedReferenceEvent(
            confirmation_id=uuid.uuid4(),
            document_id=document_id,
            deadline_candidate_index=deadline_candidate_index,
            event_type=event_type,
            confirmed_at=now,
            confirmed_date=None,
            source_type=source_type,
            confirmation_method=confirmation_method,
            candidate_id=candidate_id,
            supersedes_confirmation_id=active.confirmation_id if active else None,
        )
        self._repo.save_confirmation(rejection)
        return rejection

    # ── Idempotency-protected actions (M6-UI) ──────────────────────

    def confirm_with_idempotency(
        self,
        idempotency_key: str,
        document_id: uuid.UUID,
        deadline_candidate_index: int,
        event_type: EventType,
        confirmed_date: date,
        source_type: SourceType,
        confirmation_method: ConfirmationMethod,
        candidate_id: uuid.UUID | None = None,
        evidence_note: str = "",
        confirmed_by: str = "",
        redirect_path: str = "",
    ) -> ConfirmationActionResult:
        """Execute confirm with idempotency protection.

        Claims the idempotency key first, then executes the domain mutation.
        On replay: returns the original result without re-executing.
        On conflict: raises IdempotencyKeyConflict.
        """
        try:
            self._repo.claim_idempotency_key(
                idempotency_key=idempotency_key,
                operation_type="confirm",
                document_id=document_id,
                deadline_candidate_index=deadline_candidate_index,
            )
        except IdempotencyKeyConflictError:
            existing = self._repo.get_idempotency_record(idempotency_key)
            if existing and existing.status == "completed":
                result_id = existing.result_confirmation_id
                if result_id:
                    original = self._repo.get_confirmation(uuid.UUID(result_id))
                    if original:
                        return ConfirmationActionResult(
                            event=original,
                            was_replay=True,
                            redirect_path=redirect_path,
                            result_status="confirmed",
                        )
            raise

        try:
            event = self.confirm(
                document_id=document_id,
                deadline_candidate_index=deadline_candidate_index,
                event_type=event_type,
                confirmed_date=confirmed_date,
                source_type=source_type,
                confirmation_method=confirmation_method,
                candidate_id=candidate_id,
                evidence_note=evidence_note,
                confirmed_by=confirmed_by,
            )
        except Exception:
            with contextlib.suppress(Exception):
                self._repo.mark_idempotency_conflict(idempotency_key)
            raise

        with contextlib.suppress(Exception):
            self._repo.complete_idempotency_key(idempotency_key, str(event.confirmation_id))

        return ConfirmationActionResult(
            event=event,
            was_replay=False,
            redirect_path=redirect_path,
            result_status="confirmed",
        )

    def reject_with_idempotency(
        self,
        idempotency_key: str,
        document_id: uuid.UUID,
        deadline_candidate_index: int,
        event_type: EventType,
        candidate_id: uuid.UUID | None = None,
        redirect_path: str = "",
    ) -> ConfirmationActionResult:
        """Execute reject with idempotency protection."""
        try:
            self._repo.claim_idempotency_key(
                idempotency_key=idempotency_key,
                operation_type="reject",
                document_id=document_id,
                deadline_candidate_index=deadline_candidate_index,
            )
        except IdempotencyKeyConflictError:
            existing = self._repo.get_idempotency_record(idempotency_key)
            if existing and existing.status == "completed":
                result_id = existing.result_confirmation_id
                if result_id:
                    original = self._repo.get_confirmation(uuid.UUID(result_id))
                    if original:
                        return ConfirmationActionResult(
                            event=original,
                            was_replay=True,
                            redirect_path=redirect_path,
                            result_status="rejected",
                        )
            raise

        try:
            event = self.reject(
                document_id=document_id,
                deadline_candidate_index=deadline_candidate_index,
                event_type=event_type,
                candidate_id=candidate_id,
            )
        except Exception:
            with contextlib.suppress(Exception):
                self._repo.mark_idempotency_conflict(idempotency_key)
            raise

        with contextlib.suppress(Exception):
            self._repo.complete_idempotency_key(idempotency_key, str(event.confirmation_id))

        return ConfirmationActionResult(
            event=event,
            was_replay=False,
            redirect_path=redirect_path,
            result_status="rejected",
        )

    def revoke(
        self,
        confirmation_id: uuid.UUID,
    ) -> ConfirmedReferenceEvent | None:
        """Revoke a previous confirmation. Creates a REVOKED record."""
        existing = self._repo.get_confirmation(confirmation_id)
        if existing is None:
            return None

        now = datetime.now(UTC)
        revoked = ConfirmedReferenceEvent(
            confirmation_id=uuid.uuid4(),
            document_id=existing.document_id,
            deadline_candidate_index=existing.deadline_candidate_index,
            event_type=existing.event_type,
            confirmed_date=existing.confirmed_date,
            source_type=existing.source_type,
            confirmation_method=existing.confirmation_method,
            confirmed_at=now,
            candidate_id=existing.candidate_id,
            supersedes_confirmation_id=confirmation_id,
        )
        self._repo.save_confirmation(revoked)
        return revoked

    def get_history(
        self,
        document_id: uuid.UUID,
        deadline_candidate_index: int,
    ) -> list[ConfirmedReferenceEvent]:
        """Get confirmation history for a deadline candidate."""
        return self._repo.get_history_for_candidate(document_id, deadline_candidate_index)

    def cleanup_idempotency(self) -> int:
        """Delete expired idempotency records."""
        return self._repo.cleanup_expired_idempotency_records()

    def _detect_candidates(
        self,
        document_id: uuid.UUID,
        deadline_candidate_index: int,
    ) -> list[ReferenceEventCandidate]:
        """Detect reference event candidates from document text.

        Placeholder for M6-B implementation.
        """
        return []
