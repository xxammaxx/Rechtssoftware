"""Application service for deadline candidate extraction.

Orchestrates the deadline extraction use case:
  1. Load document text via DocumentRepository
  2. Delegate extraction to DeadlineExtractor (port)
  3. Return structured DeadlineExtractionResult
"""

import uuid

from private_legal_navigator.application.deadline_extractor import DeadlineExtractor
from private_legal_navigator.application.document_repository import DocumentRepository
from private_legal_navigator.domain.deadline import (
    DeadlineExtractionResult,
)


class DeadlineService:
    """Application service for deadline candidate extraction."""

    def __init__(
        self,
        document_repo: DocumentRepository,
        deadline_extractor: DeadlineExtractor,
    ) -> None:
        self._doc_repo = document_repo
        self._extractor = deadline_extractor

    def extract_candidates(self, document_id: uuid.UUID) -> DeadlineExtractionResult | None:
        """Extract deadline candidates from a document.

        Args:
            document_id: The document to analyze.

        Returns:
            DeadlineExtractionResult if the document exists (may have
            zero candidates), or None if the document is not found.
        """
        doc = self._doc_repo.get_by_id(document_id)
        if doc is None:
            return None

        doc_id_str = str(doc.document_id)
        text = doc.text_content if doc.text_content else ""

        return self._extractor.extract(text, document_id=doc_id_str)
