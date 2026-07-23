"""FastAPI routes for M6-A reference events and calendar arithmetic API."""

import logging
import uuid
from datetime import date
from typing import cast

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from private_legal_navigator.api.errors import CaseNotFoundError, DocumentNotFoundError
from private_legal_navigator.api.reference_event_schemas import (
    CalculationPreviewRequest,
    CalculationStepResponse,
    CalculationWarningCodeSchema,
    CalendarCalculationResponse,
    ConfirmationHistoryResponse,
    ConfirmationMethodSchema,
    ConfirmationResponse,
    ConfirmationStatusSchema,
    ConfirmRequest,
    DurationResponse,
    DurationUnitSchema,
    EventTypeSchema,
    HistoryEntryResponse,
    ListReferenceEventsResponse,
    ReferenceEventCandidateResponse,
    SourceTypeSchema,
    WarningResponse,
)
from private_legal_navigator.application.calculation_service import CalculationService
from private_legal_navigator.application.case_repository import CaseRepository
from private_legal_navigator.application.document_repository import DocumentRepository
from private_legal_navigator.application.reference_event_service import (
    ReferenceEventService,
)
from private_legal_navigator.domain.reference_event import (
    MAX_DATE,
    MIN_DATE,
    ConfirmationMethod,
    EventType,
    SourceType,
)
from private_legal_navigator.infrastructure.safe_logging import safe_log_event

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/cases/{case_id}/documents/{document_id}/deadline-candidates/{candidate_id}",
    tags=["reference-events"],
)


def _get_ref_event_service(request: Request) -> ReferenceEventService:
    return cast(ReferenceEventService, request.app.state.reference_event_service)


def _get_calculation_service(request: Request) -> CalculationService:
    return cast(CalculationService, request.app.state.calculation_service)


def _get_case_repo(request: Request) -> CaseRepository:
    return cast(CaseRepository, request.app.state.case_repository)


def _get_document_repo(request: Request) -> DocumentRepository:
    return cast(DocumentRepository, request.app.state.document_repository)


def _resolve_case(case_id: uuid.UUID, repo: CaseRepository) -> None:
    """Verify case exists or raise 404."""
    case = repo.get_by_id(case_id)
    if case is None:
        raise CaseNotFoundError()


def _build_confirm_warnings(body: ConfirmRequest) -> list[WarningResponse]:
    """Build warnings list for a confirm response.

    Always includes HUMAN_REVIEW_REQUIRED. Additionally includes
    MANUAL_ENTRY_WITHOUT_EVIDENCE when a manual entry has no evidence_note.
    """
    warnings = [
        WarningResponse(
            code=CalculationWarningCodeSchema.HUMAN_REVIEW_REQUIRED,
            message="Die Bestätigung ersetzt keine rechtliche Prüfung.",
        )
    ]
    if (
        body.action == "confirm"
        and body.source_type == SourceTypeSchema.USER_MANUAL
        and not body.evidence_note
    ):
        warnings.append(
            WarningResponse(
                code=CalculationWarningCodeSchema.MANUAL_ENTRY_WITHOUT_EVIDENCE,
                message="Manuelle Eingabe ohne Beleg/Evidenz. Geringeres Audit-Gewicht.",
            )
        )
    return warnings


def _resolve_document(document_id: uuid.UUID, repo: DocumentRepository) -> None:
    """Verify document exists or raise 404."""
    doc = repo.get_by_id(document_id)
    if doc is None:
        raise DocumentNotFoundError()


# ── 1. GET reference-events ──


