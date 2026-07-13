"""Unit tests for PdfTextExtractor."""

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
    """Tests for PdfTextExtractor."""

    def test_extract_text_from_pdf(self) -> None:
        """Should extract text from a valid PDF."""
        extractor = PdfTextExtractor()
        pdf = _make_minimal_pdf()
        text = extractor.extract(pdf)
        assert "Hallo Welt" in text

    def test_extract_empty_for_invalid_pdf(self) -> None:
        """Invalid PDF should return empty string (no crash)."""
        extractor = PdfTextExtractor()
        text = extractor.extract(b"not a pdf")
        assert text == ""

    def test_extract_empty_for_empty_bytes(self) -> None:
        """Empty bytes should return empty string."""
        extractor = PdfTextExtractor()
        text = extractor.extract(b"")
        assert text == ""
