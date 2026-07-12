"""Unit tests for the Document domain entity."""

import uuid

import pytest

from private_legal_navigator.domain.document import Document


class TestDocumentCreation:
    """Tests for Document entity creation and validation."""

    def test_valid_document_creation(self) -> None:
        """A valid document should be created successfully."""
        case_id = uuid.uuid4()
        doc = Document(
            filename="bescheid.pdf",
            mime_type="application/pdf",
            size_bytes=12345,
            case_id=case_id,
        )

        assert doc.filename == "bescheid.pdf"
        assert doc.mime_type == "application/pdf"
        assert doc.size_bytes == 12345
        assert doc.case_id == case_id
        assert isinstance(doc.document_id, uuid.UUID)
        assert doc.created_at.tzinfo is not None

    def test_document_id_is_unique(self) -> None:
        """Each document should receive a unique UUID."""
        case_id = uuid.uuid4()
        doc1 = Document("a.pdf", "application/pdf", 100, case_id)
        doc2 = Document("b.pdf", "application/pdf", 200, case_id)
        assert doc1.document_id != doc2.document_id

    def test_filename_max_length(self) -> None:
        """Filename should support up to 255 characters."""
        long_name = "a" * 251 + ".pdf"
        case_id = uuid.uuid4()
        doc = Document(long_name, "application/pdf", 100, case_id)
        assert len(doc.filename) == 255

    def test_size_bytes_must_be_positive(self) -> None:
        """size_bytes must be > 0."""
        case_id = uuid.uuid4()
        with pytest.raises(ValueError, match="Dateigröße"):
            Document("a.pdf", "application/pdf", 0, case_id)

    def test_mime_type_not_pdf(self) -> None:
        """Non-PDF mime types should be rejected."""
        case_id = uuid.uuid4()
        with pytest.raises(ValueError, match="Nur PDF-Dateien"):
            Document("image.png", "image/png", 100, case_id)

    def test_size_exceeds_limit(self) -> None:
        """Files over 20 MB should be rejected."""
        case_id = uuid.uuid4()
        too_big = 20 * 1024 * 1024 + 1
        with pytest.raises(ValueError, match="maximale Größe"):
            Document("big.pdf", "application/pdf", too_big, case_id)

    def test_size_exactly_20mb_accepted(self) -> None:
        """Exactly 20 MB should be accepted."""
        case_id = uuid.uuid4()
        exactly_20mb = 20 * 1024 * 1024
        doc = Document("big.pdf", "application/pdf", exactly_20mb, case_id)
        assert doc.size_bytes == exactly_20mb

    def test_created_at_is_utc(self) -> None:
        """created_at must be timezone-aware UTC."""
        case_id = uuid.uuid4()
        doc = Document("a.pdf", "application/pdf", 100, case_id)
        assert doc.created_at.tzinfo is not None
