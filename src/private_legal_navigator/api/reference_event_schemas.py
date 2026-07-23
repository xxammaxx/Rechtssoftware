"""Pydantic schemas for M6-A reference events and calendar arithmetic API."""

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

# ── Enum schemas ──


class EventTypeSchema(StrEnum):
    """API representation of event type."""

    DELIVERY = "delivery"
    ANNOUNCEMENT = "announcement"
    RECEIPT = "receipt"
    ISSUE_DATE = "issue_date"
    PUBLICATION = "publication"
    APPLICATION = "application"
    USER_DEFINED = "user_defined"
    UNKNOWN = "unknown"


class ConfirmationStatusSchema(StrEnum):
    """API representation of confirmation status."""

    UNCONFIRMED = "unconfirmed"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    REVOKED = "revoked"
    SUPERSEDED = "superseded"


class SourceTypeSchema(StrEnum):
    """API representation of source type."""

    AUTO_DETECTED = "auto_detected"
    USER_MANUAL = "user_manual"
    USER_CORRECTED = "user_corrected"


class ConfirmationMethodSchema(StrEnum):
    """API representation of confirmation method."""

    AUTO_SUGGESTED = "auto_suggested"
    MANUALLY_ENTERED = "manually_entered"
    CORRECTED = "corrected"


class DurationUnitSchema(StrEnum):
    """API representation of duration unit."""

    DAY = "day"
    WEEK = "week"


class CalculationWarningCodeSchema(StrEnum):
    """API representation of calculation warning codes."""

    LEGAL_CALCULATION_NOT_PERFORMED = "LEGAL_CALCULATION_NOT_PERFORMED"
    REFERENCE_EVENT_NOT_CONFIRMED = "REFERENCE_EVENT_NOT_CONFIRMED"
    REFERENCE_EVENT_REJECTED = "REFERENCE_EVENT_REJECTED"
    REFERENCE_EVENT_REVOKED = "REFERENCE_EVENT_REVOKED"
    MULTIPLE_REFERENCE_EVENTS = "MULTIPLE_REFERENCE_EVENTS"
    REFERENCE_DATE_REQUIRED = "REFERENCE_DATE_REQUIRED"
    DURATION_NOT_AVAILABLE = "DURATION_NOT_AVAILABLE"
    UNSUPPORTED_DURATION_UNIT = "UNSUPPORTED_DURATION_UNIT"
    INVALID_DURATION_AMOUNT = "INVALID_DURATION_AMOUNT"
    DURATION_LIMIT_EXCEEDED = "DURATION_LIMIT_EXCEEDED"
    INVALID_CANDIDATE_REFERENCE = "INVALID_CANDIDATE_REFERENCE"
    NO_WEEKEND_OR_HOLIDAY_ADJUSTMENT = "NO_WEEKEND_OR_HOLIDAY_ADJUSTMENT"
    NO_DELIVERY_OR_ANNOUNCEMENT_RULE_APPLIED = "NO_DELIVERY_OR_ANNOUNCEMENT_RULE_APPLIED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    MANUAL_ENTRY_WITHOUT_EVIDENCE = "MANUAL_ENTRY_WITHOUT_EVIDENCE"
    CALCULATION_PREVIEW_ONLY = "CALCULATION_PREVIEW_ONLY"
    CALCULATION_NOT_PERFORMED = "CALCULATION_NOT_PERFORMED"


# ── Request schemas ──


class ConfirmRequest(BaseModel):
    """Request body for the confirm/reject/revoke endpoint."""

    action: str = Field(..., description="'confirm', 'reject', or 'revoke'")
    candidate_id: UUID | None = Field(
        None, description="UUID of the ReferenceEventCandidate (null for manual entry)"
    )
    event_type: EventTypeSchema | None = Field(None, description="Event category")
    confirmed_date: str | None = Field(
        None, description="Confirmed reference date (ISO format YYYY-MM-DD)"
    )
    source_type: SourceTypeSchema | None = Field(None, description="Origin of the date")
    confirmation_id: UUID | None = Field(None, description="Required for revoke action")
    evidence_note: str | None = Field(
        None, max_length=2000, description="Transient user note (max 2000 chars)"
    )


class CalculationPreviewRequest(BaseModel):
    """Request body for the calculation preview endpoint."""

    confirmation_id: UUID = Field(..., description="ID of the confirmed reference event")


# ── Response schemas ──


class WarningResponse(BaseModel):
    """Warning in API response."""

    code: CalculationWarningCodeSchema
    message: str


class ReferenceEventCandidateResponse(BaseModel):
    """A single reference event candidate in API response."""

    candidate_id: UUID
    event_type: EventTypeSchema
    suggested_date: date | None = None
    source_type: SourceTypeSchema
    evidence_text: str = ""
    start_offset: int = 0
    end_offset: int = 0
    confirmation_status: ConfirmationStatusSchema = ConfirmationStatusSchema.UNCONFIRMED


class ListReferenceEventsResponse(BaseModel):
    """Response for GET reference-events endpoint."""

    candidate_id: int
    document_id: UUID
    reference_events: list[ReferenceEventCandidateResponse] = Field(default_factory=list)
    warnings: list[WarningResponse] = Field(default_factory=list)
    human_review_required: bool = True


class ConfirmationResponse(BaseModel):
    """Response for POST confirm endpoint."""

    confirmation_id: UUID
    candidate_id: UUID | None = None
    document_id: UUID
    event_type: EventTypeSchema
    confirmed_date: date | None = None
    source_type: SourceTypeSchema | None = None
    confirmation_method: ConfirmationMethodSchema | None = None
    confirmation_status: ConfirmationStatusSchema
    confirmed_at: datetime
    supersedes_confirmation_id: UUID | None = None
    previous_confirmation: dict[str, object] | None = None
    warnings: list[WarningResponse] = Field(default_factory=list)
    human_review_required: bool = True


class CalculationStepResponse(BaseModel):
    """A single calculation step in the response."""

    step: int
    operation: str
    input_date: date
    amount: int
    output_date: date


class DurationResponse(BaseModel):
    """Duration information in calculation response."""

    amount: int
    unit: DurationUnitSchema
    calendar_days: int


class CalendarCalculationResponse(BaseModel):
    """Response for POST calculation-preview endpoint."""

    result_type: str = "calculated_candidate"
    calculation_id: UUID | None = None
    reference_event: ConfirmationResponse | None = None
    duration: DurationResponse | None = None
    calculated_date: date | None = None
    calculation_steps: list[CalculationStepResponse] = Field(default_factory=list)
    adjustments_applied: dict[str, bool] = Field(
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
    warnings: list[WarningResponse] = Field(default_factory=list)


class HistoryEntryResponse(BaseModel):
    """A single entry in the confirmation history."""

    confirmation_id: UUID
    confirmed_date: date | None = None
    event_type: EventTypeSchema
    confirmation_status: ConfirmationStatusSchema
    confirmed_at: datetime
    supersedes_confirmation_id: UUID | None = None


class ConfirmationHistoryResponse(BaseModel):
    """Response for GET confirmation history endpoint."""

    candidate_id: int
    document_id: UUID
    confirmations: list[HistoryEntryResponse] = Field(default_factory=list)
    current_status: str | None = None
    human_review_required: bool = True
