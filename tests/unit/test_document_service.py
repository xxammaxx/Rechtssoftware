"""Unit tests for DocumentService."""

import uuid
from unittest.mock import MagicMock

import pytest

from private_legal_navigator.application.document_service import DocumentService
from private_legal_navigator.domain.document import Document


class TestDocumentService:
    """Tests for DocumentService with mocked dependencies."""

    @pytest.fixture
    def mock_doc_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_file_storage(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_case_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def service(
        self, mock_doc_repo: MagicMock, mock_file_storage: MagicMock, mock_case_repo: MagicMock
    ) -> DocumentService:
        return DocumentService(mock_doc_repo, mock_file_storage, mock_case_repo)

    def test_upload_document(
        self,
        service: DocumentService,
        mock_doc_repo: MagicMock,
        mock_file_storage: MagicMock,
        mock_case_repo: MagicMock,
    ) -> None:
        """Upload should store file and save metadata."""
        case_id = uuid.uuid4()
        mock_case_repo.get_by_id.return_value = MagicMock()  # case exists

        result = service.upload_document(
            case_id=case_id,
            filename="test.pdf",
            content=b"%PDF-1.4 test",
            mime_type="application/pdf",
            size_bytes=1024,
        )

        assert isinstance(result, Document)
        assert result.case_id == case_id
        assert result.filename == "test.pdf"
        mock_file_storage.store.assert_called_once()
        mock_doc_repo.save.assert_called_once_with(result)

    def test_upload_to_nonexistent_case_raises(
        self,
        service: DocumentService,
        mock_case_repo: MagicMock,
    ) -> None:
        """Upload to nonexistent case raises CaseNotFoundError."""
        mock_case_repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="Fall wurde nicht gefunden"):
            service.upload_document(
                case_id=uuid.uuid4(),
                filename="test.pdf",
                content=b"x",
                mime_type="application/pdf",
                size_bytes=100,
            )

    def test_get_document_returns_doc_and_content(
        self,
        service: DocumentService,
        mock_doc_repo: MagicMock,
        mock_file_storage: MagicMock,
    ) -> None:
        """get_document should return metadata and file content."""
        doc = Document("test.pdf", "application/pdf", 1024, uuid.uuid4())
        mock_doc_repo.get_by_id.return_value = doc
        mock_file_storage.retrieve.return_value = b"content"

        result_doc, result_content = service.get_document(doc.document_id)
        assert result_doc == doc
        assert result_content == b"content"

    def test_get_document_not_found(
        self,
        service: DocumentService,
        mock_doc_repo: MagicMock,
    ) -> None:
        """get_document for unknown ID returns None."""
        mock_doc_repo.get_by_id.return_value = None
        result = service.get_document(uuid.uuid4())
        assert result is None

    def test_list_case_documents(
        self,
        service: DocumentService,
        mock_doc_repo: MagicMock,
    ) -> None:
        """list_case_documents delegates to repository."""
        case_id = uuid.uuid4()
        docs = [Document("a.pdf", "application/pdf", 100, case_id)]
        mock_doc_repo.list_by_case.return_value = docs

        result = service.list_case_documents(case_id)
        assert result == docs

    def test_list_case_documents_empty(
        self,
        service: DocumentService,
        mock_doc_repo: MagicMock,
    ) -> None:
        """Empty list returned for case with no documents."""
        mock_doc_repo.list_by_case.return_value = []
        result = service.list_case_documents(uuid.uuid4())
        assert result == []
