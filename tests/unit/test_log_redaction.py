"""Unit tests for PrivacyRedactionFilter — STAGE 2 Red Tests.

These tests validate that the logging redaction filter correctly redacts
all mandatory sensitive fields per INV-M6A-16, INV-M6A-21, INV-M6A-DP-08,
and FR-M6A-030.
"""

import logging
from collections.abc import Mapping
from datetime import date
from uuid import UUID, uuid4

import pytest

from private_legal_navigator.infrastructure.log_redaction import (
    REDACTED_VALUE,
    SENSITIVE_FIELDS,
    PrivacyRedactionFilter,
    _redact_dict_recursive,
    configure_logging,
)

# ── Synthetic test markers (must never appear in plaintext logs) ──────────

SYNTHETIC_UUID = UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
SYNTHETIC_DATE = date(2026, 7, 15)
SYNTHETIC_EVIDENCE = "SYNTHETIC_EVIDENCE_SECRET_4711"
SYNTHETIC_NOTE = "SYNTHETIC_NOTE_DO_NOT_LOG_9182"
SYNTHETIC_SOURCE = "SYNTHETIC_SOURCE_DO_NOT_LOG_7331"

_BUILTIN_ATTRS = frozenset({
    "args", "created", "exc_info", "exc_text", "filename",
    "funcName", "levelname", "levelno", "lineno", "module",
    "msecs", "msg", "name", "pathname", "process",
    "processName", "relativeCreated", "stack_info", "thread",
    "threadName", "taskName",
})


# ── Helpers ────────────────────────────────────────────────────────────────

def _emit_and_capture(
    logger: logging.Logger,
    level: int,
    msg: str,
    *args: object,
    extra: dict[str, object] | None = None,
) -> str:
    """Emit a log record through the filter and return formatted output.

    Args:
        logger: Logger to create the record on.
        level: Log level.
        msg: Log message template.
        *args: Positional args for the log message (will be record.args).
        extra: Dict of extra attributes to set on the LogRecord.
    """
    record = logger.makeRecord(
        logger.name, level, "", 0, msg, args, None, None, None,
    )
    if extra:
        for key, value in extra.items():
            record.__dict__[key] = value
    record._privacy_filtered = False
    filt = PrivacyRedactionFilter()
    filt.filter(record)

    parts = [str(record.msg)]
    if record.args and isinstance(record.args, Mapping):
        parts.append("; ".join(
            f"{k}={v}" for k, v in record.args.items()
        ))
    # Include all extra (non-builtin) attributes the filter might have set
    for attr in sorted(record.__dict__):
        if attr in _BUILTIN_ATTRS or attr.startswith("_"):
            continue
        parts.append(f"{attr}={record.__dict__[attr]}")
    return " | ".join(parts)


# ── LT-01: Filter exists and is wired ─────────────────────────────────────

class TestFilterExistsAndWired:
    """LT-01 — Filter exists and is actually attached to a logger."""

    def test_filter_can_be_instantiated(self):
        f = PrivacyRedactionFilter()
        assert isinstance(f, logging.Filter)

    def test_filter_attached_to_root_logger(self):
        root = logging.getLogger()
        root.filters.clear()
        root.handlers.clear()
        configure_logging()
        privacy_filters = [
            f for f in root.filters
            if isinstance(f, PrivacyRedactionFilter)
        ]
        assert len(privacy_filters) == 1


# ── LT-02: confirmed_date ─────────────────────────────────────────────────

class TestRedactConfirmedDate:
    """LT-02 — confirmed_date must not appear in plaintext."""

    def test_confirmed_date_in_extra(self):
        logger = logging.getLogger("test")
        output = _emit_and_capture(
            logger, logging.INFO, "event confirmed",
            extra={"confirmed_date": SYNTHETIC_DATE.isoformat()},
        )
        assert SYNTHETIC_DATE.isoformat() not in output
        assert REDACTED_VALUE in output

    def test_confirmed_date_in_mapping_args(self):
        logger = logging.getLogger("test")
        output = _emit_and_capture(
            logger, logging.INFO, "Confirmation processed",
            {"confirmed_date": SYNTHETIC_DATE.isoformat()},
        )
        assert SYNTHETIC_DATE.isoformat() not in output
        assert REDACTED_VALUE in output


# ── LT-03: calculated_date ────────────────────────────────────────────────

class TestRedactCalculatedDate:
    def test_calculated_date_in_extra(self):
        logger = logging.getLogger("test")
        output = _emit_and_capture(
            logger, logging.INFO, "preview generated",
            extra={"calculated_date": "2026-07-29"},
        )
        assert "2026-07-29" not in output


