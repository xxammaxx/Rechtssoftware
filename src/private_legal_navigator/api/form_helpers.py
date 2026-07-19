"""Typed form-data extractors for M6-UI POST routes.

Provides runtime-checked extraction of string values from Starlette
FormData, which may contain UploadFile instances. Every extractor
performs an explicit isinstance(str, ...) check and enforces field
length limits.

UploadFile values are rejected with a controlled 400 error.
"""

from __future__ import annotations

from typing import Final

from fastapi import HTTPException
from starlette.datastructures import FormData

# Reasonable per-field limit for user-supplied strings (2 KB).
# Evidence notes use a larger limit of 2000 chars, so we allow
# slightly more for multi-byte/future expansion.
DEFAULT_MAX_FIELD_LENGTH: Final[int] = 4096

# The evidence_note field may contain a longer description.
MAX_EVIDENCE_NOTE_LENGTH: Final[int] = 2000

# Idempotency keys are hex tokens (32 hex chars = 16 bytes).
MAX_IDEMPOTENCY_KEY_LENGTH: Final[int] = 128

# Manual date is ISO format: "YYYY-MM-DD" (10 chars).
MAX_DATE_FIELD_LENGTH: Final[int] = 32

# CSRF token is a long signed string.
MAX_CSRF_TOKEN_LENGTH: Final[int] = 1024


class InvalidFormField(HTTPException):
    """A form field contained an unexpected type or exceeded length."""

    def __init__(self, field_name: str) -> None:
        super().__init__(
            status_code=400,
            detail=f"Ungültiger Wert im Feld '{field_name}'.",
        )


class MissingFormField(HTTPException):
    """A required form field was missing."""

    def __init__(self, field_name: str) -> None:
        super().__init__(
            status_code=400,
            detail=f"Das Feld '{field_name}' fehlt.",
        )


class DuplicateFormField(HTTPException):
    """A form field was submitted more than once (not supported)."""

    def __init__(self, field_name: str) -> None:
        super().__init__(
            status_code=400,
            detail=f"Das Feld '{field_name}' wurde mehrfach übermittelt.",
        )


def _check_single_value(form: FormData, field_name: str) -> None:
    """Verify the field appears at most once in the form.

    FormData.getlist returns all values for a key. If more than one,
    we reject to avoid ambiguous semantics.
    """
    values = form.getlist(field_name)
    if len(values) > 1:
        raise DuplicateFormField(field_name)


def require_form_string(
    form: FormData,
    field_name: str,
    *,
    max_length: int = DEFAULT_MAX_FIELD_LENGTH,
) -> str:
    """Extract a required string value from multipart/form-urlencoded data.

    Args:
        form: The parsed FormData from ``request.form()``.
        field_name: The name of the form field.
        max_length: Maximum allowed length (default: 4096).

    Returns:
        The trimmed string value.

    Raises:
        InvalidFormField: If the value is not a string or exceeds max_length.
        MissingFormField: If the field is absent or empty after stripping.
    """
    _check_single_value(form, field_name)

    value = form.get(field_name)

    if value is None:
        raise MissingFormField(field_name)

    if not isinstance(value, str):
        raise InvalidFormField(field_name)

    trimmed = value.strip()

    if not trimmed:
        raise MissingFormField(field_name)

    if len(trimmed) > max_length:
        raise InvalidFormField(field_name)

    return trimmed


def optional_form_string(
    form: FormData,
    field_name: str,
    *,
    max_length: int = DEFAULT_MAX_FIELD_LENGTH,
) -> str | None:
    """Extract an optional string value from multipart/form-urlencoded data.

    Args:
        form: The parsed FormData from ``request.form()``.
        field_name: The name of the form field.
        max_length: Maximum allowed length (default: 4096).

    Returns:
        The trimmed string value, or None if the field is absent or empty.

    Raises:
        InvalidFormField: If the value is not a string or exceeds max_length.
    """
    _check_single_value(form, field_name)

    value = form.get(field_name)

    if value is None:
        return None

    if not isinstance(value, str):
        raise InvalidFormField(field_name)

    trimmed = value.strip()

    if not trimmed:
        return None

    if len(trimmed) > max_length:
        raise InvalidFormField(field_name)

    return trimmed