@router.get("/reference-events", response_model=ListReferenceEventsResponse)
def list_reference_events(
    case_id: uuid.UUID,
    document_id: uuid.UUID,
    candidate_id: int,
    request: Request,
) -> ListReferenceEventsResponse | Response:
    """List all reference event candidates for a deadline candidate."""
    _resolve_case(case_id, _get_case_repo(request))
    _resolve_document(document_id, _get_document_repo(request))

    # Validate candidate_id index bounds
    if candidate_id < 0:
        return JSONResponse(
            status_code=400,
            content={
                "detail": {
                    "code": "INVALID_CANDIDATE_INDEX",
                    "message": f"candidate_id must be >= 0, got {candidate_id}",
                }
            },
        )

    service = _get_ref_event_service(request)
    candidates = service.get_reference_event_candidates(document_id, candidate_id)

    events = [
        ReferenceEventCandidateResponse(
            candidate_id=c.candidate_id,
            event_type=EventTypeSchema(c.event_type.value),
            suggested_date=c.suggested_date,
            source_type=SourceTypeSchema(c.source_type.value),
            evidence_text=c.evidence_text,
            start_offset=c.start_offset,
            end_offset=c.end_offset,
            confirmation_status=ConfirmationStatusSchema(c.confirmation_status.value),
        )
        for c in candidates
    ]

    return ListReferenceEventsResponse(
        candidate_id=candidate_id,
        document_id=document_id,
        reference_events=events,
        warnings=[],
        human_review_required=True,
    )


# ── 2. POST confirm/reject/revoke ──


