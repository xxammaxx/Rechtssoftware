"""Classification result value object."""

from dataclasses import dataclass, field


@dataclass
class ClassificationResult:
    """Result of document classification.

    Attributes:
        doc_type: The classified document type (e.g. 'bescheid', 'rechnung')
        confidence: Confidence score between 0.0 (unsure) and 1.0 (certain)
        matched_patterns: Which keyword patterns triggered the classification
    """

    doc_type: str
    confidence: float
    matched_patterns: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        if self.confidence < 0.5:
            self.doc_type = "sonstiges"
