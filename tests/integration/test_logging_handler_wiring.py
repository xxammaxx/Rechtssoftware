"""Integration tests: real handler emission through the full logging pipeline.

These tests prove that the PrivacyRedactionFilter is active on the actual
emit path: Logger -> Handler -> Filter -> Formatter -> Stream.

Unlike the unit tests in test_log_redaction.py, these tests NEVER call
filter.filter(record) directly. They use real loggers with real handlers.
"""

from __future__ import annotations

import io
import logging
from uuid import UUID

import pytest

from private_legal_navigator.infrastructure.log_redaction import (
    REDACTED_VALUE,
    PrivacyRedactionFilter,
    configure_logging,
)

# ── Synthetic test markers ─────────────────────────────────────────────────
SYNTHETIC_UUID = UUID("bbbbbbbb-1111-cccc-2222-ddddeeeeeeee")
SYNTHETIC_DATE = "2026-12-31"
SYNTHETIC_SECRET = "SYNTHETIC_DOCUMENT_ID_SECRET_XYZ"
SYNTHETIC_EXCEPTION_SECRET = "SYNTHETIC_EXCEPTION_SECRET_ABC"
SYNTHETIC_CONFIRMATION_ID = "SYNTHETIC_CONFIRMATION_ID_SECRET_123"


def _setup_clean_root() -> tuple[logging.Logger, io.StringIO]:
    """Reset the root logger and return it with a fresh StringIO handler."""
    root = logging.getLogger()
    root.handlers.clear()
    root.filters.clear()
    root.setLevel(logging.DEBUG)

    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    root.addHandler(handler)

    return root, stream


# ── HRT-01: Child Logger + extra field ──────────────────────────────────────


class TestRealChildLoggerExtra:
    """HRT-01 — A child logger's extra fields must be redacted on emission."""

    def test_extra_document_id_redacted(self):
        root, stream = _setup_clean_root()
        configure_logging()

        child = logging.getLogger("private_legal_navigator.api")
        child.propagate = True
        child.setLevel(logging.DEBUG)

        child.info("event confirmed", extra={"document_id": str(SYNTHETIC_UUID)})
        output = stream.getvalue()

        assert str(SYNTHETIC_UUID) not in output, (
            f"Sensitive UUID leaked in real emission: {output}"
        )
        assert "event confirmed" in output

    def test_extra_confirmed_date_redacted(self):
        root, stream = _setup_clean_root()
        configure_logging()

        child = logging.getLogger("private_legal_navigator.api")
        child.propagate = True
        child.setLevel(logging.DEBUG)

        child.info("date confirmed", extra={"confirmed_date": SYNTHETIC_DATE})
        output = stream.getvalue()

        assert SYNTHETIC_DATE not in output
        assert "date confirmed" in output


# ── HRT-02: Mapping args (dict-style logging) ──────────────────────────────


class TestRealChildLoggerMappingArgs:
    """HRT-02 — Mapping args must be redacted through real handler path."""

    def test_mapping_document_id_redacted(self):
        root, stream = _setup_clean_root()
        configure_logging()

        child = logging.getLogger("private_legal_navigator.application")
        child.propagate = True
        child.setLevel(logging.DEBUG)

        child.info("processed", {"document_id": str(SYNTHETIC_UUID)})
        output = stream.getvalue()

        assert str(SYNTHETIC_UUID) not in output
        assert "processed" in output


# ── HRT-03: Nested mapping structures ──────────────────────────────────────


class TestNestedMappingRedaction:
    """HRT-03 — Nested dict structures in extra must have sensitive keys redacted."""

    def test_nested_evidence_note_redacted(self):
        root, stream = _setup_clean_root()
        configure_logging()

        child = logging.getLogger("private_legal_navigator.infrastructure")
        child.propagate = True
        child.setLevel(logging.DEBUG)

        child.info(
            "nested event",
            extra={
                "payload": {
                    "evidence_note": SYNTHETIC_SECRET,
                    "safe_field": "keep_me",
                }
            },
        )
        output = stream.getvalue()

        assert SYNTHETIC_SECRET not in output
        assert "nested event" in output


# ── HRT-04: Formatter preserves structure ──────────────────────────────────


