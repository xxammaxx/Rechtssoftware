"""Application service for Case use cases."""

import uuid

from private_legal_navigator.application.case_repository import CaseRepository
from private_legal_navigator.domain.case import Case


class CaseService:
    """Application service orchestrating Case use cases.

    Coordinates between the API layer and the domain, using the
    repository port for persistence.
    """

    def __init__(self, repository: CaseRepository) -> None:
        self._repository = repository

    def create_case(self, title: str) -> Case:
        """Create a new case with the given title and persist it.

        Returns the created Case entity with server-generated UUID.
        Raises ValueError if the title is invalid.
        """
        case = Case(title=title)
        self._repository.save(case)
        return case

    def get_case(self, case_id: uuid.UUID) -> Case | None:
        """Retrieve a single case by its ID."""
        return self._repository.get_by_id(case_id)

    def list_cases(self) -> list[Case]:
        """Retrieve all cases."""
        return self._repository.list_all()
