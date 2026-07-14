"""Deadline extraction port (interface).

Following the existing pattern from DocumentClassifier(ABC) and TextExtractor(ABC),
this port allows swapping extraction implementations at the infrastructure boundary.
"""

from abc import ABC, abstractmethod

from private_legal_navigator.domain.deadline import DeadlineExtractionResult


class DeadlineExtractor(ABC):
    """Abstract deadline candidate extractor.

    Implementations analyze document text and produce a list of
    DeadlineCandidate objects with evidence tracking.

    M5 provides a deterministic, rule-based implementation.
    Future versions (M6+) may add ML-based or legal-calculation-aware
    implementations through this same port.
    """

    @abstractmethod
    def extract(self, text: str, *, document_id: str = "") -> DeadlineExtractionResult:
        """Extract deadline candidates from document text.

        Args:
            text: The extracted document text to analyze.
            document_id: Optional document identifier for the result.

        Returns:
            DeadlineExtractionResult with candidates, warnings, and review flag.
        """
        ...
