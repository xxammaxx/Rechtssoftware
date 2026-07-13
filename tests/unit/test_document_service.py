"""Unit tests for DocumentService with TextExtractor integration."""

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
    def mock_text_extractor(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def service(
        self,
        mock_doc_repo: MagicMock,
        mock_file_storage: MagicMock,
        mock_case_repo: MagicMock,
        mock_text_extractor: MagicMock,
    ) -> DocumentService:
        return DocumentService(
            mock_doc_repo, mock_file_storage, mock_case_repo, mock_text_extractor
        )

    def test_upload_document_extracts_text(
        self,
        service: DocumentService,
        mock_doc_repo: MagicMock,
        mock_file_storage: MagicMock,
        mock_case_repo: MagicMock,
        mock_text_extractor: MagicMock,
    ) -> None:
        """Upload should extract text and store it on the document."""
        case_id = uuid.uuid4()
        mock_case_repo.get_by_id.return_value = MagicMock()
        mock_text_extractor.extract.return_value = "Extracted PDF text"

        result = service.upload_document(
            case_id=case_id,
            filename="test.pdf",
            content=b"%PDF-1.4 test",
            mime_type="application/pdf",
            size_bytes=1024,
        )

        assert result.text_content == "Extracted PDF text"
        mock_text_extractor.extract.assert_called_once_with(b"%PDF-1.4 test")

    def test_upload_empty_text(
        self,
        service: DocumentService,
        mock_case_repo: MagicMock,
        mock_text_extractor: MagicMock,
    ) -> None:
        """PDF with no text should store empty string."""
        mock_case_repo.get_by_id.return_value = MagicMock()
        mock_text_extractor.extract.return_value = ""

        result = service.upload_document(
            case_id=uuid.uuid4(),
            filename="scan.pdf",
            content=b"%PDF-1.4 no text",
            mime_type="application/pdf",
            size_bytes=100,
        )
        assert result.text_content == ""

    def test_upload_to_nonexistent_case_raises(
        self, service: DocumentService, mock_case_repo: MagicMock
    ) -> None:
        """Upload to nonexistent case raises ValueError."""
        mock_case_repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="Fall wurde nicht gefunden"):
            service.upload_document(
                case_id=uuid.uuid4(),
                filename="test.pdf",
                content=b"x",
                mime_type="application/pdf",
                size_bytes=100,
            )

    def test_get_document_text(
        self, service: DocumentService, mock_doc_repo: MagicMock
    ) -> None:
        """get_document_text returns document with text_content."""
        doc = Document(
            "test.pdf", "application/pdf", 1024, uuid.uuid4(), text_content="Hello"
        )
        mock_doc_repo.get_by_id.return_value = doc

        result = service.get_document_text(doc.document_id)
        assert result is not None
        assert result.text_content == "Hello"

    def test_get_document_text_not_found(
        self, service: DocumentService, mock_doc_repo: MagicMock
    ) -> None:
        """get_document_text returns None for unknown ID."""
        mock_doc_repo.get_by_id.return_value = None
        assert service.get_document_text(uuid.uuid4()) is None

    def test_list_case_documents(
        self, service: DocumentService, mock_doc_repo: MagicMock
    ) -> None:
        """list_case_documents delegates to repository."""
        case_id = uuid.uuid4()
        docs = [Document("a.pdf", "application/pdf", 100, case_id)]
        mock_doc_repo.list_by_case.return_value = docs
        assert service.list_case_documents(case_id) == docs
