"""FastAPI routes for M6-A Reference Events and Calendar Arithmetic."""

from datetime import date
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from private_legal_navigator.api.event_schemas import (
    CalculationPreviewRequest,
    CalculationPreviewResponse,
    CalculationStepOut,
    ConfirmRequest,
    ConfirmResponse,
    DurationOut,
    HistoryEntryOut,
    HistoryResponse,
    ReferenceEventCandidateOut,
    ReferenceEventInCalculation,
    ReferenceEventListResponse,
    WarningOut,
)
from private_legal_navigator.application.deadline_extractor import DeadlineExtractor
from private_legal_navigator.application.document_repository import DocumentRepository
from private_legal_navigator.domain.calendar import (
    ConfirmationMethod,
    EventType,
    SourceType,
)
from private_legal_navigator.domain.deadline import DeadlineCandidateKind

router = APIRouter(
    prefix="/api/v1/cases/{case_id}/documents/{document_id}/deadline-candidates/{candidate_id}",
    tags=["reference-events"],
)


def _get_services(request: Request) -> dict[str, Any]:
    """Extract dependencies from app state."""
    return {
        "event_service": request.app.state.event_service,
        "document_repo": request.app.state.document_repository,
        "deadline_extractor": request.app.state.deadline_extractor,
    }


def _validate_candidate_access(
    document_repo: DocumentRepository,
    deadline_extractor: DeadlineExtractor,
    document_id: UUID,
    candidate_id: int,
) -> tuple[dict[str, Any] | None, Any]:
    """Validate document exists and candidate index is valid.

    Returns (error_dict, candidates) or (None, candidates).
    """
    document = document_repo.get_by_id(document_id)
    if document is None:
        return {"error": True, "code": "DOCUMENT_NOT_FOUND"}, None

    result = deadline_extractor.extract(document.text_content)
    candidates = result.candidates
    if candidate_id < 0 or candidate_id >= len(candidates):
        return {"error": True, "code": "INVALID_CANDIDATE_INDEX"}, None

    return None, candidates


# --- 1. List Reference Event Candidates ---


@router.get("/reference-events", response_model=None)
def list_reference_events(
    case_id: str,
    document_id: str,
    candidate_id: int,
    request: Request,
) -> ReferenceEventListResponse | JSONResponse:
    """List possible reference events for a deadline candidate."""
    svc = _get_services(request)
    doc_repo = svc["document_repo"]
    extractor = svc["deadline_extractor"]

    doc_uuid = UUID(document_id)
    err, candidates = _validate_candidate_access(doc_repo, extractor, doc_uuid, candidate_id)
    if err is not None:
        code = err.get("code", "UNKNOWN")
        return JSONResponse(
            status_code=404 if code == "DOCUMENT_NOT_FOUND" else 400,
            content={"detail": {"code": code, "message": _error_message(code)}},
        )

    candidate = candidates[candidate_id]
    if candidate.kind != DeadlineCandidateKind.RELATIVE_PERIOD:
        return JSONResponse(
            status_code=400,
            content={
                "detail": {
                    "code": "NOT_A_RELATIVE_CANDIDATE",
                    "message": "Nur RELATIVE_PERIOD-Kandidaten haben Bezugsereignisse.",
                }
            },
        )

    # Build reference event candidates from explicit dates in the document
    ref_events: list[ReferenceEventCandidateOut] = []
    for c in candidates:
        if c.kind == DeadlineCandidateKind.EXPLICIT_DATE and c.normalized_date:
            ref_events.append(
                ReferenceEventCandidateOut(
                    candidate_id=uuid4(),
                    event_type="issue_date",
                    suggested_date=c.normalized_date,
                    source_type="auto_detected",
                    evidence_text=c.raw_text,
                    start_offset=c.start_offset,
                    end_offset=c.end_offset,
                    confirmation_status="unconfirmed",
                )
            )

    # Also add the candidate itself as context
    if candidate.kind == DeadlineCandidateKind.RELATIVE_PERIOD:
        ref_events.append(
            ReferenceEventCandidateOut(
                candidate_id=uuid4(),
                event_type="unknown",
                suggested_date=None,
                source_type="auto_detected",
                evidence_text=candidate.raw_text,
                start_offset=candidate.start_offset,
                end_offset=candidate.end_offset,
                confirmation_status="unconfirmed",
            )
        )

    warnings = []
    if len(ref_events) > 1:
        warnings.append(
            WarningOut(
                code="MULTIPLE_REFERENCE_EVENTS",
                message=(
                    "Mehrere mögliche Bezugsereignisse gefunden. "
                    "Bitte wählen Sie das zutreffende Ereignis aus."
                ),
            )
        )
    warnings.append(
        WarningOut(
            code="REFERENCE_EVENT_NOT_CONFIRMED",
            message=(
                "Kein Bezugsereignis wurde bestätigt. "
                "Eine Berechnung ist erst nach Bestätigung möglich."
            ),
        )
    )

    return ReferenceEventListResponse(
        candidate_id=candidate_id,
        document_id=doc_uuid,
        reference_events=ref_events,
        warnings=warnings,
        human_review_required=True,
    )


