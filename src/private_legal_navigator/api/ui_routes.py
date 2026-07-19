"""M6-UI HTML routes — read-only and interactive confirmation.

All routes use the Application Layer orchestrator and produce
server-rendered HTML via Jinja2 templates. No direct repository access.
"""

import logging
import uuid
from datetime import date as date_type

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from starlette.templating import Jinja2Templates

from private_legal_navigator.application.local_confirmation_workspace_service import (
    LocalConfirmationWorkspaceService,
)
from private_legal_navigator.application.reference_event_repository import (
    IdempotencyKeyConflictError,
)
from private_legal_navigator.application.ui_view_models import (
    BaseContext,
    ErrorView,
)
from private_legal_navigator.domain.reference_event import (
    MAX_DATE,
    MIN_DATE,
    EventType,
)
from private_legal_navigator.infrastructure.safe_logging import safe_log_event, safe_log_failure
from private_legal_navigator.middleware.security_dependencies import ui_post_security

logger = logging.getLogger("private_legal_navigator.ui")

router = APIRouter(prefix="/ui", tags=["ui"])


def _get_workspace_service(request: Request) -> LocalConfirmationWorkspaceService:
    """Retrieve the workspace service from app state."""
    svc = request.app.state.workspace_service
    assert isinstance(svc, LocalConfirmationWorkspaceService)
    return svc


def _get_templates(request: Request) -> Jinja2Templates:
    """Retrieve the Jinja2 templates instance from app state."""
    tpl = request.app.state.templates
    assert isinstance(tpl, Jinja2Templates)
    return tpl


def _base_context(page_title: str = "PrivateLegalNavigator") -> BaseContext:
    return BaseContext(page_title=page_title)


def _render_error(
    request: Request,
    status_code: int,
    title: str,
    message: str,
    detail: str = "",
) -> HTMLResponse:
    """Render a sanitised error page.

    Never exposes stack traces, exception messages, internal paths,
    or database details.
    """
    templates = _get_templates(request)
    ctx = _base_context(page_title=f"Fehler {status_code} — {title}")
    error = ErrorView(
        status_code=status_code,
        title=title,
        message=message,
        detail=detail or "",
    )
    return HTMLResponse(
        content=templates.get_template("errors/error.html").render(
            {"request": request, "base": ctx, "error": error}
        ),
        status_code=status_code,
    )


# ---------------------------------------------------------------------------
# Route: GET /ui/
# ---------------------------------------------------------------------------


@router.get("/")
async def ui_index(request: Request) -> RedirectResponse:
    """Redirect to the case list."""
    return RedirectResponse(url="/ui/cases", status_code=303)


# ---------------------------------------------------------------------------
# Route: GET /ui/cases
# ---------------------------------------------------------------------------


@router.get("/cases")
async def ui_case_list(request: Request) -> HTMLResponse:
    """Render the case list page."""
    svc = _get_workspace_service(request)
    templates = _get_templates(request)

    try:
        view = svc.list_cases()
    except Exception as exc:
        safe_log_failure(
            logger,
            "ui.case_list_failed",
            error_code="UI_CASE_LIST_ERROR",
            exception=exc,
        )
        return _render_error(
            request, 500, "Interner Fehler", "Der Vorgang konnte nicht abgeschlossen werden."
        )

    return HTMLResponse(
        content=templates.get_template("cases/list.html").render(
            {"request": request, "base": _base_context("Fälle"), "view": view}
        ),
        headers={"Cache-Control": "no-store, max-age=0"},
    )


# ---------------------------------------------------------------------------
# Route: GET /ui/cases/{case_id}
# ---------------------------------------------------------------------------


