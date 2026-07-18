"""PDF text extraction using pymupdf (fitz)."""

import logging

import pymupdf

from private_legal_navigator.application.text_extractor import (
    ExtractionResult,
    TextExtractor,
)

logger = logging.getLogger(__name__)


class PdfTextExtractor(TextExtractor):
    """Extract text from PDF documents using pymupdf.

    Fully local — no cloud services, no external APIs.

    Error messages are in German and contain NO document content (PII-safe).
    See EC-M3-04.
    """

    def extract(self, content: bytes) -> ExtractionResult:
        """Extract text from PDF bytes.

        Opens the PDF from memory, iterates over all pages,
        and concatenates the extracted text.

        Returns ExtractionResult with extracted text (or empty string)
        and optional error message on failure.
        """
        try:
            doc = pymupdf.open(stream=content, filetype="pdf")  # type: ignore[no-untyped-call]
            parts: list[str] = []
            for page in doc:  # type: ignore[attr-defined]
                text = page.get_text()
                if text.strip():
                    parts.append(text)
            doc.close()  # type: ignore[no-untyped-call]
            return ExtractionResult(text="\n".join(parts), error=None)
        except pymupdf.EmptyFileError:
            logger.error("Textextraktion fehlgeschlagen: Datei ist leer")
            return ExtractionResult(text="", error="Datei ist leer")
        except pymupdf.FileDataError as e:
            msg = str(e)
            if "encrypt" in msg.lower():
                logger.error("Textextraktion fehlgeschlagen: PDF ist verschlüsselt")
                return ExtractionResult(text="", error="PDF ist verschlüsselt")
            logger.error("Textextraktion fehlgeschlagen: PDF ist korrupt")
            return ExtractionResult(text="", error="PDF ist korrupt")
        except Exception:
            logger.exception("Unerwarteter Fehler bei Textextraktion")
            return ExtractionResult(text="", error="Unerwarteter Fehler bei Textextraktion")
