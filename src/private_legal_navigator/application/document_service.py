"""Application service for Document use cases."""

import uuid

from private_legal_navigator.application.case_repository import CaseRepository
from private_legal_navigator.application.document_repository import DocumentRepository
from private_legal_navigator.application.file_storage import FileStorage
from private_legal_navigator.domain.document import Document


class DocumentService:
    """Application service for document upload, listing, and retrieval."""

    def __init__(
        self,
        document_repo: DocumentRepository,
        file_storage: FileStorage,
        case_repo: CaseRepository,
    ) -> None:
        self._doc_repo = document_repo
        self._file_storage = file_storage
        self._case_repo = case_repo

    def upload_document(
        self,
        case_id: uuid.UUID,
        filename: str,
        content: bytes,
        mime_type: str,
        size_bytes: int,
    ) -> Document:
        """Upload a document to a case.

        Raises ValueError if the case doesn't exist or the document is invalid.
        """
        if self._case_repo.get_by_id(case_id) is None:
            raise ValueError("Der Fall wurde nicht gefunden.")

        doc = Document(
            filename=filename,
            mime_type=mime_type,
            size_bytes=size_bytes,
            case_id=case_id,
        )

        self._file_storage.store(doc.storage_path, content)
        self._doc_repo.save(doc)
        return doc

    def get_document(self, document_id: uuid.UUID) -> tuple[Document, bytes] | None:
        """Retrieve document metadata and content. Returns None if not found."""
        doc = self._doc_repo.get_by_id(document_id)
        if doc is None:
            return None
        content = self._file_storage.retrieve(doc.storage_path)
        return doc, content

    def list_case_documents(self, case_id: uuid.UUID) -> list[Document]:
        """List all documents for a given case."""
        return self._doc_repo.list_by_case(case_id)
