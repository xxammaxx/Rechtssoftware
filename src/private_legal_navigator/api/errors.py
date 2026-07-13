"""Error handling for the FastAPI application."""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handler for RequestValidationError — returns the documented 422 error format.

    Intentionally returns a generic message without exposing input values,
    request bodies, stacktraces, or local paths.
    """
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Die Eingabedaten sind ungültig.",
            }
        },
    )


def case_not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handler for CaseNotFoundError."""
    return JSONResponse(
        status_code=404,
        content={
            "error": {
                "code": "CASE_NOT_FOUND",
                "message": "Der angeforderte Fall wurde nicht gefunden.",
            }
        },
    )


class CaseNotFoundError(Exception):
    """Raised when a case is not found."""


class DocumentNotFoundError(Exception):
    """Raised when a document is not found."""
