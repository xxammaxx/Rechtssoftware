"""Safe-Logging-API: the ONLY logging interface for product code.

INV-M6A-16, INV-M6A-21, INV-M6A-DP-08, FR-M6A-030:
Product code MUST NOT call standard logging methods directly.
All log emissions go through safe_log_event() and safe_log_failure().

Design:
  - Event names are string literals or enum values (never f-strings)
  - Structured fields are passed via extra={} — redacted by PrivacyRedactionFilter
  - Exception messages are NEVER logged
  - Raw tracebacks are NEVER logged
  - No positional %s, .format(), f-strings, or string concatenation
"""

from __future__ import annotations

import logging
from typing import Any


def safe_log_event(
    logger: logging.Logger,
    event_name: str,
    **fields: Any,
) -> None:
    """Emit a structured product log event.

    All fields are passed as extra attributes and are subject to
    PrivacyRedactionFilter redaction.

    Args:
        logger: The logger instance to use.
        event_name: Static event name (string literal or safe enum value).
            Never an f-string or variable from user input.
        **fields: Structured fields (must be keyword arguments, never
            positional). Sensitive field names are redacted by the filter.

    Example:
        safe_log_event(
            logger,
            "reference_event.confirmed",
            document_id=document_id,
            confirmation_id=confirmation_id,
            result_status="success",
        )
    """
    logger.info(event_name, extra=dict(fields))


def safe_log_failure(
    logger: logging.Logger,
    event_name: str,
    error_code: str,
    exception: Exception | None = None,
    **fields: Any,
) -> None:
    """Log a failure WITHOUT the exception message or traceback.

    Uses logger.error (NOT logger.exception) to prevent traceback emission.
    Only the exception type name is logged, never the message content.

    Args:
        logger: The logger instance to use.
        event_name: Static event name (string literal or safe enum value).
        error_code: Stable error code (string literal, e.g. "INTERNAL_ERROR").
        exception: The caught exception (only type name is extracted).
        **fields: Structured fields (keyword-only, redacted by filter).

    Example:
        try:
            ...
        except ValueError as exc:
            safe_log_failure(
                logger,
                "reference_event.failed",
                error_code="INVALID_CONFIRMATION_CONTEXT",
                exception=exc,
            )
    """
    extra: dict[str, Any] = {
        "error_code": error_code,
        "result_status": "failure",
    }
    if exception is not None:
        extra["exception_type"] = type(exception).__name__
    extra.update(fields)

    # Use error(), NOT exception() — exception() emits exc_info traceback
    logger.error(event_name, extra=extra)
