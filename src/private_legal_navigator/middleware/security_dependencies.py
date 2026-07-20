"""Security dependencies for M6-UI POST routes.

Provides CSRF validation, Origin/Referer checking, content-type enforcement,
and body size limits as FastAPI dependencies (not global middleware).
"""

import logging
import re
from typing import Annotated

from fastapi import Depends, HTTPException, Request

from private_legal_navigator.infrastructure.safe_logging import safe_log_failure
from private_legal_navigator.middleware.csrf import CsrfTokenService

logger = logging.getLogger("private_legal_navigator.ui")

MAX_BODY_BYTES = 65_536  # 64 KB limit for form submissions
ALLOWED_CONTENT_TYPE = "application/x-www-form-urlencoded"

# M6-UI Slice 2 action suffixes that extend the candidate page path.
# CSRF tokens are bound to the page path (/candidates/{idx}) and
# validated by stripping these known action suffixes from the POST path.
_ACTION_SUFFIX_PATTERN = re.compile(r"/(confirm|reject|manual-confirm|correct|revoke)$")


async def require_form_content_type(request: Request) -> None:
    """Enforce application/x-www-form-urlencoded Content-Type on POST."""
    if request.method != "POST":
        return

    content_type = request.headers.get("content-type", "")
    if ALLOWED_CONTENT_TYPE not in content_type:
        raise HTTPException(
            status_code=415,
            detail="Nicht unterstütztes Medienformat.",
        )


async def require_body_size_limit(request: Request) -> None:
    """Reject POST requests with body exceeding MAX_BODY_BYTES."""
    if request.method != "POST":
        return

    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_BODY_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Die Anfragedaten sind zu groß.",
        )


async def require_origin_or_referer(request: Request) -> None:
    """Validate Origin or Referer header for state-changing requests.

    For local single-user operation: accepts same-origin, localhost,
    and 127.0.0.1 origins. Rejects if neither header is present.
    """
    if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
        return

    origin = request.headers.get("origin", "")
    referer = request.headers.get("referer", "")

    if origin:
        if not _is_same_origin(origin, request):
            raise HTTPException(status_code=403, detail="Ungültige Anfrageherkunft.")
    elif referer:
        if not _is_same_origin(referer, request):
            raise HTTPException(status_code=403, detail="Ungültige Anfrageherkunft.")
    else:
        raise HTTPException(
            status_code=403,
            detail="Die Anfrage konnte nicht verarbeitet werden.",
        )


def _is_same_origin(header_value: str, request: Request) -> bool:
    """Check if a URL from a header matches the request's origin."""
    base = str(request.base_url).rstrip("/")
    return header_value.startswith(base)


async def require_csrf_token(request: Request) -> None:
    """Validate CSRF token from form against browser nonce cookie.

    M6-UI Slice 2: CSRF tokens are bound to the candidate detail page
    path (e.g. ``/ui/cases/{id}/documents/{id}/candidates/{idx}``).
    POST actions add a suffix (``/confirm``, ``/reject``,
    ``/manual-confirm``).  We strip the suffix before validation so
    one page token covers all three forms.
    """
    if request.method != "POST":
        return

    csrf_service: CsrfTokenService | None = getattr(request.app.state, "csrf_service", None)
    if csrf_service is None:
        safe_log_failure(
            logger,
            "ui.csrf_service_missing",
            error_code="CSRF_SERVICE_MISSING",
        )
        raise HTTPException(
            status_code=500,
            detail="Der Vorgang konnte nicht abgeschlossen werden.",
        )

    try:
        form = await request.form()
    except Exception as exc:
        safe_log_failure(
            logger,
            "ui.csrf_form_read_failed",
            error_code="CSRF_FORM_READ_ERROR",
            exception=exc,
        )
        raise HTTPException(status_code=400, detail="Ungültiges Formular.") from exc

    # Use FormData typing to help mypy distinguish strings from UploadFile
    raw_token = form.get("csrf_token", "")
    csrf_token: str = raw_token.strip() if isinstance(raw_token, str) else ""

    browser_nonce = request.cookies.get("pln_csrf_nonce", "")

    if not csrf_token or not browser_nonce:
        raise HTTPException(status_code=403, detail="Fehlende Sicherheitsdaten.")

    # Strip action suffix so the token matches the page path.
    raw_path = request.url.path
    action_path = _ACTION_SUFFIX_PATTERN.sub("", raw_path)

    if not csrf_service.validate_token(csrf_token, browser_nonce, action_path):
        raise HTTPException(
            status_code=403,
            detail="Die Anfrage konnte nicht verarbeitet werden.",
        )


# ── Combined dependency for all POST routes ──


async def ui_post_security(
    _content_type: Annotated[None, Depends(require_form_content_type)],
    _body_size: Annotated[None, Depends(require_body_size_limit)],
    _origin: Annotated[None, Depends(require_origin_or_referer)],
    _csrf: Annotated[None, Depends(require_csrf_token)],
) -> None:
    """Aggregate all POST security checks in one dependency."""
    pass
