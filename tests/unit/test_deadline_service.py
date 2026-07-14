"""Unit tests for DeadlineService (application layer).

Uses mocked DeadlineExtractor and real in-memory document repository
to test orchestration logic.

SYNTHETISCH – KEINE ECHTEN PERSONEN- ODER FALLDATEN
"""

import uuid
from datetime import date
from unittest.mock import MagicMock

import pytest

from private_legal_navigator.application.deadline_extractor import DeadlineExtractor
from private_legal_navigator.application.deadline_service import DeadlineService
from private_legal_navigator.domain.deadline import (
    DeadlineCandidate,
    DeadlineCandidateKind,
    DeadlineExtractionResult,
    DeadlineWarning,
    DeadlineWarningCode,
)
from private_legal_navigator.domain.document import Document


@pytest.fixture
def mock_extractor():
    """Return a mock DeadlineExtractor that returns an empty result."""
    extractor = MagicMock(spec=DeadlineExtractor)
    extractor.extract.return_value = DeadlineExtractionResult(
        document_id="test-doc-id",
        candidates=[],
        warnings=[
            DeadlineWarning(
                code=DeadlineWarningCode.LEGAL_CALCULATION_NOT_PERFORMED,
                message="Keine rechtliche Frist berechnet.",
            ),
        ],
    )
    return extractor


@pytest.fixture
def mock_doc_repo():
    """Return a mock document repository."""
    return MagicMock()


class TestDeadlineService:
    def test_returns_none_for_missing_document(self, mock_doc_repo, mock_extractor):
        """Service returns None when document is not found."""
        mock_doc_repo.get_by_id.return_value = None
        service = DeadlineService(mock_doc_repo, mock_extractor)

        doc_id = uuid.uuid4()
        result = service.extract_candidates(doc_id)
        assert result is None

    def test_returns_result_for_existing_document(self, mock_doc_repo, mock_extractor):
        """Service returns extraction result when document exists."""
        doc_id = uuid.uuid4()
        doc = Document(
            filename="test.pdf",
            mime_type="application/pdf",
            size_bytes=1000,
            case_id=uuid.uuid4(),
            document_id=doc_id,
            text_content="SYNTHETISCH – Frist bis 31.07.2026",
        )
        mock_doc_repo.get_by_id.return_value = doc

        mock_extractor.extract.return_value = DeadlineExtractionResult(
            document_id=str(doc_id),
            candidates=[
                DeadlineCandidate(
                    kind=DeadlineCandidateKind.EXPLICIT_DATE,
                    raw_text="31.07.2026",
                    start_offset=25,
                    end_offset=35,
                    normalized_date=date(2026, 7, 31),
                    rule_id="DEADLINE_DATE_NUMERIC_DE_V1",
                ),
            ],
            warnings=[
                DeadlineWarning(
                    code=DeadlineWarningCode.LEGAL_CALCULATION_NOT_PERFORMED,
                    message="Keine rechtliche Frist berechnet.",
                ),
            ],
        )

        service = DeadlineService(mock_doc_repo, mock_extractor)
        result = service.extract_candidates(doc_id)

        assert result is not None
        assert len(result.candidates) == 1
        assert result.candidates[0].normalized_date == date(2026, 7, 31)
        assert result.human_review_required is True

    def test_passes_document_text_to_extractor(self, mock_doc_repo, mock_extractor):
        """Service passes the document's text_content to the extractor."""
        doc_id = uuid.uuid4()
        test_text = "SYNTHETISCH – bis zum 01.01.2025"
        doc = Document(
            filename="test.pdf",
            mime_type="application/pdf",
            size_bytes=1000,
            case_id=uuid.uuid4(),
            document_id=doc_id,
            text_content=test_text,
        )
        mock_doc_repo.get_by_id.return_value = doc

        service = DeadlineService(mock_doc_repo, mock_extractor)
        service.extract_candidates(doc_id)

        # Verify extractor was called with correct text
        mock_extractor.extract.assert_called_once()
        call_args = mock_extractor.extract.call_args
        assert call_args[0][0] == test_text

    def test_handles_empty_text_content(self, mock_doc_repo, mock_extractor):
        """Service handles documents with empty text_content."""
        doc_id = uuid.uuid4()
        doc = Document(
            filename="test.pdf",
            mime_type="application/pdf",
            size_bytes=1000,
            case_id=uuid.uuid4(),
            document_id=doc_id,
            text_content="",
        )
        mock_doc_repo.get_by_id.return_value = doc
        mock_extractor.extract.return_value = DeadlineExtractionResult(
            document_id=str(doc_id),
            candidates=[],
            warnings=[
                DeadlineWarning(
                    code=DeadlineWarningCode.NO_DEADLINE_CANDIDATE,
                    message="Kein Text vorhanden.",
                ),
            ],
        )

        service = DeadlineService(mock_doc_repo, mock_extractor)
        result = service.extract_candidates(doc_id)

        assert result is not None
        assert result.candidates == []

    def test_document_id_includes_in_result(self, mock_doc_repo, mock_extractor):
        """Result document_id matches the requested document."""
        doc_id = uuid.uuid4()
        doc = Document(
            filename="test.pdf",
            mime_type="application/pdf",
            size_bytes=1000,
            case_id=uuid.uuid4(),
            document_id=doc_id,
            text_content="SYNTHETISCH – Test",
        )
        mock_doc_repo.get_by_id.return_value = doc
        mock_extractor.extract.return_value = DeadlineExtractionResult(
            document_id=str(doc_id),
            candidates=[],
            warnings=[],
        )

        service = DeadlineService(mock_doc_repo, mock_extractor)
        result = service.extract_candidates(doc_id)

        assert result is not None
        assert result.document_id == str(doc_id)