@router.post("/reference-events/confirm", response_model=ConfirmationResponse)
def confirm_reference_event(
    case_id: uuid.UUID,
    document_id: uuid.UUID,
    candidate_id: int,
    body: ConfirmRequest,
    request: Request,
) -> ConfirmationResponse | Response:
    """Confirm, reject, or revoke a reference event."""
    _resolve_case(case_id, _get_case_repo(request))
    _resolve_document(document_id, _get_document_repo(request))

    service = _get_ref_event_service(request)

    if body.action == "confirm":
        if body.confirmed_date is None:
            return JSONResponse(
                status_code=400,
                content={
                    "detail": {
                        "code": "INVALID_DATE",
                        "message": "confirmed_date is required for confirm action",
                    }
                },
            )
        # Parse and validate the confirmed_date string
        try:
            parsed_date = date.fromisoformat(body.confirmed_date)
        except (ValueError, TypeError):
            return JSONResponse(
                status_code=400,
                content={
                    "detail": {
                        "code": "INVALID_DATE",
                        "message": f"Invalid date format: {body.confirmed_date}. Use YYYY-MM-DD.",
                    }
                },
            )
        if parsed_date < MIN_DATE or parsed_date > MAX_DATE:
            return JSONResponse(
                status_code=400,
                content={
                    "detail": {
                        "code": "INVALID_DATE",
                        "message": (
                            f"Date {body.confirmed_date} out of valid range "
                            f"({MIN_DATE} to {MAX_DATE})."
                        ),
                    }
                },
            )
        if body.event_type is None or body.source_type is None:
            return JSONResponse(
                status_code=400,
                content={
                    "detail": {
                        "code": "VALIDATION_ERROR",
                        "message": "event_type and source_type are required for confirm",
                    }
                },
            )

        # Map source_type → confirmation_method
        method_map = {
            SourceTypeSchema.AUTO_DETECTED: ConfirmationMethodSchema.AUTO_SUGGESTED,
            SourceTypeSchema.USER_MANUAL: ConfirmationMethodSchema.MANUALLY_ENTERED,
            SourceTypeSchema.USER_CORRECTED: ConfirmationMethodSchema.CORRECTED,
        }
        confirmation_method = method_map.get(
            body.source_type, ConfirmationMethodSchema.AUTO_SUGGESTED
        )

        event = service.confirm(
            document_id=document_id,
            deadline_candidate_index=candidate_id,
            event_type=EventType(body.event_type.value),
            confirmed_date=parsed_date,
            source_type=SourceType(body.source_type.value),
            confirmation_method=ConfirmationMethod(confirmation_method.value),
            candidate_id=body.candidate_id,
            evidence_note=body.evidence_note or "",
        )

        safe_log_event(
            logger,
            "reference_event.confirmed",
            confirmation_id=str(event.confirmation_id),
            document_id=str(document_id),
        )

        return ConfirmationResponse(
            confirmation_id=event.confirmation_id,
            candidate_id=event.candidate_id,
            document_id=event.document_id,
            event_type=EventTypeSchema(event.event_type.value),
            confirmed_date=event.confirmed_date,
            source_type=SourceTypeSchema(event.source_type.value) if event.source_type else None,
            confirmation_method=ConfirmationMethodSchema(event.confirmation_method.value)
            if hasattr(event, "confirmation_method")
            else None,
            confirmation_status=ConfirmationStatusSchema.CONFIRMED,
            confirmed_at=event.confirmed_at,
            supersedes_confirmation_id=event.supersedes_confirmation_id,
            warnings=_build_confirm_warnings(body),
            human_review_required=True,
        )

    elif body.action == "reject":
        if body.event_type is None:
            return JSONResponse(
                status_code=400,
                content={
                    "detail": {
                        "code": "VALIDATION_ERROR",
                        "message": "event_type is required for reject",
                    }
                },
            )
        event = service.reject(
            document_id=document_id,
            deadline_candidate_index=candidate_id,
            event_type=EventType(body.event_type.value),
            candidate_id=body.candidate_id,
        )
        safe_log_event(
            logger,
            "reference_event.rejected",
            confirmation_id=str(event.confirmation_id),
            document_id=str(document_id),
        )
        return ConfirmationResponse(
            confirmation_id=event.confirmation_id,
            document_id=event.document_id,
            event_type=EventTypeSchema(event.event_type.value),
            confirmation_status=ConfirmationStatusSchema.REJECTED,
            confirmed_at=event.confirmed_at,
            warnings=[
                WarningResponse(
                    code=CalculationWarningCodeSchema.REFERENCE_EVENT_REJECTED,
                    message="Bezugsereignis abgelehnt. Eine Berechnung ist nicht möglich.",
                )
            ],
            human_review_required=True,
        )

    elif body.action == "revoke":
        if body.confirmation_id is None:
            return JSONResponse(
                status_code=400,
                content={
                    "detail": {
                        "code": "VALIDATION_ERROR",
                        "message": "confirmation_id is required for revoke",
                    }
                },
            )
        revoked = service.revoke(confirmation_id=body.confirmation_id)
        if revoked is None:
            return JSONResponse(
                status_code=404,
                content={
                    "detail": {
                        "code": "CONFIRMATION_NOT_FOUND",
                        "message": "Confirmation not found",
                    }
                },
            )

        return ConfirmationResponse(
            confirmation_id=revoked.confirmation_id,
            document_id=revoked.document_id,
            event_type=EventTypeSchema(revoked.event_type.value),
            confirmation_status=ConfirmationStatusSchema.REVOKED,
            confirmed_at=revoked.confirmed_at,
            supersedes_confirmation_id=body.confirmation_id,
            warnings=[
                WarningResponse(
                    code=CalculationWarningCodeSchema.REFERENCE_EVENT_REVOKED,
                    message="Bestätigung widerrufen. Eine Berechnung ist nicht mehr möglich.",
                )
            ],
            human_review_required=True,
        )

    return JSONResponse(
        status_code=400,
        content={
            "detail": {
                "code": "INVALID_CONFIRMATION_ACTION",
                "message": f"Unknown action: {body.action}",
            }
        },
    )


# ── 3. POST calculation-preview ──


