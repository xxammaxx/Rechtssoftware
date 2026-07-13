"""PDF text extraction using pymupdf (fitz)."""

import pymupdf

from private_legal_navigator.application.text_extractor import TextExtractor


class PdfTextExtractor(TextExtractor):
    """Extract text from PDF documents using pymupdf.

    Fully local — no cloud services, no external APIs.
    """

    def extract(self, content: bytes) -> str:
        """Extract text from PDF bytes.

        Opens the PDF from memory, iterates over all pages,
        and concatenates the extracted text.

        Returns empty string for PDFs with no extractable text
        (e.g., scanned documents without OCR layer).
        """
        try:
            doc = pymupdf.open(stream=content, filetype="pdf")  # type: ignore[no-untyped-call]
            parts: list[str] = []
            for page in doc:  # type: ignore[attr-defined]
                text = page.get_text()
                if text.strip():
                    parts.append(text)
            doc.close()  # type: ignore[no-untyped-call]
            return "\n".join(parts)
        except Exception:
            return ""