# ── LT-04: suggested_date ─────────────────────────────────────────────────

class TestRedactSuggestedDate:
    def test_suggested_date_in_extra(self):
        logger = logging.getLogger("test")
        output = _emit_and_capture(
            logger, logging.INFO, "candidate",
            extra={"suggested_date": "2026-06-01"},
        )
        assert "2026-06-01" not in output


# ── LT-05: evidence_text ──────────────────────────────────────────────────

class TestRedactEvidenceText:
    def test_evidence_text_in_extra(self):
        logger = logging.getLogger("test")
        output = _emit_and_capture(
            logger, logging.INFO, "confirm attempted",
            extra={"evidence_text": SYNTHETIC_EVIDENCE},
        )
        assert SYNTHETIC_EVIDENCE not in output


# ── LT-06: evidence_note ──────────────────────────────────────────────────

class TestRedactEvidenceNote:
    def test_evidence_note_in_extra(self):
        logger = logging.getLogger("test")
        output = _emit_and_capture(
            logger, logging.INFO, "manual entry",
            extra={"evidence_note": SYNTHETIC_NOTE},
        )
        assert SYNTHETIC_NOTE not in output


# ── LT-07: source_text ────────────────────────────────────────────────────

class TestRedactSourceText:
    def test_source_text_in_extra(self):
        logger = logging.getLogger("test")
        output = _emit_and_capture(
            logger, logging.INFO, "source",
            extra={"source_text": SYNTHETIC_SOURCE},
        )
        assert SYNTHETIC_SOURCE not in output


# ── LT-08: document_id ────────────────────────────────────────────────────

class TestRedactDocumentId:
    def test_document_id_in_extra(self):
        logger = logging.getLogger("test")
        output = _emit_and_capture(
            logger, logging.INFO, "stored",
            extra={"document_id": SYNTHETIC_UUID},
        )
        assert str(SYNTHETIC_UUID) not in output


# ── LT-09: confirmation_id ────────────────────────────────────────────────

class TestRedactConfirmationId:
    def test_confirmation_id_in_extra(self):
        logger = logging.getLogger("test")
        output = _emit_and_capture(
            logger, logging.INFO, "created",
            extra={"confirmation_id": SYNTHETIC_UUID},
        )
        assert str(SYNTHETIC_UUID) not in output


# ── LT-10: Mapping arguments ──────────────────────────────────────────────

class TestRedactMappingArgs:
    def test_multiple_sensitive_keys_in_mapping(self):
        logger = logging.getLogger("test")
        output = _emit_and_capture(
            logger, logging.INFO, "Confirmation",
            {"confirmation_id": str(SYNTHETIC_UUID),
             "confirmed_date": SYNTHETIC_DATE.isoformat()},
        )
        assert str(SYNTHETIC_UUID) not in output
        assert SYNTHETIC_DATE.isoformat() not in output


# ── LT-11: Extra fields ───────────────────────────────────────────────────

class TestRedactExtraFields:
    def test_sensitive_field_becomes_redacted(self):
        logger = logging.getLogger("test")
        output = _emit_and_capture(
            logger, logging.INFO, "test",
            extra={"document_id": SYNTHETIC_UUID,
                   "confirmed_date": "2026-01-01"},
        )
        assert str(SYNTHETIC_UUID) not in output
        assert "2026-01-01" not in output


# ── LT-12: Nested structures ──────────────────────────────────────────────

class TestRedactNestedStructures:
    def test_nested_dict(self):
        result = _redact_dict_recursive({
            "info": {
                "document_id": str(SYNTHETIC_UUID),
                "nested": {"confirmed_date": "2026-01-15"},
            }
        })
        assert result["info"]["document_id"] == REDACTED_VALUE  # type: ignore[index]
        assert result["info"]["nested"]["confirmed_date"] == REDACTED_VALUE  # type: ignore[index]

    def test_list_of_dicts(self):
        result = _redact_dict_recursive([
            {"document_id": str(SYNTHETIC_UUID)},
            {"confirmation_id": str(SYNTHETIC_UUID)},
        ])
        assert result[0]["document_id"] == REDACTED_VALUE  # type: ignore[index]
        assert result[1]["confirmation_id"] == REDACTED_VALUE  # type: ignore[index]


# ── LT-13: Exception path ─────────────────────────────────────────────────

