"""Synthetic PDF generator for testing.

Produces minimal valid PDF bytes with a SYNTHETISCH – metadata prefix
to comply with Constitution §12 (no real data in tests).
"""

from typing import Final

SYNTHETIC_TITLE: Final[str] = "SYNTHETISCH – M2 Test Document"
MINIMAL_PDF_BYTES: Final[bytes] = (
    b"%PDF-1.4\n"
    b"1 0 obj\n"
    b"<< /Type /Catalog /Pages 2 0 R >>\n"
    b"endobj\n"
    b"2 0 obj\n"
    b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
    b"endobj\n"
    b"3 0 obj\n"
    b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\n"
    b"endobj\n"
    b"xref\n"
    b"0 4\n"
    b"0000000000 65535 f \n"
    b"0000000009 00000 n \n"
    b"0000000058 00000 n \n"
    b"0000000115 00000 n \n"
    b"trailer\n"
    b"<< /Size 4 /Root 1 0 R >>\n"
    b"startxref\n"
    b"190\n"
    b"%%EOF"
)


def synthetic_pdf_bytes() -> bytes:
    """Return minimal valid PDF bytes for testing."""
    return MINIMAL_PDF_BYTES


def synthetic_pdf_size() -> int:
    """Return byte size of the synthetic PDF."""
    return len(MINIMAL_PDF_BYTES)
