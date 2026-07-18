"""Unit tests for M6-A logging filter (reference date redaction).

SYNTHETISCH – KEINE ECHTEN PERSONEN- ODER FALLDATEN
"""

import logging

import pytest

from private_legal_navigator.infrastructure.log_filter import ReferenceEventLogFilter


class TestReferenceEventLogFilter:
    """Log filter redacts sensitive M6-A field names per INV-M6A-21/DP-08.

    The filter replaces sensitive field name occurrences with [REDACTED].
    This prevents field-level identification of sensitive data in logs.
    """

    @pytest.fixture
    def log_filter(self) -> ReferenceEventLogFilter:
        return ReferenceEventLogFilter()

    def test_redacts_confirmed_date_field(self, log_filter: ReferenceEventLogFilter) -> None:
        """confirmed_date field name is replaced."""
        msg = "confirmed_date=2026-07-15"
        result = log_filter.redact(msg)
        assert "confirmed_date" not in result
        assert "[REDACTED]" in result

    def test_redacts_evidence_text_field(self, log_filter: ReferenceEventLogFilter) -> None:
        """evidence_text field name is replaced."""
        msg = "evidence_text=Bescheid vom 15.07.2026"
        result = log_filter.redact(msg)
        assert "evidence_text" not in result
        assert "[REDACTED]" in result

    def test_redacts_evidence_note_field(self, log_filter: ReferenceEventLogFilter) -> None:
        """evidence_note field name is replaced."""
        msg = "evidence_note=Zustellungsurkunde geprueft"
        result = log_filter.redact(msg)
        assert "evidence_note" not in result
        assert "[REDACTED]" in result

    def test_redacts_source_text_field(self, log_filter: ReferenceEventLogFilter) -> None:
        """source_text field name is replaced."""
        msg = "source_text=innerhalb von zwei Wochen"
        result = log_filter.redact(msg)
        assert "source_text" not in result
        assert "[REDACTED]" in result

    def test_redacts_document_id_field(self, log_filter: ReferenceEventLogFilter) -> None:
        """document_id field name is replaced."""
        doc_id = "550e8400-e29b-41d4-a716-446655440000"
        msg = f"document_id={doc_id}"
        result = log_filter.redact(msg)
        assert "document_id" not in result
        assert "[REDACTED]" in result

    def test_redacts_confirmation_id_field(self, log_filter: ReferenceEventLogFilter) -> None:
        """confirmation_id field name is replaced."""
        conf_id = "660e8400-e29b-41d4-a716-446655440001"
        msg = f"confirmation_id={conf_id}"
        result = log_filter.redact(msg)
        assert "confirmation_id" not in result
        assert "[REDACTED]" in result

    def test_all_sensitive_fields_covered(self, log_filter: ReferenceEventLogFilter) -> None:
        """Verify the SENSITIVE_FIELDS list matches INV-M6A-21 and DP-08."""
        expected = {
            "confirmed_date",
            "evidence_text",
            "evidence_note",
            "source_text",
            "document_id",
            "confirmation_id",
        }
        actual = set(log_filter.SENSITIVE_FIELDS)
        assert actual == expected, f"Missing fields: {expected - actual}"

    def test_benign_message_unchanged(self, log_filter: ReferenceEventLogFilter) -> None:
        """Messages without sensitive fields are not modified."""
        msg = "This is a benign log message"
        result = log_filter.redact(msg)
        assert result == msg

    def test_multiple_occurrences(self, log_filter: ReferenceEventLogFilter) -> None:
        """Multiple sensitive field occurrences in the same message."""
        msg = "confirmed_date=2026-07-15 and evidence_text=Bescheid"
        result = log_filter.redact(msg)
        assert "confirmed_date" not in result
        assert "evidence_text" not in result
        assert result.count("[REDACTED]") == 2

    def test_filter_returns_true(self, log_filter: ReferenceEventLogFilter) -> None:
        """Filter must return True to not drop log records."""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test confirmation_id=abc",
            args=None,
            exc_info=None,
        )
        assert log_filter.filter(record) is True

    def test_filter_modifies_record(self, log_filter: ReferenceEventLogFilter) -> None:
        """Filter modifies the record message in-place."""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="confirmed_date=2026-07-15",
            args=None,
            exc_info=None,
        )
        log_filter.filter(record)
        assert "confirmed_date" not in record.msg
        assert "[REDACTED]" in record.msg

    def test_redact_dict_values(self, log_filter: ReferenceEventLogFilter) -> None:
        """Sensitive dictionary keys are redacted."""
        d = {"confirmed_date": "2026-07-15", "event_type": "delivery", "evidence_text": "Bescheid"}
        result = ReferenceEventLogFilter._redact_dict(d)
        assert result["confirmed_date"] == "[REDACTED]"
        assert result["evidence_text"] == "[REDACTED]"
        assert result["event_type"] == "delivery"
