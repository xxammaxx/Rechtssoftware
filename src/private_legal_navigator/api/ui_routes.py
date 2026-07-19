"""M6-UI read-only HTML routes.

All routes use the Application Layer orchestrator and produce
server-rendered HTML via Jinja2 templates. No direct repository access.
"""

import logging
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.templating import Jinja2Templates

from private_legal_navigator.application.local_confirmation_workspace_service import (
    LocalConfirmationWorkspaceService,
)
from private_legal_navigator.application.ui_view_models import (
    BaseContext,
    ErrorView,
)
from private_legal_navigator.infrastructure.safe_logging import safe_log_failure

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