@router.get("/cases/{case_id}")
async def ui_case_detail(request: Request) -> HTMLResponse:
    """Render the case detail page with document list."""
    svc = _get_workspace_service(request)
    templates = _get_templates(request)

    case_id_str = request.path_params.get("case_id", "")

    try:
        case_id = uuid.UUID(case_id_str)
    except (ValueError, AttributeError):
        return _render_error(
            request, 404, "Nicht gefunden", "Der angeforderte Fall wurde nicht gefunden."
        )

    try:
        view = svc.get_case(case_id)
    except Exception as exc:
        safe_log_failure(
            logger,
            "ui.case_detail_failed",
            error_code="UI_CASE_DETAIL_ERROR",
            exception=exc,
        )
        return _render_error(
            request, 500, "Interner Fehler", "Der Vorgang konnte nicht abgeschlossen werden."
        )

    if view is None:
        return _render_error(
            request, 404, "Nicht gefunden", "Der angeforderte Fall wurde nicht gefunden."
        )

    return HTMLResponse(
        content=templates.get_template("cases/detail.html").render(
            {"request": request, "base": _base_context(view.title), "view": view}
        ),
        headers={"Cache-Control": "no-store, max-age=0"},
    )


# ---------------------------------------------------------------------------
# Route: GET /ui/cases/{case_id}/documents/{document_id}
# ---------------------------------------------------------------------------


@router.get("/cases/{case_id}/documents/{document_id}")
async def ui_document_detail(request: Request) -> HTMLResponse:
    """Render the document detail / workspace page.

    Displays deadline candidates and document text preview.
    Reference event candidates are not yet displayed (M6-A placeholder).
    """
    svc = _get_workspace_service(request)
    templates = _get_templates(request)

    case_id_str = request.path_params.get("case_id", "")
    doc_id_str = request.path_params.get("document_id", "")

    try:
        case_id = uuid.UUID(case_id_str)
        document_id = uuid.UUID(doc_id_str)
    except (ValueError, AttributeError):
        return _render_error(
            request, 404, "Nicht gefunden", "Das angeforderte Dokument wurde nicht gefunden."
        )

    try:
        view = svc.get_document_workspace(case_id, document_id)
    except Exception as exc:
        safe_log_failure(
            logger,
            "ui.document_workspace_failed",
            error_code="UI_DOCUMENT_WORKSPACE_ERROR",
            exception=exc,
        )
        return _render_error(
            request, 500, "Interner Fehler", "Der Vorgang konnte nicht abgeschlossen werden."
        )

    if view is None:
        return _render_error(
            request, 404, "Nicht gefunden", "Das angeforderte Dokument wurde nicht gefunden."
        )

    return HTMLResponse(
        content=templates.get_template("documents/detail.html").render(
            {
                "request": request,
                "base": _base_context(view.document_filename),
                "view": view,
            }
        ),
        headers={"Cache-Control": "no-store, max-age=0"},
    )


# ---------------------------------------------------------------------------
# Helpers for CSRF cookie management
# ---------------------------------------------------------------------------


def _safe_form_str(form: dict[str, str], key: str, default: str = "") -> str:
    """Safely extract a string value from form data."""
    val = form.get(key, default)
    if isinstance(val, str):
        return val.strip()
    return default


def _set_csrf_cookie(response: Response, request: Request) -> None:
    """Set the CSRF browser nonce cookie on a GET response.

    Only sets if no cookie exists or if the service generates a new nonce.
    """
    existing = request.cookies.get("pln_csrf_nonce", "")
    if existing:
        return  # Don't rotate — would break other tabs

    csrf_service = request.app.state.csrf_service
    nonce = csrf_service.generate_browser_nonce()

    # Secure=False for local HTTP; document in code comment
    response.set_cookie(
        key="pln_csrf_nonce",
        value=nonce,
        httponly=True,
        samesite="strict",
        path="/ui",
        secure=False,  # Local HTTP — no TLS
    )


# ---------------------------------------------------------------------------
# Route: GET /ui/cases/{case_id}/documents/{document_id}/candidates/{candidate_index}
# ---------------------------------------------------------------------------


