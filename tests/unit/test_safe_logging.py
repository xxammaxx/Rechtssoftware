"""Unit tests for the Safe-Logging-API (safe_log_event, safe_log_failure).

Verifies that:
  - safe_log_event emits structured logs with event name visible
  - safe_log_failure emits error_code and exception_type but NEVER
    exception message or traceback
  - Sensitive fields are passed via extra (subject to PrivacyRedactionFilter)
  - Event names and error codes are static string literals
"""

from __future__ import annotations

import io
import logging
from uuid import UUID

from private_legal_navigator.infrastructure.log_redaction import (
    configure_logging,
)
from private_legal_navigator.infrastructure.safe_logging import (
    safe_log_event,
    safe_log_failure,
)

SYNTHETIC_UUID = UUID("aaaaaaa1-1111-1111-1111-aaaaaaaaaaaa")
SYNTHETIC_SECRET = "SYNTHETIC_SAFELOG_SECRET_7777"


class _RecordCaptureHandler(logging.Handler):
    """Handler that captures LogRecords for inspection."""

    def __init__(self):
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def _setup_with_capture() -> tuple[logging.Logger, io.StringIO, _RecordCaptureHandler]:
    """Set up logger with StringIO output AND record capture."""
    root = logging.getLogger()
    root.handlers.clear()
    root.filters.clear()
    root.setLevel(logging.DEBUG)

    # StringIO handler for text output
    stream = io.StringIO()
    stream_handler = logging.StreamHandler(stream)
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    root.addHandler(stream_handler)

    # Record capture handler
    capture_handler = _RecordCaptureHandler()
    capture_handler.setLevel(logging.DEBUG)
    root.addHandler(capture_handler)

    configure_logging()

    child = logging.getLogger("private_legal_navigator.test")
    child.propagate = True
    child.setLevel(logging.DEBUG)

    return child, stream, capture_handler


# ── safe_log_event tests ────────────────────────────────────────────────────


class TestSafeLogEvent:
    """safe_log_event() emits structured, safe log events."""

    def test_safe_log_event_emits_message(self):
        child, stream, capture = _setup_with_capture()
        safe_log_event(child, "test.event", result_status="success")
        output = stream.getvalue()
        assert "test.event" in output
        assert len(capture.records) >= 1

    def test_sensitive_extra_field_redacted(self):
        """Sensitive field names in extra are redacted by the filter."""
        child, stream, capture = _setup_with_capture()
        safe_log_event(
            child,
            "reference_event.confirmed",
            document_id=str(SYNTHETIC_UUID),
            result_status="success",
        )
        output = stream.getvalue()
        assert str(SYNTHETIC_UUID) not in output, f"safe_log_event leaked sensitive UUID: {output}"
        assert "reference_event.confirmed" in output

    def test_safe_log_event_confirm_pattern(self):
        """Verify the confirm pattern from event_service.py works."""
        child, stream, capture = _setup_with_capture()
        safe_log_event(
            child,
            "reference_event.confirmed",
            confirmation_method="MANUALLY_ENTERED",
            source_type="USER_MANUAL",
            result_status="success",
        )
        output = stream.getvalue()
        assert "reference_event.confirmed" in output

    def test_safe_log_event_rejected_pattern(self):
        """Verify the reject pattern from event_service.py works."""
        child, stream, capture = _setup_with_capture()
        safe_log_event(child, "reference_event.rejected", result_status="success")
        output = stream.getvalue()
        assert "reference_event.rejected" in output

    def test_safe_log_event_revoked_pattern(self):
        """Verify the revoke pattern from event_service.py works."""
        child, stream, capture = _setup_with_capture()
        safe_log_event(child, "reference_event.revoked", result_status="success")
        output = stream.getvalue()
        assert "reference_event.revoked" in output

    def test_extra_fields_on_record(self):
        """Extra fields are set on the LogRecord for structured logging."""
        child, stream, capture = _setup_with_capture()
        safe_log_event(
            child,
            "test.extra",
            confirmation_method="AUTO_SUGGESTED",
            result_status="success",
        )
        assert len(capture.records) >= 1
        record = capture.records[0]
        assert hasattr(record, "confirmation_method")
        assert record.confirmation_method == "AUTO_SUGGESTED"


# ── safe_log_failure tests ──────────────────────────────────────────────────


