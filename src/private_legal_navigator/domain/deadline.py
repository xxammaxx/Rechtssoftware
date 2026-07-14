"""Domain models for deadline candidate extraction.

M5 erkennt ausschließlich mögliche Frist- und Terminangaben im Text.
Es berechnet keine verbindliche Rechtsfrist und ersetzt keine
anwaltliche oder behördliche Prüfung.
"""

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum


class DeadlineCandidateKind(StrEnum):
    """Type of deadline reference found in text."""

    EXPLICIT_DATE = "explicit_date"
    RELATIVE_PERIOD = "relative_period"
    QUALITATIVE_REFERENCE = "qualitative_reference"


class DeadlineCertainty(StrEnum):
    """How certain the extraction is."""

    EXACT = "exact"
    UNRESOLVED = "unresolved"
    AMBIGUOUS = "ambiguous"


class DeadlineWarningCode(StrEnum):
    """Stable warning codes for deadline extraction results.

    These codes MUST NOT change between releases to ensure
    downstream consumers can rely on them.
    """

    LEGAL_CALCULATION_NOT_PERFORMED = "LEGAL_CALCULATION_NOT_PERFORMED"
    NO_DEADLINE_CANDIDATE = "NO_DEADLINE_CANDIDATE"
    MULTIPLE_DEADLINE_CANDIDATES = "MULTIPLE_DEADLINE_CANDIDATES"
    RELATIVE_REFERENCE_REQUIRED = "RELATIVE_REFERENCE_REQUIRED"
    AMBIGUOUS_DATE = "AMBIGUOUS_DATE"


@dataclass
class DeadlineCandidate:
    """A potential deadline reference found in document text.

    Attributes:
        kind: Type of deadline reference.
        raw_text: Original text from the document.
        start_offset: Character offset where the match starts.
        end_offset: Character offset where the match ends.
        normalized_date: ISO date (YYYY-MM-DD), None if unresolvable.
        amount: Numeric amount for relative periods.
        unit: Time unit for relative periods (Tag/Woche/Monat/Jahr).
        reference_required: True if a reference point is needed.
        certainty: How certain the extraction is.
        rule_id: Stable identifier for the rule that produced this candidate.
    """

    kind: DeadlineCandidateKind
    raw_text: str
    start_offset: int
    end_offset: int
    normalized_date: date | None = None
    amount: int | None = None
    unit: str | None = None
    reference_required: bool = False
    certainty: DeadlineCertainty = DeadlineCertainty.EXACT
    rule_id: str = ""

    def __post_init__(self) -> None:
        if self.start_offset < 0:
            raise ValueError("start_offset must be >= 0")
        if self.end_offset < self.start_offset:
            raise ValueError("end_offset must be >= start_offset")
        if self.kind == DeadlineCandidateKind.EXPLICIT_DATE and self.normalized_date is None:
            raise ValueError("EXPLICIT_DATE candidates must have normalized_date")
        if self.kind == DeadlineCandidateKind.RELATIVE_PERIOD and (
            self.amount is None or self.unit is None
        ):
            raise ValueError("RELATIVE_PERIOD candidates must have amount and unit")


@dataclass
class DeadlineWarning:
    """A warning about the deadline extraction result."""

    code: DeadlineWarningCode
    message: str


@dataclass
class DeadlineExtractionResult:
    """Complete result of deadline candidate extraction.

    Attributes:
        document_id: The document that was analyzed.
        candidates: List of deadline candidates found (empty if none).
        warnings: List of warnings (always includes LEGAL_CALCULATION_NOT_PERFORMED).
        human_review_required: Always True — safety hard-gate.
    """

    document_id: str
    candidates: list[DeadlineCandidate] = field(default_factory=list)
    warnings: list[DeadlineWarning] = field(default_factory=list)
    human_review_required: bool = True