@router.post("/calculation-preview", response_model=CalendarCalculationResponse)
def calculation_preview(
    case_id: uuid.UUID,
    document_id: uuid.UUID,
    candidate_id: int,
    body: CalculationPreviewRequest,
    request: Request,
) -> CalendarCalculationResponse | Response:
    """Request a non-binding calculation preview."""
    _resolve_case(case_id, _get_case_repo(request))
    _resolve_document(document_id, _get_document_repo(request))

    # Note: In production, the duration amount and unit would come from the M5 candidate.
    # For now, this is a stub that validates the confirmation exists.
    # The full M5 integration is part of the build phase.
    try:
        # Stub duration for response demonstration
        from private_legal_navigator.domain.reference_event import Duration, DurationUnit

        stub_duration = Duration(amount=14, unit=DurationUnit.DAY)
        repo = request.app.state.reference_event_repository
        event = repo.get_confirmation(body.confirmation_id)

        if event is None:
            return JSONResponse(
                status_code=404,
                content={
                    "detail": {
                        "code": "CONFIRMATION_NOT_FOUND",
                        "message": "No confirmed reference event exists for this candidate.",
                    }
                },
            )

        from private_legal_navigator.infrastructure.deterministic_calendar_arithmetic import (
            DeterministicCalendarArithmetic,
        )

        arithmetic = DeterministicCalendarArithmetic()
        result = arithmetic.calculate(event, stub_duration)

        safe_log_event(
            logger,
            "calendar_preview.generated",
            calculation_id=str(result.calculation_id) if result.calculation_id else None,
            document_id=str(document_id),
        )

        return CalendarCalculationResponse(
            calculation_id=result.calculation_id,
            calculated_date=result.calculated_date,
            calculation_steps=[
                CalculationStepResponse(
                    step=s.step,
                    operation=s.operation.value,
                    input_date=s.input_date,
                    amount=s.amount,
                    output_date=s.output_date,
                )
                for s in result.calculation_steps
            ],
            duration=DurationResponse(
                amount=stub_duration.amount,
                unit=DurationUnitSchema(stub_duration.unit.value),
                calendar_days=stub_duration.calendar_days,
            ),
            adjustments_applied=result.adjustments_applied,
            warnings=[
                WarningResponse(code=CalculationWarningCodeSchema(w), message=w)
                for w in result.warnings
            ],
            legal_validity_assessed=False,
            human_review_required=True,
        )

    except ValueError as e:
        error_code = str(e)
        if "REFERENCE_EVENT_NOT_CONFIRMED" in error_code:
            return JSONResponse(
                status_code=400,
                content={
                    "detail": {"code": "REFERENCE_EVENT_NOT_CONFIRMED", "message": error_code}
                },
            )
        if "UNSUPPORTED_DURATION_UNIT" in error_code:
            return JSONResponse(
                status_code=400,
                content={"detail": {"code": "UNSUPPORTED_DURATION_UNIT", "message": error_code}},
            )
        if "CALCULATED_DATE_OUT_OF_RANGE" in error_code:
            return JSONResponse(
                status_code=400,
                content={"detail": {"code": "CALCULATED_DATE_OUT_OF_RANGE", "message": error_code}},
            )
        return JSONResponse(
            status_code=400,
            content={"detail": {"code": "CALCULATION_NOT_PERFORMED", "message": error_code}},
        )


# ── 4. GET confirmation history ──


@router.get("/reference-events/history", response_model=ConfirmationHistoryResponse)
def confirmation_history(
    case_id: uuid.UUID,
    document_id: uuid.UUID,
    candidate_id: int,
    request: Request,
) -> ConfirmationHistoryResponse:
    """Get full confirmation history for a deadline candidate."""
    _resolve_case(case_id, _get_case_repo(request))
    _resolve_document(document_id, _get_document_repo(request))

    service = _get_ref_event_service(request)
    history = service.get_history(document_id, candidate_id)

    entries = [
        HistoryEntryResponse(
            confirmation_id=h.confirmation_id,
            confirmed_date=h.confirmed_date,
            event_type=EventTypeSchema(h.event_type.value),
            confirmation_status=ConfirmationStatusSchema.SUPERSEDED
            if i > 0
            else ConfirmationStatusSchema.CONFIRMED,
            confirmed_at=h.confirmed_at,
            supersedes_confirmation_id=h.supersedes_confirmation_id,
        )
        for i, h in enumerate(history)
    ]

    current_status = None
    if history:
        current_status = "confirmed"

    return ConfirmationHistoryResponse(
        candidate_id=candidate_id,
        document_id=document_id,
        confirmations=entries,
        current_status=current_status,
        human_review_required=True,
    )
