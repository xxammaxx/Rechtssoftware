"""Error handling for the FastAPI application."""

from fastapi import Request
from fastapi.responses import JSONResponse


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