class TestSafeLogFailure:
    """safe_log_failure() emits error events WITHOUT exception messages."""

    def test_safe_log_failure_emits_event_name(self):
        child, stream, capture = _setup_with_capture()
        safe_log_failure(
            child,
            "reference_event.failed",
            error_code="INTERNAL_PROCESSING_ERROR",
        )
        output = stream.getvalue()
        assert "reference_event.failed" in output

    def test_error_code_on_record(self):
        """Error code is set on the LogRecord for structured logging."""
        child, stream, capture = _setup_with_capture()
        safe_log_failure(
            child,
            "reference_event.failed",
            error_code="INTERNAL_PROCESSING_ERROR",
        )
        assert len(capture.records) >= 1
        record = capture.records[0]
        assert hasattr(record, "error_code")
        assert record.error_code == "INTERNAL_PROCESSING_ERROR"

    def test_safe_log_failure_emits_exception_type_only(self):
        """Exception type name appears on record, but NOT the message."""
        child, stream, capture = _setup_with_capture()
        try:
            raise ValueError("This message should NOT be in the log")
        except ValueError as exc:
            safe_log_failure(
                child,
                "reference_event.failed",
                error_code="INTERNAL_PROCESSING_ERROR",
                exception=exc,
            )
        output = stream.getvalue()
        # Exception message must NOT appear
        assert "This message should NOT be in the log" not in output, (
            f"safe_log_failure leaked exception message: {output}"
        )
        # Exception type name on record
        assert len(capture.records) >= 1
        record = capture.records[0]
        assert hasattr(record, "exception_type")
        assert record.exception_type == "ValueError"

    def test_safe_log_failure_no_traceback(self):
        """safe_log_failure uses logger.error(), not logger.exception().
        No traceback should appear in output."""
        child, stream, capture = _setup_with_capture()
        try:
            raise ValueError("secret_message_12345")
        except ValueError as exc:
            safe_log_failure(
                child,
                "reference_event.failed",
                error_code="INTERNAL_PROCESSING_ERROR",
                exception=exc,
            )
        output = stream.getvalue()
        assert "Traceback" not in output, f"safe_log_failure emitted traceback: {output}"

    def test_safe_log_failure_no_exception_args(self):
        """Exception args must not appear in the log."""
        child, stream, capture = _setup_with_capture()

        class CustomError(Exception):
            pass

        try:
            raise CustomError("arg1", "arg2", "secret_data")
        except CustomError as exc:
            safe_log_failure(
                child,
                "reference_event.failed",
                error_code="INTERNAL_PROCESSING_ERROR",
                exception=exc,
            )
        output = stream.getvalue()
        assert "arg1" not in output
        assert "arg2" not in output
        assert "secret_data" not in output

    def test_safe_log_failure_with_extra_sensitive_field(self):
        """Extra sensitive fields are redacted even in failure path."""
        child, stream, capture = _setup_with_capture()
        try:
            raise ValueError("test")
        except ValueError as exc:
            safe_log_failure(
                child,
                "reference_event.failed",
                error_code="INTERNAL_PROCESSING_ERROR",
                exception=exc,
                document_id=str(SYNTHETIC_UUID),
            )
        output = stream.getvalue()
        assert str(SYNTHETIC_UUID) not in output, (
            f"safe_log_failure leaked extra sensitive field: {output}"
        )

    def test_safe_log_failure_result_status_is_failure(self):
        """Result status is always 'failure' in safe_log_failure."""
        child, stream, capture = _setup_with_capture()
        safe_log_failure(
            child,
            "reference_event.failed",
            error_code="INTERNAL_PROCESSING_ERROR",
        )
        assert len(capture.records) >= 1
        record = capture.records[0]
        assert hasattr(record, "result_status")
        assert record.result_status == "failure"


# ── Integration: chain with PrivacyRedactionFilter ─────────────────────────


class TestSafeLoggingWithFilter:
    """Verify safe_log_event/safe_log_failure work with PrivacyRedactionFilter."""

    def test_filter_does_not_block_safe_events(self):
        """The filter returns True (never blocks records)."""
        child, stream, capture = _setup_with_capture()
        safe_log_event(child, "test.passes.filter", result_status="ok")
        output = stream.getvalue()
        assert "test.passes.filter" in output

    def test_filter_redacts_nested_structures(self):
        """Nested data in fields is recursively redacted."""
        child, stream, capture = _setup_with_capture()
        safe_log_event(
            child,
            "test.nested",
            payload={
                "document_id": str(SYNTHETIC_UUID),
                "safe_field": "ok",
            },
        )
        output = stream.getvalue()
        assert str(SYNTHETIC_UUID) not in output
        assert "test.nested" in output


# ── Idempotency and safety ──────────────────────────────────────────────────


class TestSafeLoggingSafety:
    """safe_log_event and safe_log_failure are safe for repeated calls."""

    def test_multiple_events_no_side_effects(self):
        child, stream, capture = _setup_with_capture()
        for i in range(5):
            safe_log_event(child, "test.multi", iteration=i)
        output = stream.getvalue()
        assert output.count("test.multi") == 5

    def test_logger_not_modified(self):
        child, stream, capture = _setup_with_capture()
        level_before = child.level
        propagate_before = child.propagate
        safe_log_event(child, "test.no_modify")
        assert child.level == level_before
        assert child.propagate == propagate_before
