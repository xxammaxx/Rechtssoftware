"""Repository port (interface) for Case persistence."""

from abc import ABC, abstractmethod
from uuid import UUID

from private_legal_navigator.domain.case import Case


class CaseRepository(ABC):
    """Abstract repository for Case persistence.

    Defines the port that infrastructure implementations must satisfy.
    """

    @abstractmethod
    def save(self, case: Case) -> None:
        """Persist a case. Creates or updates as needed."""
        ...

    @abstractmethod
    def get_by_id(self, case_id: UUID) -> Case | None:
        """Retrieve a single case by its ID. Returns None if not found."""
        ...

    @abstractmethod
    def list_all(self) -> list[Case]:
        """Retrieve all cases, deterministically sorted."""
        ...