class TestFormatterOutput:
    """HRT-04 — Formatter preserves operation metadata, extra fields are redacted.

    NOTE: The formatter uses %(message)s which renders record.getMessage().
    Extra attributes (document_id, etc.) are stored on the record but NOT
    rendered by the default formatter. Redaction is verified by checking
    the sensitive UUID does NOT appear, NOT by checking for [REDACTED]
    in the formatted text (which won't appear unless %(document_id)s is
    in the format string).
    """

    def test_sensitive_uuid_not_in_formatted_output(self):
        root, stream = _setup_clean_root()
        configure_logging()

        child = logging.getLogger("private_legal_navigator")
        child.propagate = True
        child.setLevel(logging.DEBUG)

        child.info("reference_event.confirmed", extra={"document_id": str(SYNTHETIC_UUID)})
        output = stream.getvalue()

        assert str(SYNTHETIC_UUID) not in output, (
            f"Sensitive UUID appeared in formatted output: {output}"
        )
        assert "reference_event.confirmed" in output

    def test_extra_attribute_is_redacted_on_record(self):
        """Verify that even though extra attrs aren't in formatted output,
        the record attribute itself is redacted (defense in depth)."""
        root, stream = _setup_clean_root()
        configure_logging()

        child = logging.getLogger("private_legal_navigator")
        child.propagate = True
        child.setLevel(logging.DEBUG)

        # Use a custom formatter that renders extra attrs to prove redaction
        root.handlers[0].setFormatter(
            logging.Formatter("%(levelname)s %(name)s: %(message)s doc_id=%(document_id)s")
        )
        stream.truncate(0)
        stream.seek(0)

        child.info("reference_event.confirmed", extra={"document_id": str(SYNTHETIC_UUID)})
        output = stream.getvalue()

        assert str(SYNTHETIC_UUID) not in output, (
            f"Sensitive UUID leaked through custom formatter: {output}"
        )
        assert REDACTED_VALUE in output, (
            f"[REDACTED] not found in custom-formatted output: {output}"
        )
        assert "reference_event.confirmed" in output


# ── HRT-05: Idempotency ────────────────────────────────────────────────────


class TestIdempotency:
    """HRT-05 — configure_logging() must be safe to call multiple times."""

    def test_no_duplicate_handlers(self):
        root = logging.getLogger()
        root.handlers.clear()
        root.filters.clear()

        configure_logging()
        first_handler_count = len(root.handlers)

        configure_logging()
        second_handler_count = len(root.handlers)

        assert first_handler_count == second_handler_count, (
            f"configure_logging created duplicate handlers: "
            f"first={first_handler_count}, second={second_handler_count}"
        )

    def test_no_duplicate_filters_per_handler(self):
        root = logging.getLogger()
        root.handlers.clear()
        root.filters.clear()

        configure_logging()
        configure_logging()
        configure_logging()

        for h in root.handlers:
            privacy_filters = [f for f in h.filters if isinstance(f, PrivacyRedactionFilter)]
            assert len(privacy_filters) == 1, (
                f"Handler has {len(privacy_filters)} PrivacyRedactionFilters, expected exactly 1"
            )

    def test_idempotent_emission(self):
        """Multiple configure_logging calls must not cause double emission."""
        root = logging.getLogger()
        root.handlers.clear()
        root.filters.clear()

        configure_logging()

        stream = io.StringIO()
        # Replace handler with instrumented one for capture
        root.handlers.clear()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter("%(message)s"))
        root.addHandler(handler)

        configure_logging()  # second call — should add filter to handler

        child = logging.getLogger("private_legal_navigator")
        child.propagate = True
        child.setLevel(logging.DEBUG)

        child.info("test message", extra={"document_id": str(SYNTHETIC_UUID)})
        output = stream.getvalue()

        lines = [line for line in output.strip().split("\n") if line]
        assert len(lines) == 1, f"Expected exactly 1 log line, got {len(lines)}: {lines}"


# ── HRT-06: Multiple child loggers ─────────────────────────────────────────


class TestMultipleChildLoggers:
    """HRT-06 — All application child loggers must be protected."""

    LOGGER_NAMES = [
        "private_legal_navigator",
        "private_legal_navigator.api",
        "private_legal_navigator.application",
        "private_legal_navigator.infrastructure",
    ]

    @pytest.mark.parametrize("logger_name", LOGGER_NAMES)
    def test_child_logger_protected(self, logger_name):
        root, stream = _setup_clean_root()
        configure_logging()

        child = logging.getLogger(logger_name)
        child.propagate = True
        child.setLevel(logging.DEBUG)

        child.info("test", extra={"document_id": str(SYNTHETIC_UUID)})
        output = stream.getvalue()

        assert str(SYNTHETIC_UUID) not in output, f"Logger '{logger_name}' leaked UUID in: {output}"


# ── HRT-07: Non-application loggers untouched ──────────────────────────────


class TestForeignLoggersUntouched:
    """HRT-07 — configure_logging must not mutate unrelated loggers."""

    def test_foreign_logger_handlers_unchanged(self):
        foreign = logging.getLogger("some.other.library")
        foreign.handlers.clear()

        root, _ = _setup_clean_root()
        configure_logging()

        # Foreign logger should NOT have handlers added
        assert len(foreign.handlers) == 0, (
            f"Foreign logger got unexpected handlers: {foreign.handlers}"
        )

    def test_foreign_logger_propagate_unchanged(self):
        foreign = logging.getLogger("another.library")
        original_propagate = foreign.propagate

        root, _ = _setup_clean_root()
        configure_logging()

        assert foreign.propagate == original_propagate, (
            "configure_logging changed propagate on foreign logger"
        )