# --- 2. Confirm / Reject / Revoke ---


@router.post("/reference-events/confirm", response_model=None)
def confirm_reference_event(
    case_id: str,
    document_id: str,
    candidate_id: int,
    body: ConfirmRequest,
    request: Request,
) -> ConfirmResponse | JSONResponse:
    """Confirm, reject, or revoke a reference event."""
    svc = _get_services(request)
    event_service = svc["event_service"]
    doc_repo = svc["document_repo"]
    extractor = svc["deadline_extractor"]

    doc_uuid = UUID(document_id)

    # Validate document access
    err, _ = _validate_candidate_access(doc_repo, extractor, doc_uuid, candidate_id)
    if err is not None:
        code = err.get("code", "UNKNOWN")
        return JSONResponse(
            status_code=404 if code == "DOCUMENT_NOT_FOUND" else 400,
            content={"detail": {"code": code, "message": _error_message(code)}},
        )

    action = body.action.lower()

    if action == "revoke":
        if body.confirmation_id is None:
            return JSONResponse(
                status_code=400,
                content={
                    "detail": {
                        "code": "INVALID_CONFIRMATION_ACTION",
                        "message": "confirmation_id is required for revoke.",
                    }
                },
            )
        try:
            event = event_service.revoke(body.confirmation_id, doc_uuid)
        except ValueError:
            return JSONResponse(
                status_code=404,
                content={
                    "detail": {
                        "code": "CONFIRMATION_NOT_FOUND",
                        "message": f"Confirmation {body.confirmation_id} not found.",
                    }
                },
            )

        # Get prior confirmation for the response
        prior = event_service._repo.get_by_id(body.confirmation_id)
        previous = None
        if prior:
            previous = {
                "confirmation_id": str(prior.confirmation_id),
                "confirmed_date": (
                    prior.confirmed_date.isoformat() if prior.confirmed_date else None
                ),
                "confirmation_status": "superseded",
            }

        return ConfirmResponse(
            confirmation_id=event.confirmation_id,
            document_id=doc_uuid,
            supersedes_confirmation_id=body.confirmation_id,
            confirmation_status="revoked",
            confirmed_at=event.confirmed_at,
            previous_confirmation=previous,
            warnings=[
                WarningOut(
                    code="REFERENCE_EVENT_REVOKED",
                    message="Bestätigung widerrufen. Eine Berechnung ist nicht mehr möglich.",
                )
            ],
            human_review_required=True,
        )

    if action == "reject":
        event_type = EventType(body.event_type) if body.event_type else EventType.UNKNOWN
        event = event_service.reject(
            document_id=doc_uuid,
            candidate_id=body.candidate_id,
            event_type=event_type,
        )
        return ConfirmResponse(
            confirmation_id=event.confirmation_id,
            candidate_id=body.candidate_id,
            document_id=doc_uuid,
            event_type=event_type.value,
            confirmation_status="rejected",
            confirmed_at=event.confirmed_at,
            warnings=[
                WarningOut(
                    code="REFERENCE_EVENT_REJECTED",
                    message="Bezugsereignis abgelehnt. Eine Berechnung ist nicht möglich.",
                )
            ],
            human_review_required=True,
        )

    if action == "confirm":
        # Parse the confirmed date
        confirmed_date_str = body.confirmed_date
        if not confirmed_date_str:
            return JSONResponse(
                status_code=400,
                content={
                    "detail": {
                        "code": "INVALID_DATE",
                        "message": "confirmed_date is required for confirm action.",
                    }
                },
            )

        try:
            confirmed_date = date.fromisoformat(confirmed_date_str)
        except (ValueError, TypeError):
            return JSONResponse(
                status_code=400,
                content={
                    "detail": {
                        "code": "INVALID_DATE",
                        "message": f"'{confirmed_date_str}' is not a valid ISO date (YYYY-MM-DD).",
                    }
                },
            )

        # Validate date range
        if confirmed_date < date(1900, 1, 1) or confirmed_date > date(2099, 12, 31):
            return JSONResponse(
                status_code=400,
                content={
                    "detail": {
                        "code": "INVALID_DATE",
                        "message": "Date must be between 1900-01-01 and 2099-12-31.",
                    }
                },
            )

        # Validate source_type
        source_type_str = body.source_type or "auto_detected"
        try:
            source_type = SourceType(source_type_str)
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={
                    "detail": {
                        "code": "INVALID_SOURCE_TYPE",
                        "message": f"Unknown source_type: {source_type_str}.",
                    }
                },
            )

        event_type = EventType(body.event_type) if body.event_type else EventType.UNKNOWN

        event = event_service.confirm(
            document_id=doc_uuid,
            candidate_id=body.candidate_id,
            event_type=event_type,
            confirmed_date=confirmed_date,
            source_type=source_type,
            confirmed_by="",
            evidence_note=body.evidence_note[:2000],
        )

        # Map status for response
        status_map = {
            ConfirmationMethod.AUTO_SUGGESTED: "confirmed",
            ConfirmationMethod.MANUALLY_ENTERED: "confirmed",
            ConfirmationMethod.CORRECTED: "confirmed",
        }

        warnings = [
            WarningOut(
                code="HUMAN_REVIEW_REQUIRED",
                message="Die Bestätigung ersetzt keine rechtliche Prüfung.",
            )
        ]
        if source_type == SourceType.USER_MANUAL and not body.evidence_note:
            warnings.append(
                WarningOut(
                    code="MANUAL_ENTRY_WITHOUT_EVIDENCE",
                    message="Manuelle Eingabe ohne Beleg. Geringeres Audit-Gewicht.",
                )
            )

        return ConfirmResponse(
            confirmation_id=event.confirmation_id,
            candidate_id=body.candidate_id,
            document_id=doc_uuid,
            event_type=event_type.value,
            confirmed_date=confirmed_date,
            source_type=source_type.value,
            confirmation_method=event.confirmation_method.value,
            confirmation_status=status_map.get(event.confirmation_method, "confirmed"),
            confirmed_at=event.confirmed_at,
            supersedes_confirmation_id=event.supersedes_confirmation_id,
            warnings=warnings,
            human_review_required=True,
        )

    # Unknown action
    return JSONResponse(
        status_code=400,
        content={
            "detail": {
                "code": "INVALID_CONFIRMATION_ACTION",
                "message": f"Unknown action: {action}. Use 'confirm', 'reject', or 'revoke'.",
            }
        },
    )


