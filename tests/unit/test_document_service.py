"""Unit tests for DocumentService with TextExtractor and Classifier."""

import uuid
from unittest.mock import MagicMock

import pytest

from private_legal_navigator.application.document_service import DocumentService
from private_legal_navigator.application.text_extractor import ExtractionResult
from private_legal_navigator.domain.classification import ClassificationResult
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
    def mock_classifier(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def service(
        self,
        mock_doc_repo: MagicMock,
        mock_file_storage: MagicMock,
        mock_case_repo: MagicMock,
        mock_text_extractor: MagicMock,
        mock_classifier: MagicMock,
    ) -> DocumentService:
        return DocumentService(
            mock_doc_repo,
            mock_file_storage,
            mock_case_repo,
            mock_text_extractor,
            mock_classifier,
        )

    def test_upload_classifies_document(
        self,
        service: DocumentService,
        mock_case_repo: MagicMock,
        mock_text_extractor: MagicMock,
        mock_classifier: MagicMock,
        mock_doc_repo: MagicMock,
    ) -> None:
        """Upload should classify the document after text extraction."""
        case_id = uuid.uuid4()
        mock_case_repo.get_by_id.return_value = MagicMock()
        mock_text_extractor.extract.return_value = ExtractionResult(
            text="Bescheid über Steuern", error=None
        )
        mock_classifier.classify.return_value = ClassificationResult("bescheid", 0.85, ["bescheid"])

        result = service.upload_document(
            case_id=case_id,
            filename="test.pdf",
            content=b"%PDF-1.4",
            mime_type="application/pdf",
            size_bytes=1024,
        )

        assert result.text_content == "Bescheid über Steuern"
        assert result.extraction_error is None
        assert result.doc_type == "bescheid"
        assert result.classification_confidence == 0.85
        mock_text_extractor.extract.assert_called_once_with(b"%PDF-1.4")
        mock_classifier.classify.assert_called_once_with("Bescheid über Steuern")

    def test_upload_sonstiges_when_no_match(
        self,
        service: DocumentService,
        mock_case_repo: MagicMock,
        mock_text_extractor: MagicMock,
        mock_classifier: MagicMock,
    ) -> None:
        """Unrecognized text should result in 'sonstiges'."""
        mock_case_repo.get_by_id.return_value = MagicMock()
        mock_text_extractor.extract.return_value = ExtractionResult(text="lorem ipsum", error=None)
        mock_classifier.classify.return_value = ClassificationResult("sonstiges", 0.0, [])

        result = service.upload_document(
            case_id=uuid.uuid4(),
            filename="x.pdf",
            content=b"x",
            mime_type="application/pdf",
            size_bytes=100,
        )
        assert result.text_content == "lorem ipsum"
        assert result.extraction_error is None
        assert result.doc_type == "sonstiges"
        assert result.classification_confidence == 0.0

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

    def test_upload_nonexistent_case(
        self,
        service: DocumentService,
        mock_case_repo: MagicMock,
    ) -> None:
        mock_case_repo.get_by_id.return_value = None
        with pytest.raises(ValueError, match="Fall wurde nicht gefunden"):
            service.upload_document(
                case_id=uuid.uuid4(),
                filename="x.pdf",
                content=b"x",
                mime_type="application/pdf",
                size_bytes=100,
            )

    def test_get_document_text_with_classification(
        self,
        service: DocumentService,
        mock_doc_repo: MagicMock,
    ) -> None:
        doc = Document(
            "a.pdf",
            "application/pdf",
            100,
            uuid.uuid4(),
            text_content="hello",
            extraction_error=None,
            doc_type="bescheid",
            classification_confidence=0.9,
        )
        mock_doc_repo.get_by_id.return_value = doc
        result = service.get_document_text(doc.document_id)
        assert result is not None
        assert result.text_content == "hello"
        assert result.extraction_error is None
        assert result.doc_type == "bescheid"

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
