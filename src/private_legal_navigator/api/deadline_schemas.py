"""Pydantic schemas for M5 deadline candidate extraction API."""

from datetime import date
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class DeadlineCandidateKindSchema(StrEnum):
    """API representation of deadline candidate kind."""

    EXPLICIT_DATE = "explicit_date"
    RELATIVE_PERIOD = "relative_period"
    QUALITATIVE_REFERENCE = "qualitative_reference"


class DeadlineCertaintySchema(StrEnum):
    """API representation of deadline certainty."""

    EXACT = "exact"
    UNRESOLVED = "unresolved"
    AMBIGUOUS = "ambiguous"


class DeadlineWarningCodeSchema(StrEnum):
    """API representation of warning codes."""

    LEGAL_CALCULATION_NOT_PERFORMED = "LEGAL_CALCULATION_NOT_PERFORMED"
    NO_DEADLINE_CANDIDATE = "NO_DEADLINE_CANDIDATE"
    MULTIPLE_DEADLINE_CANDIDATES = "MULTIPLE_DEADLINE_CANDIDATES"
    RELATIVE_REFERENCE_REQUIRED = "RELATIVE_REFERENCE_REQUIRED"
    AMBIGUOUS_DATE = "AMBIGUOUS_DATE"


class DeadlineCandidateResponse(BaseModel):
    """Single deadline candidate in API response."""

    kind: DeadlineCandidateKindSchema
    raw_text: str
    start_offset: int
    end_offset: int
    normalized_date: date | None = None
    amount: int | None = None
    unit: str | None = None
    reference_required: bool = False
    certainty: DeadlineCertaintySchema
    rule_id: str


class DeadlineWarningResponse(BaseModel):
    """Warning in API response."""

    code: DeadlineWarningCodeSchema
    message: str


class DeadlineExtractionResponse(BaseModel):
    """Complete deadline extraction API response."""

    document_id: UUID
    candidates: list[DeadlineCandidateResponse] = Field(default_factory=list)
    warnings: list[DeadlineWarningResponse] = Field(default_factory=list)
    human_review_required: bool = True
