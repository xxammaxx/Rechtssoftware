"""Repository port (interface) for reference event persistence."""

from abc import ABC, abstractmethod
from uuid import UUID

from private_legal_navigator.domain.reference_event import (
    ConfirmedReferenceEvent,
)


class ReferenceEventRepository(ABC):
    """Abstract repository for confirmed reference events.

    Responsible for persisting ConfirmedReferenceEvent records and
    retrieving confirmation history for audit trail purposes.
    """

    @abstractmethod
    def save_confirmation(self, event: ConfirmedReferenceEvent) -> None:
        """Persist a confirmed reference event.

        Args:
            event: The confirmed reference event to persist.
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
