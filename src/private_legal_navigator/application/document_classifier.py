"""Document classifier port (interface)."""

from abc import ABC, abstractmethod

from private_legal_navigator.domain.classification import ClassificationResult


class DocumentClassifier(ABC):
    """Abstract document classifier.

    Classifies a document based on its extracted text content.
    Implementations may use rules, ML models, or other approaches.
    """

    @abstractmethod
    def classify(self, text: str) -> ClassificationResult:
        """Classify a document based on its extracted text.

        Args:
            text: The extracted text content of the document.

        Returns:
            A ClassificationResult with doc_type, confidence, and matched patterns.
        """
        ...
