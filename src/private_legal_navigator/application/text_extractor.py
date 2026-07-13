"""Text extraction port (interface)."""

from abc import ABC, abstractmethod


class TextExtractor(ABC):
    """Abstract text extractor for documents.

    Implementations extract text from binary document content.
    PDF extraction (pymupdf) is the first implementation.
    OCR implementations can be added later as separate adapters.
    """

    @abstractmethod
    def extract(self, content: bytes) -> str:
        """Extract text from raw document bytes.

        Returns the extracted text, or an empty string if no text is found.
        """
        ...