@router.get("/cases/{case_id}/documents/{document_id}/candidates/{candidate_index}")
async def ui_candidate_detail(request: Request) -> HTMLResponse:
    """Render the candidate detail page with confirmation history and forms."""
    svc = _get_workspace_service(request)
    templates = _get_templates(request)

    case_id_str = request.path_params.get("case_id", "")
    doc_id_str = request.path_params.get("document_id", "")
    cand_idx_str = request.path_params.get("candidate_index", "0")

    try:
        case_id = uuid.UUID(case_id_str)
        document_id = uuid.UUID(doc_id_str)
        candidate_index = int(cand_idx_str)
    except (ValueError, AttributeError):
        return _render_error(
            request,
            404,
            "Nicht gefunden",
            "Die angeforderte Seite wurde nicht gefunden.",
        )

    try:
        view = svc.get_candidate_detail(
            case_id,
            document_id,
            candidate_index,
            action_path=str(request.url.path),
        )
    except Exception as exc:
        safe_log_failure(
            logger,
            "ui.candidate_detail_failed",
            error_code="UI_CANDIDATE_DETAIL_ERROR",
            exception=exc,
        )
        return _render_error(
            request,
            500,
            "Interner Fehler",
            "Der Vorgang konnte nicht abgeschlossen werden.",
        )

    if view is None:
        return _render_error(
            request,
            404,
            "Nicht gefunden",
            "Die angeforderte Zeitangabe wurde nicht gefunden.",
        )

    response = HTMLResponse(
        content=templates.get_template("candidates/detail.html").render(
            {
                "request": request,
                "base": _base_context("Bezugsdatum prüfen"),
                "view": view,
            }
        ),
        headers={"Cache-Control": "no-store, max-age=0"},
    )
    _set_csrf_cookie(response, request)
    return response


# ---------------------------------------------------------------------------
# Route: POST /ui/cases/{case_id}/documents/{document_id}/candidates/{candidate_index}/confirm
# ---------------------------------------------------------------------------


@router.post(
    "/cases/{case_id}/documents/{document_id}/candidates/{candidate_index}/confirm",
    dependencies=[Depends(ui_post_security)],
    response_model=None,
)
async def ui_confirm_candidate(request: Request) -> RedirectResponse | HTMLResponse:
    """Confirm a detected reference event candidate (POST, CSRF, Idempotent, PRG)."""
    svc = _get_workspace_service(request)

    case_id_str = request.path_params.get("case_id", "")
    doc_id_str = request.path_params.get("document_id", "")
    cand_idx_str = request.path_params.get("candidate_index", "0")

    try:
        case_id = uuid.UUID(case_id_str)
        document_id = uuid.UUID(doc_id_str)
        candidate_index = int(cand_idx_str)
    except (ValueError, AttributeError):
        return _render_error(
            request,
            400,
            "Ungültige Anfrage",
            "Die angegebenen IDs sind ungültig.",
        )

    # Read form data
    try:
        form = await request.form()
    except Exception:
        return _render_error(
            request,
            400,
            "Ungültiges Formular",
            "Das Formular konnte nicht verarbeitet werden.",
        )

    idempotency_key = form.get("idempotency_key", "")
    if isinstance(idempotency_key, str):
        idempotency_key = idempotency_key.strip()

    confirmed_date_str = form.get("confirmed_date", "")
    if isinstance(confirmed_date_str, str):
        confirmed_date_str = confirmed_date_str.strip()

    event_type_str = _safe_form_str(form, "event_type", "unknown")  # type: ignore[arg-type]

    if not idempotency_key:
        return _render_error(
            request,
            400,
            "Ungültiges Formular",
            "Der Sicherheitsschlüssel fehlt.",
        )

    # Parse and validate date
    try:
        confirmed_date = date_type.fromisoformat(str(confirmed_date_str))  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return _render_error(
            request,
            400,
            "Ungültiges Datum",
            "Bitte geben Sie ein gültiges Datum im Format JJJJ-MM-TT ein.",
        )

    if confirmed_date < MIN_DATE or confirmed_date > MAX_DATE:
        return _render_error(
            request,
            400,
            "Datum außerhalb des Bereichs",
            f"Das Datum muss zwischen {MIN_DATE.isoformat()} und {MAX_DATE.isoformat()} liegen.",
        )

    # Parse event type
    try:
        event_type = EventType(event_type_str)  # type: ignore[arg-type]
    except ValueError:
        event_type = EventType.UNKNOWN

    redirect_path = str(
        request.url_for(
            "ui_candidate_detail",
            case_id=case_id_str,
            document_id=doc_id_str,
            candidate_index=cand_idx_str,
        )
    )

    try:
        _ = svc.confirm_candidate(
            idempotency_key=idempotency_key,  # type: ignore[arg-type]
            case_id=case_id,
            document_id=document_id,
            candidate_index=candidate_index,
            event_type=event_type,
            confirmed_date=confirmed_date,
            redirect_path=redirect_path,
        )
    except IdempotencyKeyConflictError:
        return _render_error(
            request,
            409,
            "Bereits verarbeitet",
            "Diese Aktion wurde bereits ausgeführt. Bitte laden Sie die Seite neu.",
        )
    except ValueError as exc:
        return _render_error(
            request,
            404,
            "Nicht gefunden",
            str(exc),
        )
    except Exception as exc:
        safe_log_failure(
            logger,
            "ui.confirm_candidate_failed",
            error_code="UI_CONFIRM_FAILED",
            exception=exc,
        )
        return _render_error(
            request,
            500,
            "Interner Fehler",
            "Der Vorgang konnte nicht abgeschlossen werden.",
        )

    # Safe audit event — no IDs, dates, or user data
    safe_log_event(logger, "ui.reference_event.confirm_requested")

    # PRG: 303 redirect to candidate detail with success flag
    redirect_url = f"{redirect_path}?confirmed=1"
    return RedirectResponse(url=redirect_url, status_code=303)


