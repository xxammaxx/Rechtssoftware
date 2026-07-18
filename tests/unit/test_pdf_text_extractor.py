"""Unit tests for PdfTextExtractor."""

from private_legal_navigator.application.text_extractor import ExtractionResult
from private_legal_navigator.infrastructure.pdf_text_extractor import PdfTextExtractor


def _make_minimal_pdf() -> bytes:
    """Create a minimal valid PDF with extractable text."""
    # A minimal PDF with one page and text
    return (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
        b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
        b"4 0 obj<</Length 44>>stream\n"
        b"BT /F1 12 Tf 100 700 Td (Hallo Welt) Tj ET\n"
        b"endstream\n"
        b"endobj\n"
        b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
        b"xref\n0 6\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000266 00000 n \n"
        b"0000000360 00000 n \n"
        b"trailer<</Size 6/Root 1 0 R>>\n"
        b"startxref\n421\n%%EOF"
    )


class TestPdfTextExtractor:
    """Tests for PdfTextExtractor returning ExtractionResult."""

    def test_extract_text_from_pdf(self) -> None:
        """Should extract text from a valid PDF."""
        extractor = PdfTextExtractor()
        pdf = _make_minimal_pdf()
        result = extractor.extract(pdf)
        assert isinstance(result, ExtractionResult)
        assert "Hallo Welt" in result.text
        assert result.error is None

    def test_extract_error_for_invalid_pdf(self) -> None:
        """Invalid PDF should return ExtractionResult with error."""
        extractor = PdfTextExtractor()
        result = extractor.extract(b"not a pdf")
        assert isinstance(result, ExtractionResult)
        assert result.text == ""
        assert result.error is not None
        assert "korrupt" in result.error

    def test_extract_error_for_empty_bytes(self) -> None:
        """Empty bytes should return ExtractionResult with error."""
        extractor = PdfTextExtractor()
        result = extractor.extract(b"")
        assert isinstance(result, ExtractionResult)
        assert result.text == ""
        assert result.error is not None

    def test_extraction_error_contains_no_document_content(self) -> None:
        """Error messages must not contain document content (PII-safe)."""
        extractor = PdfTextExtractor()
        result = extractor.extract(b"not a pdf")
        assert result.error is not None
        # Error should describe the problem, not echo the content
        assert "not a pdf" not in result.error
