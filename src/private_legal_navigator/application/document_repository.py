"""Repository port (interface) for Document persistence."""

from abc import ABC, abstractmethod
from uuid import UUID

from private_legal_navigator.domain.document import Document


class DocumentRepository(ABC):
    """Abstract repository for Document metadata persistence."""

    @abstractmethod
    def save(self, document: Document) -> None:
        """Persist document metadata."""
        ...

    @abstractmethod
    def get_by_id(self, document_id: UUID) -> Document | None:
        """Retrieve document metadata by ID."""
        ...

    @abstractmethod
    def list_by_case(self, case_id: UUID) -> list[Document]:
        """List all documents for a given case."""
        ...
