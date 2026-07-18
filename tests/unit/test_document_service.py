"""Unit tests for DocumentService with TextExtractor integration."""

import uuid
from unittest.mock import MagicMock

import pytest

from private_legal_navigator.application.document_service import DocumentService
from private_legal_navigator.application.text_extractor import ExtractionResult
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
        mock_text_extractor.extract.return_value = ExtractionResult(
            text="Extracted PDF text", error=None
        )

        result = service.upload_document(
            case_id=case_id,
            filename="test.pdf",
            content=b"%PDF-1.4 test",
            mime_type="application/pdf",
            size_bytes=1024,
        )

        assert result.text_content == "Extracted PDF text"
        assert result.extraction_error is None
        mock_text_extractor.extract.assert_called_once_with(b"%PDF-1.4 test")

    def test_upload_empty_text(
        self,
        service: DocumentService,
        mock_case_repo: MagicMock,
        mock_text_extractor: MagicMock,
    ) -> None:
        """PDF with no text should store empty string, no error."""
        mock_case_repo.get_by_id.return_value = MagicMock()
        mock_text_extractor.extract.return_value = ExtractionResult(text="", error=None)

        result = service.upload_document(
            case_id=uuid.uuid4(),
            filename="scan.pdf",
            content=b"%PDF-1.4 no text",
            mime_type="application/pdf",
            size_bytes=100,
        )
        assert result.text_content == ""
        assert result.extraction_error is None

    def test_upload_with_extraction_error(
        self,
        service: DocumentService,
        mock_doc_repo: MagicMock,
        mock_file_storage: MagicMock,
        mock_case_repo: MagicMock,
        mock_text_extractor: MagicMock,
    ) -> None:
        """Upload with extraction error still succeeds, error recorded."""
        case_id = uuid.uuid4()
        mock_case_repo.get_by_id.return_value = MagicMock()
        mock_text_extractor.extract.return_value = ExtractionResult(
            text="", error="PDF ist korrupt"
        )

        result = service.upload_document(
            case_id=case_id,
            filename="corrupt.pdf",
            content=b"garbage",
            mime_type="application/pdf",
            size_bytes=100,
        )

        assert result.text_content == ""
        assert result.extraction_error == "PDF ist korrupt"
        # Upload should still persist file and document
        mock_file_storage.store.assert_called_once()
        mock_doc_repo.save.assert_called_once()

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

    def test_get_document_text(self, service: DocumentService, mock_doc_repo: MagicMock) -> None:
        """get_document_text returns document with text_content and extraction_error."""
        doc = Document(
            "test.pdf",
            "application/pdf",
            1024,
            uuid.uuid4(),
            text_content="Hello",
            extraction_error=None,
        )
        mock_doc_repo.get_by_id.return_value = doc

        result = service.get_document_text(doc.document_id)
        assert result is not None
        assert result.text_content == "Hello"
        assert result.extraction_error is None

    def test_get_document_text_with_error(
        self, service: DocumentService, mock_doc_repo: MagicMock
    ) -> None:
        """get_document_text returns document with extraction_error set."""
        doc = Document(
            "bad.pdf",
            "application/pdf",
            100,
            uuid.uuid4(),
            text_content="",
            extraction_error="PDF ist korrupt",
        )
        mock_doc_repo.get_by_id.return_value = doc

        result = service.get_document_text(doc.document_id)
        assert result is not None
        assert result.text_content == ""
        assert result.extraction_error == "PDF ist korrupt"

    def test_get_document_text_not_found(
        self, service: DocumentService, mock_doc_repo: MagicMock
    ) -> None:
        """get_document_text returns None for unknown ID."""
        mock_doc_repo.get_by_id.return_value = None
        assert service.get_document_text(uuid.uuid4()) is None

    def test_list_case_documents(self, service: DocumentService, mock_doc_repo: MagicMock) -> None:
        """list_case_documents delegates to repository."""
        case_id = uuid.uuid4()
        docs = [Document("a.pdf", "application/pdf", 100, case_id)]
        mock_doc_repo.list_by_case.return_value = docs
        assert service.list_case_documents(case_id) == docs
