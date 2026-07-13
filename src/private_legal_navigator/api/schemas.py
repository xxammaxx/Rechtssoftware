"""Pydantic schemas for API request/response serialization."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class CreateCaseRequest(BaseModel):
    """Request body for creating a new case."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Titel des Falls (1–200 Zeichen)",
    )

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, v: str) -> str:
        """Reject titles that are empty or whitespace-only after stripping."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("Titel darf nicht leer sein")
        return stripped


class CaseResponse(BaseModel):
    """Response body for a single case."""

    case_id: UUID
    title: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CaseListResponse(BaseModel):
    """Response body for listing cases."""

    items: list[CaseResponse]
    count: int


class ErrorDetail(BaseModel):
    """Machine-readable error detail."""

    code: str
    message: str


class ErrorResponse(BaseModel):
    """Standard error response envelope."""

    error: ErrorDetail


class DocumentResponse(BaseModel):
    """Response body for a single document."""

    document_id: UUID
    case_id: UUID
    filename: str
    mime_type: str
    size_bytes: int
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    """Response body for listing documents."""

    items: list[DocumentResponse]
    count: int


class DocumentTextResponse(BaseModel):
    """Response body for extracted document text."""

    document_id: UUID
    text_content: str
    text_length: int
