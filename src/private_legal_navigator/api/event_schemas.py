"""Pydantic schemas for M6-A Reference Events and Calendar Arithmetic API."""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# --- Reference Event Candidates ---


class ReferenceEventCandidateOut(BaseModel):
    """A possible reference event for a deadline candidate."""

    candidate_id: UUID
    event_type: str
    suggested_date: date | None = None
    source_type: str
    evidence_text: str = ""
    start_offset: int = 0
    end_offset: int = 0
    confirmation_status: str = "unconfirmed"

    model_config = {"from_attributes": True}


class WarningOut(BaseModel):
    """A warning about the response."""

    code: str
    message: str


class ReferenceEventListResponse(BaseModel):
    """Response for listing reference event candidates."""

    candidate_id: int
    document_id: UUID
    reference_events: list[ReferenceEventCandidateOut] = Field(default_factory=list)
    warnings: list[WarningOut] = Field(default_factory=list)
    human_review_required: bool = True


# --- Confirmation ---


class ConfirmRequest(BaseModel):
    """Request to confirm, reject, or revoke a reference event."""

    action: str  # "confirm", "reject", "revoke"
    candidate_id: UUID | None = None
    event_type: str | None = None
    confirmed_date: str | None = None  # ISO date YYYY-MM-DD
    source_type: str | None = None  # "auto_detected", "user_manual", "user_corrected"
    confirmation_id: UUID | None = None
    evidence_note: str = ""


class ConfirmResponse(BaseModel):
    """Response after confirming/rejecting/revoking a reference event."""

    confirmation_id: UUID
    candidate_id: UUID | None = None
    document_id: UUID
    event_type: str | None = None
    confirmed_date: date | None = None
    source_type: str | None = None
    confirmation_method: str | None = None
    confirmation_status: str
    confirmed_at: datetime
    supersedes_confirmation_id: UUID | None = None
    previous_confirmation: dict[str, Any] | None = None
    warnings: list[WarningOut] = Field(default_factory=list)
    human_review_required: bool = True


# --- Calculation Preview ---


class CalculationPreviewRequest(BaseModel):
    """Request a non-binding calculation preview."""

    confirmation_id: UUID


class CalculationStepOut(BaseModel):
    """A single step in the arithmetic calculation."""

    step: int
    operation: str
    input_date: date
    amount: int
    output_date: date


class DurationOut(BaseModel):
    """Duration used for calculation."""

    amount: int
    unit: str
    calendar_days: int


class ReferenceEventInCalculation(BaseModel):
    """The reference event used in a calculation."""

    confirmation_id: UUID
    event_type: str
    confirmed_date: date
    confirmation_status: str
    confirmation_method: str
    source_type: str


class CalculationPreviewResponse(BaseModel):
    """Response for a calculation preview."""

    result_type: str = "calculated_candidate"
    calculation_id: UUID | None = None
    reference_event: ReferenceEventInCalculation | None = None
    duration: DurationOut | None = None
    calculated_date: date | None = None
    calculation_steps: list[CalculationStepOut] = Field(default_factory=list)
    adjustments: dict[str, bool] = Field(default_factory=dict)
    legal_validity_assessed: bool = False
    human_review_required: bool = True
    warnings: list[WarningOut] = Field(default_factory=list)


# --- History ---


class HistoryEntryOut(BaseModel):
    """A single entry in the confirmation history."""

    confirmation_id: UUID
    confirmed_date: date | None = None
    event_type: str
    confirmation_status: str
    confirmed_at: datetime
    supersedes_confirmation_id: UUID | None = None


class HistoryResponse(BaseModel):
    """Response for confirmation history."""

    candidate_id: int
    document_id: UUID
    confirmations: list[HistoryEntryOut] = Field(default_factory=list)
    current_status: str = "unconfirmed"
    human_review_required: bool = True


# --- Error ---


class ErrorDetail(BaseModel):
    """Standard error envelope detail."""

    code: str
    message: str


class ErrorResponse(BaseModel):
    """Standard error envelope."""

    detail: ErrorDetail