# --- 3. Calculation Preview ---


@router.post("/calculation-preview", response_model=None)
def calculation_preview(
    case_id: str,
    document_id: str,
    candidate_id: int,
    body: CalculationPreviewRequest,
    request: Request,
) -> CalculationPreviewResponse | JSONResponse:
    """Request a non-binding arithmetic calculation preview."""
    svc = _get_services(request)
    event_service = svc["event_service"]
    doc_repo = svc["document_repo"]
    extractor = svc["deadline_extractor"]

    doc_uuid = UUID(document_id)

    # Validate document and candidate
    err, candidates = _validate_candidate_access(doc_repo, extractor, doc_uuid, candidate_id)
    if err is not None:
        code = err.get("code", "UNKNOWN")
        return JSONResponse(
            status_code=404 if code == "DOCUMENT_NOT_FOUND" else 400,
            content={"detail": {"code": code, "message": _error_message(code)}},
        )

    candidate = candidates[candidate_id]

    # Validate M5 candidate is RELATIVE_PERIOD with duration
    if candidate.kind != DeadlineCandidateKind.RELATIVE_PERIOD:
        return JSONResponse(
            status_code=400,
            content={
                "detail": {
                    "code": "DURATION_NOT_AVAILABLE",
                    "message": "Der Kandidat hat keine berechenbare Dauer.",
                }
            },
        )

    if candidate.amount is None or candidate.unit is None:
        return JSONResponse(
            status_code=400,
            content={
                "detail": {
                    "code": "DURATION_NOT_AVAILABLE",
                    "message": "Keine Dauer verfügbar für diesen Kandidaten.",
                }
            },
        )

    # Get the confirmed reference event
    event = event_service._repo.get_by_id(body.confirmation_id)
    if event is None:
        return JSONResponse(
            status_code=404,
            content={
                "detail": {
                    "code": "CONFIRMATION_NOT_FOUND",
                    "message": f"Confirmation {body.confirmation_id} not found.",
                }
            },
        )

    if event.confirmed_date is None:
        return JSONResponse(
            status_code=400,
            content={
                "detail": {
                    "code": "REFERENCE_EVENT_NOT_CONFIRMED",
                    "message": "Kein bestätigtes Bezugsdatum vorhanden.",
                }
            },
        )

    duration_amount = candidate.amount
    duration_unit = candidate.unit

    # Validate duration
    if duration_amount <= 0:
        return JSONResponse(
            status_code=400,
            content={
                "detail": {
                    "code": "INVALID_DURATION_AMOUNT",
                    "message": "Dauer muss positiv sein.",
                }
            },
        )

    if duration_amount > 36500:
        return JSONResponse(
            status_code=400,
            content={
                "detail": {
                    "code": "DURATION_LIMIT_EXCEEDED",
                    "message": f"Dauer {duration_amount} überschreitet Maximum (36500).",
                }
            },
        )

    # Map duration unit
    german_units = {"Tag": "day", "tag": "day", "Woche": "week", "woche": "week"}
    unit = german_units.get(duration_unit, duration_unit)

    if unit not in ("day", "week"):
        return JSONResponse(
            status_code=400,
            content={
                "detail": {
                    "code": "UNSUPPORTED_DURATION_UNIT",
                    "message": (
                        f"Die Dauer-Einheit '{unit}' wird nicht unterstützt. "
                        "Nur 'day' und 'week' sind verfügbar."
                    ),
                }
            },
        )

    # Compute
    result = event_service.calculate_preview(
        document_id=doc_uuid,
        candidate_index=candidate_id,
        confirmation_id=body.confirmation_id,
        duration_amount=duration_amount,
        duration_unit=unit,
    )

    if result.calculated_date is None:
        # Return error based on warnings
        warning_codes = result.warnings
        return JSONResponse(
            status_code=400,
            content={
                "detail": {
                    "code": warning_codes[0] if warning_codes else "CALCULATION_NOT_PERFORMED",
                    "message": _error_message(
                        warning_codes[0] if warning_codes else "CALCULATION_NOT_PERFORMED"
                    ),
                }
            },
        )

    # Build response
    calc_steps = [
        CalculationStepOut(
            step=s.step,
            operation=s.operation.value,
            input_date=s.input_date,
            amount=s.amount,
            output_date=s.output_date,
        )
        for s in result.calculation_steps
    ]

    return CalculationPreviewResponse(
        result_type="calculated_candidate",
        calculation_id=uuid4(),
        reference_event=ReferenceEventInCalculation(
            confirmation_id=event.confirmation_id,
            event_type=event.event_type.value,
            confirmed_date=event.confirmed_date,
            confirmation_status="confirmed",
            confirmation_method=event.confirmation_method.value,
            source_type=event.source_type.value,
        ),
        duration=DurationOut(
            amount=duration_amount,
            unit=unit,
            calendar_days=(duration_amount * 7 if unit == "week" else duration_amount),
        ),
        calculated_date=result.calculated_date,
        calculation_steps=calc_steps,
        adjustments=result.adjustments_applied,
        legal_validity_assessed=False,
        human_review_required=True,
        warnings=[WarningOut(code=w, message=_warning_message(w)) for w in result.warnings],
    )