# ---------------------------------------------------------------------------
# Route: POST .../candidates/{candidate_index}/reject
# ---------------------------------------------------------------------------


@router.post(
    "/cases/{case_id}/documents/{document_id}/candidates/{candidate_index}/reject",
    dependencies=[Depends(ui_post_security)],
    response_model=None,
)
async def ui_reject_candidate(request: Request) -> RedirectResponse | HTMLResponse:
    """Reject a detected reference event candidate (POST, CSRF, Idempotent, PRG)."""
    svc = _get_workspace_service(request)

    case_id_str = request.path_params.get("case_id", "")
    doc_id_str = request.path_params.get("document_id", "")
    cand_idx_str = request.path_params.get("candidate_index", "0")

    try:
        case_id = uuid.UUID(case_id_str)
        document_id = uuid.UUID(doc_id_str)
        candidate_index = int(cand_idx_str)
    except (ValueError, AttributeError):
        return _render_error(
            request,
            400,
            "Ungültige Anfrage",
            "Die angegebenen IDs sind ungültig.",
        )

    try:
        form = await request.form()
    except Exception:
        return _render_error(
            request,
            400,
            "Ungültiges Formular",
            "Das Formular konnte nicht verarbeitet werden.",
        )

    idempotency_key = form.get("idempotency_key", "")
    if isinstance(idempotency_key, str):
        idempotency_key = idempotency_key.strip()

    event_type_str = form.get("event_type", "unknown")
    if isinstance(event_type_str, str):
        event_type_str = event_type_str.strip()

    if not idempotency_key:
        return _render_error(
            request,
            400,
            "Ungültiges Formular",
            "Der Sicherheitsschlüssel fehlt.",
        )

    try:
        event_type = EventType(event_type_str)
    except ValueError:
        event_type = EventType.UNKNOWN

    redirect_path = str(
        request.url_for(
            "ui_candidate_detail",
            case_id=case_id_str,
            document_id=doc_id_str,
            candidate_index=cand_idx_str,
        )
    )

    try:
        svc.reject_candidate(
            idempotency_key=idempotency_key,
            case_id=case_id,
            document_id=document_id,
            candidate_index=candidate_index,
            event_type=event_type,
            redirect_path=redirect_path,
        )
    except IdempotencyKeyConflictError:
        return _render_error(
            request,
            409,
            "Bereits verarbeitet",
            "Diese Aktion wurde bereits ausgeführt. Bitte laden Sie die Seite neu.",
        )
    except ValueError as exc:
        return _render_error(request, 404, "Nicht gefunden", str(exc))
    except Exception as exc:
        safe_log_failure(
            logger,
            "ui.reject_candidate_failed",
            error_code="UI_REJECT_FAILED",
            exception=exc,
        )
        return _render_error(
            request,
            500,
            "Interner Fehler",
            "Der Vorgang konnte nicht abgeschlossen werden.",
        )

    safe_log_event(logger, "ui.reference_event.reject_requested")

    redirect_url = f"{redirect_path}?rejected=1"
    return RedirectResponse(url=redirect_url, status_code=303)


