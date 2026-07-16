"""Port for persistent reference event storage (M6-A Variant B).

Confirmation is persistent. Calculation is on-demand.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from private_legal_navigator.domain.calendar import ConfirmedReferenceEvent


class ReferenceEventRepository(ABC):
    """Persistence port for confirmed reference events.

    Variant B: confirmation is stored, calculation is recomputed.
    """

    @abstractmethod
    def save(self, event: ConfirmedReferenceEvent) -> None:
        """Store a confirmed reference event.

        If a prior confirmation with the same candidate_id exists,
        it is marked as SUPERSEDED before the new one is inserted.
        """
        ...

    @abstractmethod
    def get_by_id(self, confirmation_id: UUID) -> ConfirmedReferenceEvent | None:
        """Retrieve a confirmation by its ID."""
        ...

    @abstractmethod
    def get_active(self, document_id: UUID, candidate_index: int) -> ConfirmedReferenceEvent | None:
        """Get the currently active (CONFIRMED) event for a document and candidate index.

        Returns the most recent CONFIRMED event, or None.
        """
        ...

    @abstractmethod
    def get_history(self, document_id: UUID, candidate_index: int) -> list[ConfirmedReferenceEvent]:
        """Get full confirmation audit trail, newest first."""
        ...

    @abstractmethod
    def get_by_candidate_index(
        self, document_id: UUID, candidate_index: int
    ) -> list[ConfirmedReferenceEvent]:
        """Get all confirmations for a candidate index, newest first."""
        ...
