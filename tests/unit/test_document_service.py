"""Unit tests for DocumentService with TextExtractor and Classifier."""

import uuid
from unittest.mock import MagicMock

import pytest

from private_legal_navigator.application.document_service import DocumentService
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
        mock_text_extractor.extract.return_value = "Bescheid über Steuern"
        mock_classifier.classify.return_value = ClassificationResult("bescheid", 0.85, ["bescheid"])

        result = service.upload_document(
            case_id=case_id,
            filename="test.pdf",
            content=b"%PDF-1.4",
            mime_type="application/pdf",
            size_bytes=1024,
        )

        assert result.doc_type == "bescheid"
        assert result.classification_confidence == 0.85
        assert result.matched_patterns == ["bescheid"]
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
        mock_text_extractor.extract.return_value = "lorem ipsum"
        mock_classifier.classify.return_value = ClassificationResult("sonstiges", 0.0, [])

        result = service.upload_document(
            case_id=uuid.uuid4(),
            filename="x.pdf",
            content=b"x",
            mime_type="application/pdf",
            size_bytes=100,
        )
        assert result.doc_type == "sonstiges"
        assert result.classification_confidence == 0.0

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
            doc_type="bescheid",
            classification_confidence=0.9,
            matched_patterns=["bescheid", "festsetzung"],
        )
        mock_doc_repo.get_by_id.return_value = doc
        result = service.get_document_text(doc.document_id)
        assert result is not None
        assert result.doc_type == "bescheid"
        assert result.matched_patterns == ["bescheid", "festsetzung"]
