"""Domain models for M6-A reference events and calendar arithmetic.

M6-A extends M5 (deadline candidate extraction) with:
1. Reference event candidates detected from document text
2. User-confirmed reference dates (persistent, versioned)
3. Pure calendar arithmetic (days/weeks only, non-binding preview)

M6-A berechnet KEINE rechtlich verbindliche Frist.
Das Ergebnis ist eine Berechnungsvorschau.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

# ──────────────────────────────────────────────
# Enums (T101)
# ──────────────────────────────────────────────


class EventType(StrEnum):
    """Semantic categories of reference events.

    These describe what the event IS, not what legal significance it has.
    """

    DELIVERY = "delivery"
    ANNOUNCEMENT = "announcement"
    RECEIPT = "receipt"
    ISSUE_DATE = "issue_date"
    PUBLICATION = "publication"
    APPLICATION = "application"
    USER_DEFINED = "user_defined"
    UNKNOWN = "unknown"


class ConfirmationStatus(StrEnum):
    """Lifecycle state of a reference event confirmation."""

    UNCONFIRMED = "unconfirmed"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    REVOKED = "revoked"
    SUPERSEDED = "superseded"


class SourceType(StrEnum):
    """Origin of the reference date."""

    AUTO_DETECTED = "auto_detected"
    USER_MANUAL = "user_manual"
    USER_CORRECTED = "user_corrected"


class ConfirmationMethod(StrEnum):
    """How the reference date was established."""

    AUTO_SUGGESTED = "auto_suggested"
    MANUALLY_ENTERED = "manually_entered"
    CORRECTED = "corrected"


class DurationUnit(StrEnum):
    """Supported duration units for arithmetic calculation."""

    DAY = "day"
    WEEK = "week"


class CalculationOperation(StrEnum):
    """Arithmetic operations for calendar calculation."""

    ADD_CALENDAR_DAYS = "ADD_CALENDAR_DAYS"
    ADD_CALENDAR_WEEKS = "ADD_CALENDAR_WEEKS"


# ──────────────────────────────────────────────
# Domain Entities (T102, T103, T104, T105)
# ──────────────────────────────────────────────


@dataclass
class ReferenceEventCandidate:
    """A candidate reference event that could anchor a relative deadline.

    Detected from document text. Always starts as UNCONFIRMED.
    The confirmation_status lifecycle is managed by the application layer.

    Attributes:
        candidate_id: Unique identifier for this candidate.
        document_id: The document this was detected in.
        deadline_candidate_index: Index of the M5 DeadlineCandidate (0-based).
        event_type: Semantic category of the event.
        suggested_date: The date detected or suggested (None if unresolvable).
        source_type: Where this candidate came from.
        source_reference: Reference to the originating data (max 100 chars).
        evidence_text: The original text that was the basis (max 2000 chars).
        start_offset: Character offset in the document text.
        end_offset: Character offset in the document text.
        confirmation_status: Current lifecycle state (always UNCONFIRMED initially).
    """

    candidate_id: UUID
    document_id: UUID
    deadline_candidate_index: int = 0
    event_type: EventType = EventType.UNKNOWN
    suggested_date: date | None = None
    source_type: SourceType = SourceType.AUTO_DETECTED
    source_reference: str = ""
    evidence_text: str = ""
    start_offset: int = 0
    end_offset: int = 0
    confirmation_status: ConfirmationStatus = ConfirmationStatus.UNCONFIRMED

    def __post_init__(self) -> None:
        if self.start_offset < 0:
            raise ValueError("start_offset must be >= 0")
        if self.end_offset < self.start_offset:
            raise ValueError("end_offset must be >= start_offset")
        if len(self.evidence_text) > 2000:
            raise ValueError("evidence_text exceeds 2000 character limit")
        if len(self.source_reference) > 100:
            raise ValueError("source_reference exceeds 100 character limit")


@dataclass
class ConfirmedReferenceEvent:
    """An explicitly confirmed reference date with full audit trail.

    Once confirmed, this enables calendar arithmetic.
    Confirmation records are versioned — changes create new records;
    previous records remain as SUPERSEDED or REVOKED for traceability.

    Attributes:
        confirmation_id: Unique identifier for this confirmation.
        candidate_id: The candidate this confirmation refers to (None if manual).
        document_id: The document context.
        event_type: User-selected event category.
        confirmed_date: The user-confirmed reference date.
        source_type: Where the date came from.
        confirmation_method: How the user confirmed.
        confirmed_at: Timestamp of confirmation (UTC).
        confirmed_by: Human identifier / label (max 100 chars).
        evidence_note: Transient note from the user (max 2000 chars).
        supersedes_confirmation_id: Previous confirmation this replaces.
    """

    confirmation_id: UUID
    document_id: UUID
    event_type: EventType
    confirmed_at: datetime
    deadline_candidate_index: int = 0
    confirmed_date: date | None = None
    source_type: SourceType = SourceType.AUTO_DETECTED
    confirmation_method: ConfirmationMethod = ConfirmationMethod.AUTO_SUGGESTED
    candidate_id: UUID | None = None
    confirmed_by: str = ""
    evidence_note: str = ""
    supersedes_confirmation_id: UUID | None = None

    def __post_init__(self) -> None:
        if len(self.confirmed_by) > 100:
            raise ValueError("confirmed_by exceeds 100 character limit")
        if len(self.evidence_note) > 2000:
            raise ValueError("evidence_note exceeds 2000 character limit")


# ──────────────────────────────────────────────
# Value Objects (T104)
# ──────────────────────────────────────────────


@dataclass(frozen=True)
class Duration:
    """A duration amount with unit for arithmetic calculation.

    Only DAY and WEEK are supported in M6-A.
    Frozen to ensure immutability.

    Attributes:
        amount: Positive integer duration amount.
        unit: DurationUnit (DAY or WEEK).
    """

    amount: int
    unit: DurationUnit

    @property
    def calendar_days(self) -> int:
        """Convert to calendar days for arithmetic."""
        if self.unit == DurationUnit.WEEK:
            return self.amount * 7
        return self.amount

    def __post_init__(self) -> None:
        if self.amount <= 0:
            raise ValueError("Duration amount must be positive")
        if self.amount > 36500:
            raise ValueError("Duration exceeds maximum (36500 days / ~100 years)")


# ──────────────────────────────────────────────
# Calculation Model (T105)
# ──────────────────────────────────────────────


@dataclass
class CalculationStep:
    """A single step in the arithmetic calculation.

    Attributes:
        step: Sequence number (1-based).
        operation: The arithmetic operation performed.
        input_date: The date before the operation (ISO format).
        amount: Number of calendar days added.
        output_date: The resulting date (ISO format).
    """

    step: int
    operation: CalculationOperation
    input_date: date
    amount: int
    output_date: date

    def __post_init__(self) -> None:
        if self.step < 1:
            raise ValueError("step must be >= 1")
        if self.amount < 0:
            raise ValueError("amount must be >= 0")


@dataclass
class CalendarCalculationCandidate:
    """The result of calendar arithmetic — a non-binding calculation preview.

    This is NOT a legal deadline. It is a purely mathematical date calculation.
    All safety flags are structurally set: human_review_required=true,
    legal_validity_assessed=false, all adjustments false.

    Attributes:
        calculation_id: Unique identifier for this calculation.
        reference_event: The user-confirmed reference event.
        duration: The duration used for calculation.
        calculated_date: The resulting date.
        calculation_steps: Step-by-step arithmetic trail.
        adjustments_applied: Summary of what adjustments were (not) applied.
        legal_validity_assessed: Always false — no legal assessment.
        human_review_required: Always true — mandatory human review.
        warnings: Warning codes describing limitations.
    """

    calculation_id: UUID | None = None
    confirmed_reference_event: ConfirmedReferenceEvent | None = None
    duration: Duration | None = None
    calculated_date: date | None = None
    calculation_steps: list[CalculationStep] = field(default_factory=list)
    adjustments_applied: dict[str, bool] = field(
        default_factory=lambda: {
            "weekend_adjustment_applied": False,
            "holiday_adjustment_applied": False,
            "legal_rule_applied": False,
            "delivery_fiction_applied": False,
            "announcement_fiction_applied": False,
        }
    )
    legal_validity_assessed: bool = False
    human_review_required: bool = True
    warnings: list[str] = field(default_factory=list)


# ──────────────────────────────────────────────
# Warning Codes (T106)
# ──────────────────────────────────────────────


class CalculationWarningCode(StrEnum):
    """Warning codes specific to calendar calculation.

    These codes MUST NOT change between releases to ensure
    downstream consumers can rely on them.
    """

    # Inherited from M5:
    LEGAL_CALCULATION_NOT_PERFORMED = "LEGAL_CALCULATION_NOT_PERFORMED"
    MULTIPLE_DEADLINE_CANDIDATES = "MULTIPLE_DEADLINE_CANDIDATES"

    # M6-A — Confirmation gates:
    REFERENCE_EVENT_NOT_CONFIRMED = "REFERENCE_EVENT_NOT_CONFIRMED"
    REFERENCE_EVENT_REJECTED = "REFERENCE_EVENT_REJECTED"
    REFERENCE_EVENT_REVOKED = "REFERENCE_EVENT_REVOKED"
    MULTIPLE_REFERENCE_EVENTS = "MULTIPLE_REFERENCE_EVENTS"

    # M6-A — Duration validation:
    REFERENCE_DATE_REQUIRED = "REFERENCE_DATE_REQUIRED"
    DURATION_NOT_AVAILABLE = "DURATION_NOT_AVAILABLE"
    UNSUPPORTED_DURATION_UNIT = "UNSUPPORTED_DURATION_UNIT"
    INVALID_DURATION_AMOUNT = "INVALID_DURATION_AMOUNT"
    DURATION_LIMIT_EXCEEDED = "DURATION_LIMIT_EXCEEDED"

    # M6-A — Candidate validation:
    INVALID_CANDIDATE_REFERENCE = "INVALID_CANDIDATE_REFERENCE"

    # M6-A — Safety disclaimers:
    NO_WEEKEND_OR_HOLIDAY_ADJUSTMENT = "NO_WEEKEND_OR_HOLIDAY_ADJUSTMENT"
    NO_DELIVERY_OR_ANNOUNCEMENT_RULE_APPLIED = "NO_DELIVERY_OR_ANNOUNCEMENT_RULE_APPLIED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    CALCULATION_PREVIEW_ONLY = "CALCULATION_PREVIEW_ONLY"
    CALCULATION_NOT_PERFORMED = "CALCULATION_NOT_PERFORMED"


# Domain constants (INV-M6A-23)
MIN_DATE: date = date(1900, 1, 1)
MAX_DATE: date = date(2099, 12, 31)
MAX_DURATION_CALENDAR_DAYS: int = 36500
