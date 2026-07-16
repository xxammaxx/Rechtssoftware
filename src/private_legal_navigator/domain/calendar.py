"""Domain models for M6-A: Confirmed Reference Events and Calendar Arithmetic.

M6-A provides non-binding calculation previews. It computes NO legally
binding deadlines. Every output requires human review.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID


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


class CalculationWarningCode(StrEnum):
    """Stable warning codes for calendar calculation results."""

    # Inherited from M5:
    LEGAL_CALCULATION_NOT_PERFORMED = "LEGAL_CALCULATION_NOT_PERFORMED"
    MULTIPLE_DEADLINE_CANDIDATES = "MULTIPLE_DEADLINE_CANDIDATES"

    # M6-A - Confirmation gates:
    REFERENCE_EVENT_NOT_CONFIRMED = "REFERENCE_EVENT_NOT_CONFIRMED"
    REFERENCE_EVENT_REJECTED = "REFERENCE_EVENT_REJECTED"
    REFERENCE_EVENT_REVOKED = "REFERENCE_EVENT_REVOKED"
    MULTIPLE_REFERENCE_EVENTS = "MULTIPLE_REFERENCE_EVENTS"

    # M6-A - Duration validation:
    REFERENCE_DATE_REQUIRED = "REFERENCE_DATE_REQUIRED"
    DURATION_NOT_AVAILABLE = "DURATION_NOT_AVAILABLE"
    UNSUPPORTED_DURATION_UNIT = "UNSUPPORTED_DURATION_UNIT"
    INVALID_DURATION_AMOUNT = "INVALID_DURATION_AMOUNT"
    DURATION_LIMIT_EXCEEDED = "DURATION_LIMIT_EXCEEDED"

    # M6-A - Safety disclaimers:
    NO_WEEKEND_OR_HOLIDAY_ADJUSTMENT = "NO_WEEKEND_OR_HOLIDAY_ADJUSTMENT"
    NO_DELIVERY_OR_ANNOUNCEMENT_RULE_APPLIED = "NO_DELIVERY_OR_ANNOUNCEMENT_RULE_APPLIED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    CALCULATION_PREVIEW_ONLY = "CALCULATION_PREVIEW_ONLY"
    CALCULATION_NOT_PERFORMED = "CALCULATION_NOT_PERFORMED"

    # M6-A - Manual entry:
    MANUAL_ENTRY_WITHOUT_EVIDENCE = "MANUAL_ENTRY_WITHOUT_EVIDENCE"

    # M6-A - Range validation:
    CALCULATED_DATE_OUT_OF_RANGE = "CALCULATED_DATE_OUT_OF_RANGE"

    # M6-A - General validation:
    FIELD_TOO_LONG = "FIELD_TOO_LONG"
    INVALID_SOURCE_TYPE = "INVALID_SOURCE_TYPE"


@dataclass
class ReferenceEventCandidate:
    """A candidate reference event that could anchor a relative deadline.

    Attributes:
        candidate_id: Unique identifier for this candidate.
        document_id: The document this was detected in.
        deadline_candidate_id: The M5 DeadlineCandidate this relates to (if any).
        event_type: Semantic category of the event.
        suggested_date: The date detected or suggested.
        source_type: Where this candidate came from (auto-detected, user, etc.).
        source_reference: Reference to the originating data (max 100 chars).
        evidence_text: The original text that was the basis (max 2000 chars, not persisted).
        start_offset: Character offset in the document text.
        end_offset: Character offset in the document text.
        confirmation_status: Current lifecycle state.
    """

    candidate_id: UUID
    document_id: UUID
    deadline_candidate_id: UUID | None = None
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
        if len(self.source_reference) > 100:
            raise ValueError("source_reference exceeds 100 characters")
        if len(self.evidence_text) > 2000:
            raise ValueError("evidence_text exceeds 2000 characters")


@dataclass
class ConfirmedReferenceEvent:
    """An explicitly confirmed reference date with full audit trail.

    Once confirmed, this enables calendar arithmetic.
    The confirmation is immutable - changes create new records.

    Attributes:
        confirmation_id: Unique identifier for this confirmation.
        candidate_id: The candidate this confirmation refers to (null if manual).
        document_id: The document context.
        event_type: User-selected event category.
        confirmed_date: The user-confirmed reference date.
        source_type: Where the date came from.
        confirmation_method: How the user confirmed.
        confirmed_at: Timestamp of confirmation (UTC).
        confirmed_by: Human identifier (future: user ID, max 100 chars).
        evidence_note: Optional note (max 2000 chars, transient, not persisted).
        supersedes_confirmation_id: Previous confirmation this replaces (null if first).
    """

    confirmation_id: UUID
    candidate_id: UUID | None
    document_id: UUID
    event_type: EventType
    confirmed_date: date | None
    source_type: SourceType
    confirmation_method: ConfirmationMethod
    confirmed_at: datetime
    confirmed_by: str = ""
    evidence_note: str = ""
    supersedes_confirmation_id: UUID | None = None

    def __post_init__(self) -> None:
        if len(self.confirmed_by) > 100:
            raise ValueError("confirmed_by exceeds 100 characters")
        if len(self.evidence_note) > 2000:
            raise ValueError("evidence_note exceeds 2000 characters")


@dataclass(frozen=True)
class Duration:
    """A duration amount with unit for arithmetic calculation.

    Only DAY and WEEK are supported in M6-A.
    Frozen to ensure immutability.
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


@dataclass
class CalculationStep:
    """A single step in the arithmetic calculation.

    Attributes:
        step: Sequence number (1-based).
        operation: The arithmetic operation performed.
        input_date: The date before the operation.
        amount: Number of calendar days added.
        output_date: The resulting date.
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
    """The result of calendar arithmetic - a non-binding calculation preview.

    This is NOT a legal deadline. It is a purely mathematical date calculation.

    Attributes:
        calculation_id: Unique identifier for this calculation.
        confirmed_reference_event: The user-confirmed reference date.
        duration: The duration used for calculation.
        calculated_date: The resulting date.
        calculation_steps: Step-by-step arithmetic trail.
        adjustments_applied: Summary of what adjustments were (not) applied.
        legal_validity_assessed: Always false - no legal assessment.
        human_review_required: Always true - mandatory human review.
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
