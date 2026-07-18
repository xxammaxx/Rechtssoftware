"""Application service for reference event lifecycle management.

Orchestrates the reference event use cases:
  1. List reference event candidates for an M5 deadline candidate
  2. Confirm/reject/revoke a reference event
  3. Get confirmation history
"""

import uuid
from datetime import UTC, date, datetime

from private_legal_navigator.application.reference_event_repository import (
    ReferenceEventRepository,
)
from private_legal_navigator.domain.reference_event import (
    ConfirmationMethod,
    ConfirmedReferenceEvent,
    EventType,
    ReferenceEventCandidate,
    SourceType,
)


class ReferenceEventService:
    """Application service for reference event lifecycle management."""

    def __init__(self, repo: ReferenceEventRepository) -> None:
        self._repo = repo

    def get_reference_event_candidates(
        self,
        document_id: uuid.UUID,
        deadline_candidate_index: int,
    ) -> list[ReferenceEventCandidate]:
        """Get reference event candidates for a deadline candidate.

        In the future build, this will detect reference events from document text.
        For now, returns candidates detected by M5-based rules.

        Args:
            document_id: The document identifier.
            deadline_candidate_index: The M5 deadline candidate index (0-based).

        Returns:
            List of ReferenceEventCandidates (may be empty).
        """
        detected = self._detect_candidates(document_id, deadline_candidate_index)
        return detected

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

        Creates a new ConfirmedReferenceEvent. If a previous CONFIRMED
        confirmation exists for the same candidate, it is superseded.

        Args:
            document_id: The document identifier.
            deadline_candidate_index: The M5 deadline candidate index (0-based).
            event_type: User-selected event category.
            confirmed_date: The confirmed reference date.
            source_type: Where the date came from.
            confirmation_method: How the user confirmed.
            candidate_id: The candidate this confirmation refers to (None if manual).
            evidence_note: Transient user note (max 2000 chars).
            confirmed_by: Human identifier (max 100 chars).

        Returns:
            The newly created ConfirmedReferenceEvent.
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
    ) -> ConfirmedReferenceEvent:
        """Reject a reference event candidate.

        Creates a REJECTED confirmation record. No calculation is possible
        until a new CONFIRMED record is created.

        Args:
            document_id: The document identifier.
            deadline_candidate_index: The M5 deadline candidate index (0-based).
            event_type: The event type being rejected.
            candidate_id: The candidate being rejected (None if generic rejection).

        Returns:
            The REJECTED ConfirmedReferenceEvent.
        """
        now = datetime.now(UTC)
        rejection = ConfirmedReferenceEvent(
            confirmation_id=uuid.uuid4(),
            document_id=document_id,
            deadline_candidate_index=deadline_candidate_index,
            event_type=event_type,
            confirmed_at=now,
            confirmed_date=None,
            source_type=SourceType.AUTO_DETECTED,
            confirmation_method=ConfirmationMethod.AUTO_SUGGESTED,
            candidate_id=candidate_id,
        )
        self._repo.save_confirmation(rejection)
        return rejection

    def revoke(
        self,
        confirmation_id: uuid.UUID,
    ) -> ConfirmedReferenceEvent | None:
        """Revoke a previous confirmation.

        Creates a new REVOKED record. The revoked record supersedes
        the previously active confirmation. After revocation, no
        calculation is possible until a new CONFIRMED record is created.

        Args:
            confirmation_id: The confirmation to revoke.

        Returns:
            The new REVOKED ConfirmedReferenceEvent, or None if the
            original confirmation was not found.
        """
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
        """Get confirmation history for a deadline candidate.

        Args:
            document_id: The document identifier.
            deadline_candidate_index: The M5 deadline candidate index (0-based).

        Returns:
            List of ConfirmedReferenceEvent records sorted by confirmed_at desc.
        """
        return self._repo.get_history_for_candidate(document_id, deadline_candidate_index)

    def _detect_candidates(
        self,
        document_id: uuid.UUID,
        deadline_candidate_index: int,
    ) -> list[ReferenceEventCandidate]:
        """Detect reference event candidates from document text.

        Placeholder for M6-B implementation. Currently returns empty list.

        In the future build, this will analyze the M5 deadline candidate's
        context and detect possible reference events from the document text.
        """
        return []