# --- 4. Get Confirmation History ---


@router.get("/reference-events/history", response_model=None)
def get_confirmation_history(
    case_id: str,
    document_id: str,
    candidate_id: int,
    request: Request,
) -> HistoryResponse | JSONResponse:
    """Get full confirmation audit trail for a candidate."""
    svc = _get_services(request)
    event_service = svc["event_service"]
    doc_repo = svc["document_repo"]
    extractor = svc["deadline_extractor"]

    doc_uuid = UUID(document_id)
    err, _ = _validate_candidate_access(doc_repo, extractor, doc_uuid, candidate_id)
    if err is not None:
        code = err.get("code", "UNKNOWN")
        return JSONResponse(
            status_code=404 if code == "DOCUMENT_NOT_FOUND" else 400,
            content={"detail": {"code": code, "message": _error_message(code)}},
        )

    history = event_service.get_history(doc_uuid, candidate_id)

    entries = []
    current_status = "unconfirmed"

    for event in history:
        # Determine effective status
        if event.confirmed_date is None:
            status = "revoked" if event.supersedes_confirmation_id is not None else "rejected"
        else:
            status = "confirmed"

        entries.append(
            HistoryEntryOut(
                confirmation_id=event.confirmation_id,
                confirmed_date=event.confirmed_date,
                event_type=event.event_type.value,
                confirmation_status=status,
                confirmed_at=event.confirmed_at,
                supersedes_confirmation_id=event.supersedes_confirmation_id,
            )
        )
        if status == "revoked":
            current_status = "revoked"
        elif status == "confirmed":
            current_status = "confirmed"
        elif status == "rejected" and current_status == "unconfirmed":
            current_status = "rejected"

    return HistoryResponse(
        candidate_id=candidate_id,
        document_id=doc_uuid,
        confirmations=entries,
        current_status=current_status,
        human_review_required=True,
    )