class TestExceptionPath:
    def test_exception_does_not_leak_extra(self):
        logger = logging.getLogger("test")
        try:
            raise ValueError("bad data")
        except ValueError:
            output = _emit_and_capture(
                logger, logging.ERROR, "failure",
                extra={
                    "document_id": SYNTHETIC_UUID,
                    "confirmed_date": SYNTHETIC_DATE.isoformat(),
                },
            )
            assert str(SYNTHETIC_UUID) not in output
            assert SYNTHETIC_DATE.isoformat() not in output

    def test_no_extra_leak_in_exception(self):
        logger = logging.getLogger("test")
        output = _emit_and_capture(
            logger, logging.ERROR, "failure",
            extra={
                "document_id": SYNTHETIC_UUID,
                "confirmed_date": SYNTHETIC_DATE.isoformat(),
            },
        )
        assert str(SYNTHETIC_UUID) not in output
        assert SYNTHETIC_DATE.isoformat() not in output


# ── LT-14: Idempotency ────────────────────────────────────────────────────

class TestIdempotency:
    def test_configure_logging_idempotent(self):
        root = logging.getLogger()
        root.filters.clear()
        root.handlers.clear()

        configure_logging()
        first = len([f for f in root.filters
                     if isinstance(f, PrivacyRedactionFilter)])

        configure_logging()
        second = len([f for f in root.filters
                      if isinstance(f, PrivacyRedactionFilter)])

        assert first == 1
        assert second == 1

    def test_filter_idempotent_on_record(self):
        logger = logging.getLogger("test")
        output1 = _emit_and_capture(
            logger, logging.INFO, "test",
            extra={"document_id": SYNTHETIC_UUID},
        )
        output2 = _emit_and_capture(
            logger, logging.INFO, "test",
            extra={"document_id": SYNTHETIC_UUID},
        )
        assert output1 == output2


# ── LT-15: Operational metadata preserved ─────────────────────────────────

class TestOperationalMetadataPreserved:
    def test_warning_code_preserved(self):
        logger = logging.getLogger("test")
        output = _emit_and_capture(
            logger, logging.WARNING, "preview warning",
            extra={"warning_code": "UNSUPPORTED_DURATION_UNIT"},
        )
        assert "UNSUPPORTED_DURATION_UNIT" in output

    def test_http_status_preserved(self):
        logger = logging.getLogger("test")
        output = _emit_and_capture(
            logger, logging.INFO, "request complete",
            extra={"http_status": 200},
        )
        assert "200" in output

    def test_operation_name_preserved(self):
        logger = logging.getLogger("test")
        output = _emit_and_capture(
            logger, logging.INFO, "reference_event.confirmed",
        )
        assert "reference_event.confirmed" in output

    def test_result_status_preserved(self):
        logger = logging.getLogger("test")
        output = _emit_and_capture(
            logger, logging.INFO, "confirmation created",
            extra={"result_status": "success"},
        )
        assert "success" in output


# ── LT-16: No mutation ────────────────────────────────────────────────────

class TestNoMutation:
    def test_original_dict_unchanged(self):
        original = {"document_id": str(SYNTHETIC_UUID), "label": "keep"}
        _redact_dict_recursive(original)
        assert original["document_id"] == str(SYNTHETIC_UUID)

    def test_original_list_unchanged(self):
        original = [{"document_id": str(SYNTHETIC_UUID)}]
        _redact_dict_recursive(original)
        assert original[0]["document_id"] == str(SYNTHETIC_UUID)


# ── SENSITIVE_FIELDS completeness ─────────────────────────────────────────

class TestSensitiveFieldsCompleteness:
    def test_mandatory_fields_present(self):
        mandatory = {
            "confirmed_date", "reference_date", "calculated_date",
            "suggested_date", "evidence_text", "evidence_note",
            "source_text", "document_id", "confirmation_id",
        }
        assert mandatory.issubset(set(SENSITIVE_FIELDS))


class TestFilterHandlesAllFieldNames:
    @pytest.mark.parametrize("field", SENSITIVE_FIELDS)
    def test_field_is_redacted(self, field):
        logger = logging.getLogger("test")
        output = _emit_and_capture(
            logger, logging.INFO, "test",
            extra={field: "test-value"},
        )
        assert "test-value" not in output, (
            f"Field '{field}' was NOT redacted in: {output}"
        )


class TestRedactReferenceDate:
    def test_reference_date_in_extra(self):
        logger = logging.getLogger("test")
        output = _emit_and_capture(
            logger, logging.INFO, "reference",
            extra={"reference_date": "2026-07-01"},
        )
        assert "2026-07-01" not in output
        assert REDACTED_VALUE in output


class TestRedactCaseId:
    def test_case_id_in_extra(self):
        logger = logging.getLogger("test")
        test_uuid = uuid4()
        output = _emit_and_capture(
            logger, logging.INFO, "case",
            extra={"case_id": test_uuid},
        )
        assert str(test_uuid) not in output