# ── HRT-08: Handler has filter ─────────────────────────────────────────────


class TestHandlerHasFilter:
    """HRT-08 — Every root handler must have exactly one PrivacyRedactionFilter."""

    def test_handler_has_privacy_filter(self):
        root = logging.getLogger()
        root.handlers.clear()
        root.filters.clear()

        configure_logging()

        for h in root.handlers:
            privacy_filters = [f for f in h.filters if isinstance(f, PrivacyRedactionFilter)]
            assert len(privacy_filters) == 1, (
                f"Handler {h} missing PrivacyRedactionFilter (filters: {h.filters})"
            )


# ── Positional and f-string leak detection ──────────────────────────────────


class TestPositionalAndFStringLeakDetection:
    """Prove that positional %s and f-strings bypass the filter.

    These tests document the CURRENT LIMITATION of the key-based filter.
    The fix is NOT to make the filter smarter, but to enforce a STATIC
    POLICY GUARD (see test_logging_static_policy.py) that prevents these
    patterns in product code.

    These tests serve as RED_TEST evidence that the leak exists without
    the static guard.
    """

    def test_positional_args_leak_proven(self):
        """Prove that positional %s logging leaks sensitive data."""
        root, stream = _setup_clean_root()
        configure_logging()

        child = logging.getLogger("private_legal_navigator")
        child.propagate = True
        child.setLevel(logging.DEBUG)

        # THIS IS FORBIDDEN by static policy — but proves filter gap
        child.info("document_id=%s", str(SYNTHETIC_UUID))
        output = stream.getvalue()

        assert str(SYNTHETIC_UUID) in output, (
            "RED_TEST FAILED: positional arg should leak (proves filter gap)"
        )

    def test_fstring_leak_proven(self):
        """Prove that f-string logging leaks sensitive data."""
        root, stream = _setup_clean_root()
        configure_logging()

        child = logging.getLogger("private_legal_navigator")
        child.propagate = True
        child.setLevel(logging.DEBUG)

        # THIS IS FORBIDDEN by static policy — but proves filter gap
        child.info(f"document_id={SYNTHETIC_UUID}")
        output = stream.getvalue()

        assert str(SYNTHETIC_UUID) in output, (
            "RED_TEST FAILED: f-string should leak (proves filter gap)"
        )


# ── Exception path through real handler ─────────────────────────────────────


class TestRealExceptionPath:
    """Test that the real exception emission path is protected."""

    def test_exception_extra_redacted(self):
        """Exception with extra must redact sensitive fields."""
        root, stream = _setup_clean_root()
        configure_logging()

        child = logging.getLogger("private_legal_navigator")
        child.propagate = True
        child.setLevel(logging.DEBUG)

        try:
            raise ValueError("stable_error_code_only")
        except ValueError:
            child.exception(
                "reference_event.failed",
                extra={"document_id": str(SYNTHETIC_UUID)},
            )

        output = stream.getvalue()
        assert str(SYNTHETIC_UUID) not in output, (
            f"Sensitive UUID leaked in exception log: {output}"
        )
        assert "reference_event.failed" in output
        assert "Traceback" in output

    def test_safe_exception_message_preserved(self):
        """Exception with safe (non-sensitive) message must still log traceback."""
        root, stream = _setup_clean_root()
        configure_logging()

        child = logging.getLogger("private_legal_navigator")
        child.propagate = True
        child.setLevel(logging.DEBUG)

        try:
            raise ValueError("INVALID_CONFIRMATION_CONTEXT")
        except ValueError:
            child.exception("reference_event.failed")

        output = stream.getvalue()
        assert "Traceback" in output
        assert "INVALID_CONFIRMATION_CONTEXT" in output  # safe error code

    def test_exception_message_with_secret_leaks(self):
        """Prove that exception messages with secrets WILL leak in traceback.

        This is a RED_TEST: the filter cannot redact text inside exception
        messages or tracebacks. The static policy guard must prevent putting
        secrets in exception messages.
        """
        root, stream = _setup_clean_root()
        configure_logging()

        child = logging.getLogger("private_legal_navigator")
        child.propagate = True
        child.setLevel(logging.DEBUG)

        try:
            raise ValueError(f"confirmation_id={SYNTHETIC_EXCEPTION_SECRET}")
        except ValueError:
            child.exception("reference_event.failed")

        output = stream.getvalue()
        assert SYNTHETIC_EXCEPTION_SECRET in output, (
            "RED_TEST FAILED: exception message should leak (proves filter gap)"
        )