# --- Helpers ---


def _error_message(code: str) -> str:
    """Return a human-readable error message for a given error code."""
    messages: dict[str, str] = {
        "CASE_NOT_FOUND": "Der Fall wurde nicht gefunden.",
        "DOCUMENT_NOT_FOUND": "Das angeforderte Dokument wurde nicht gefunden.",
        "INVALID_CANDIDATE_INDEX": "Der Kandidaten-Index ist ungültig.",
        "NOT_A_RELATIVE_CANDIDATE": "Nur RELATIVE_PERIOD-Kandidaten haben Bezugsereignisse.",
        "CONFIRMATION_NOT_FOUND": "Die Bestätigung wurde nicht gefunden.",
        "INVALID_CONFIRMATION_ACTION": "Unbekannte Aktion.",
        "INVALID_DATE": "Ungültiges Datum.",
        "ALREADY_CONFIRMED": "Bezugsereignis ist bereits bestätigt.",
        "ALREADY_REVOKED": "Bezugsereignis ist bereits widerrufen.",
        "REFERENCE_EVENT_NOT_CONFIRMED": "Kein bestätigtes Bezugsdatum vorhanden.",
        "REFERENCE_EVENT_REVOKED": "Bezugsereignis wurde widerrufen.",
        "DURATION_NOT_AVAILABLE": "Keine Dauer verfügbar.",
        "UNSUPPORTED_DURATION_UNIT": "Dauer-Einheit wird nicht unterstützt.",
        "INVALID_DURATION_AMOUNT": "Dauer muss positiv sein.",
        "DURATION_LIMIT_EXCEEDED": "Dauer überschreitet Maximum.",
        "CALCULATION_NOT_PERFORMED": "Berechnung nicht durchgeführt.",
        "INVALID_SOURCE_TYPE": "Ungültiger source_type.",
        "FIELD_TOO_LONG": "Freitextfeld überschreitet maximale Länge.",
    }
    return messages.get(code, f"Fehler: {code}")


def _warning_message(code: str) -> str:
    """Return a human-readable warning message for a given warning code."""
    messages: dict[str, str] = {
        "CALCULATION_PREVIEW_ONLY": (
            "Diese Berechnung ist eine unverbindliche Vorschau. "
            "Sie stellt KEINE rechtlich verbindliche Frist dar."
        ),
        "NO_WEEKEND_OR_HOLIDAY_ADJUSTMENT": (
            "Wochenenden und Feiertage wurden nicht berücksichtigt. "
            "Die tatsächliche rechtliche Frist kann abweichen."
        ),
        "NO_DELIVERY_OR_ANNOUNCEMENT_RULE_APPLIED": (
            "Es wurden keine Zustellungs- oder Bekanntgaberegeln angewendet."
        ),
        "HUMAN_REVIEW_REQUIRED": (
            "Menschliche Prüfung zwingend erforderlich. Nicht zur Fristwahrung geeignet."
        ),
        "LEGAL_CALCULATION_NOT_PERFORMED": (
            "Es wurde keine rechtliche Fristberechnung durchgeführt. "
            "Diese Ausgabe ist eine rein mathematische Datumsberechnung."
        ),
    }
    return messages.get(code, code)
