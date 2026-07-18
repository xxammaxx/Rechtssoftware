"""Text extraction port (interface)."""

from abc import ABC, abstractmethod
from typing import NamedTuple


class ExtractionResult(NamedTuple):
    """Result of a text extraction attempt.

    Attributes:
        text: The extracted text, or empty string if no text was found
              or extraction failed.
        error: Error message if extraction failed, None on success.
               Must not contain document content or PII (see EC-M3-04).
    """

    text: str
    error: str | None


class TextExtractor(ABC):
    """Abstract text extractor for documents.

    Implementations extract text from binary document content.
    PDF extraction (pymupdf) is the first implementation.
    OCR implementations can be added later as separate adapters.
    """

    @abstractmethod
    def extract(self, content: bytes) -> ExtractionResult:
        """Extract text from raw document bytes.

        Returns an ExtractionResult with the extracted text (or empty string
        if no text is found) and an optional error message on failure.
        """
        ...