# ---------------------------------------------------------------------------
# Route: POST .../candidates/{candidate_index}/manual-confirm
# ---------------------------------------------------------------------------


@router.post(
    "/cases/{case_id}/documents/{document_id}/candidates/{candidate_index}/manual-confirm",
    dependencies=[Depends(ui_post_security)],
    response_model=None,
)
async def ui_manual_confirm(request: Request) -> RedirectResponse | HTMLResponse:
    """Manually confirm a reference date (POST, CSRF, Idempotent, PRG)."""
    svc = _get_workspace_service(request)

    case_id_str = request.path_params.get("case_id", "")
    doc_id_str = request.path_params.get("document_id", "")
    cand_idx_str = request.path_params.get("candidate_index", "0")

    try:
        case_id = uuid.UUID(case_id_str)
        document_id = uuid.UUID(doc_id_str)
        candidate_index = int(cand_idx_str)
    except (ValueError, AttributeError):
        return _render_error(
            request,
            400,
            "Ungültige Anfrage",
            "Die angegebenen IDs sind ungültig.",
        )

    try:
        form = await request.form()
    except Exception:
        return _render_error(
            request,
            400,
            "Ungültiges Formular",
            "Das Formular konnte nicht verarbeitet werden.",
        )

    idempotency_key = form.get("idempotency_key", "")
    if isinstance(idempotency_key, str):
        idempotency_key = idempotency_key.strip()

    manual_date_str = form.get("manual_date", "")
    if isinstance(manual_date_str, str):
        manual_date_str = manual_date_str.strip()

    event_type_str = form.get("event_type", "unknown")
    if isinstance(event_type_str, str):
        event_type_str = event_type_str.strip()

    evidence_note = form.get("evidence_note", "")
    if isinstance(evidence_note, str):
        evidence_note = evidence_note.strip()

    if not idempotency_key:
        return _render_error(
            request,
            400,
            "Ungültiges Formular",
            "Der Sicherheitsschlüssel fehlt.",
        )

    # Parse and validate date
    try:
        manual_date = date_type.fromisoformat(manual_date_str)
    except (ValueError, TypeError):
        return _render_error(
            request,
            400,
            "Ungültiges Datum",
            "Bitte geben Sie ein gültiges Datum im Format JJJJ-MM-TT ein.",
        )

    if manual_date < MIN_DATE or manual_date > MAX_DATE:
        return _render_error(
            request,
            400,
            "Datum außerhalb des Bereichs",
            f"Das Datum muss zwischen {MIN_DATE.isoformat()} und {MAX_DATE.isoformat()} liegen.",
        )

    try:
        event_type = EventType(event_type_str)
    except ValueError:
        event_type = EventType.UNKNOWN

    redirect_path = str(
        request.url_for(
            "ui_candidate_detail",
            case_id=case_id_str,
            document_id=doc_id_str,
            candidate_index=cand_idx_str,
        )
    )

    try:
        svc.manual_confirm_date(
            idempotency_key=idempotency_key,
            case_id=case_id,
            document_id=document_id,
            candidate_index=candidate_index,
            event_type=event_type,
            confirmed_date=manual_date,
            redirect_path=redirect_path,
            evidence_note=evidence_note,
        )
    except IdempotencyKeyConflictError:
        return _render_error(
            request,
            409,
            "Bereits verarbeitet",
            "Diese Aktion wurde bereits ausgeführt. Bitte laden Sie die Seite neu.",
        )
    except ValueError as exc:
        return _render_error(request, 404, "Nicht gefunden", str(exc))
    except Exception as exc:
        safe_log_failure(
            logger,
            "ui.manual_confirm_failed",
            error_code="UI_MANUAL_CONFIRM_FAILED",
            exception=exc,
        )
        return _render_error(
            request,
            500,
            "Interner Fehler",
            "Der Vorgang konnte nicht abgeschlossen werden.",
        )

    safe_log_event(logger, "ui.reference_event.manual_entry_requested")

    redirect_url = f"{redirect_path}?confirmed=1"
    return RedirectResponse(url=redirect_url, status_code=303)
