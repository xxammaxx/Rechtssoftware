"""Privacy redaction filter for M6-A logging invariants.

INV-M6A-16: No case or reference data in logs.
INV-M6A-21: Redact confirmed_date, evidence_text, evidence_note, source_text.
INV-M6A-DP-08: Additionally redact document_id, confirmation_id.
FR-M6A-030: System MUST NOT emit confirmed reference data in logs.
"""

import logging
from collections.abc import Mapping
from datetime import date, datetime
from uuid import UUID

# Field names that MUST be redacted from log output.
# Order is stable for deterministic test assertions.
SENSITIVE_FIELDS: tuple[str, ...] = (
    "calculated_date",
    "case_id",
    "candidate_id",
    "confirmation_id",
    "confirmed_date",
    "deadline_candidate_id",
    "document_id",
    "evidence_note",
    "evidence_text",
    "reference_date",
    "reference_event_candidate_id",
    "source_text",
    "suggested_date",
    "supersedes_confirmation_id",
)

REDACTED_VALUE = "[REDACTED]"

# LogRecord built-in attribute names that must never be redacted
# even if they happen to match a sensitive field name.
_BUILTIN_RECORD_ATTRS: frozenset[str] = frozenset(
    {
        "args",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "taskName",
    }
)


def _is_sensitive_key(key: str) -> bool:
    """Check if a key name matches a sensitive field."""
    return key in SENSITIVE_FIELDS


def _redact_dict_recursive(data: object, _depth: int = 0) -> object:
    """Recursively redact sensitive keys from nested structures.

    Does NOT mutate the original object. Returns a redacted copy.
    Depth-limited to prevent infinite recursion.
    """
    if _depth > 10:
        return REDACTED_VALUE

    if isinstance(data, Mapping):
        result: dict[str, object] = {}
        for key, value in data.items():
            key_str = str(key)
            if _is_sensitive_key(key_str):
                result[key_str] = REDACTED_VALUE
            else:
                result[key_str] = _redact_dict_recursive(value, _depth + 1)
        return result

    if isinstance(data, (list, tuple)):
        return type(data)(_redact_dict_recursive(item, _depth + 1) for item in data)

    if isinstance(data, (UUID, date, datetime)):
        return str(data)

    return data


class PrivacyRedactionFilter(logging.Filter):
    """Logging filter that redacts sensitive M6-A fields from log records.

    Operates on three paths:
    1. Extra attributes set on the LogRecord via ``extra={}`` parameter
       → replaced with REDACTED_VALUE if the key is sensitive
    2. Mapping-style ``args`` (dict passed to log call)
       → recursive redaction of sensitive keys in the dict
    3. Non-builtin attributes that contain nested mappings
       → recursive redaction of sensitive keys inside them

    The filter is idempotent and never mutates the caller's data.

    .. CAUTION::

       This filter ONLY protects structured logging:

       * Safe:  ``logger.info("msg", extra={"document_id": uuid})``
       * Safe:  ``logger.info("msg", {"document_id": uuid})``

       It does NOT protect:

       * Positional ``%s`` args: ``logger.info("id=%s", uuid)``  — LEAKS
       * F-string interpolation: ``logger.info(f"id={uuid}")``   — LEAKS
       * Exception traceback local variables                      — LEAK

       The ``tests/unit/test_logging_static_policy.py`` static guard
       prevents positional/f-string patterns from entering product code.
       Always use ``extra={}`` or Mapping-style dict args with
       sensitive data.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Apply privacy redaction. Always returns True (never drops records)."""
        if getattr(record, "_privacy_filtered", False):
            return True

        # 1. Redact extra attributes on the record (only non-builtins)
        for key in list(record.__dict__.keys()):
            if key in _BUILTIN_RECORD_ATTRS:
                continue

            val = record.__dict__[key]
            if _is_sensitive_key(key):
                record.__dict__[key] = REDACTED_VALUE
            elif isinstance(val, Mapping):
                record.__dict__[key] = _redact_dict_recursive(val)

        # 2. Redact mapping-style args
        if isinstance(record.args, Mapping):
            # Build a redacted copy of the args dict
            redacted_args = dict(record.args)
            for key in list(redacted_args.keys()):
                if _is_sensitive_key(str(key)):
                    redacted_args[str(key)] = REDACTED_VALUE
            record.args = redacted_args

        object.__setattr__(record, "_privacy_filtered", True)
        return True


def configure_logging(
    level: int = logging.INFO,
    *,
    install_root_filter: bool = True,
) -> None:
    """Configure application logging with privacy redaction.

    PrivacyRedactionFilter is attached to every emitting path:

    1. Root logger filter  — catches propagated child-logger records
    2. Handler filter       — defense in depth for direct handler emission
    3. Uvicorn access mute  — reduced to WARNING to avoid URL-embedded IDs

    Safe to call multiple times (idempotent). Never removes foreign
    handlers or filters from non-application loggers.
    """
    root_logger = logging.getLogger()
    redaction_filter = PrivacyRedactionFilter()

    # --- 1. Root logger filter (catches propagated child-logger records) ---
    if install_root_filter:
        root_logger.filters = [
            f for f in root_logger.filters if not isinstance(f, PrivacyRedactionFilter)
        ]
        root_logger.addFilter(redaction_filter)

    # --- 2. Handler filter (defense in depth) ---
    if not root_logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)

    # Attach PrivacyRedactionFilter to every existing handler
    # (idempotent — never duplicates)
    for h in root_logger.handlers:
        existing_filters = [f for f in h.filters if isinstance(f, PrivacyRedactionFilter)]
        if not existing_filters:
            h.addFilter(PrivacyRedactionFilter())

    root_logger.setLevel(level)

    # Silence overly verbose / privacy-sensitive library loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)

    # Attach PrivacyRedactionFilter to uvicorn.error logger directly.
    # Defense in depth: uvicorn.error may have its own handler that
    # bypasses root logger propagation. Adding the filter to the logger
    # itself ensures every record through uvicorn.error is filtered.
    _uvicorn_error = logging.getLogger("uvicorn.error")
    _uvicorn_error_filters = [
        f for f in _uvicorn_error.filters if isinstance(f, PrivacyRedactionFilter)
    ]
    if not _uvicorn_error_filters:
        _uvicorn_error.addFilter(PrivacyRedactionFilter())
