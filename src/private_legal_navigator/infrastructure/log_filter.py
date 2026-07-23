"""Logging filter for M6-A reference date redaction.

Redacts sensitive fields from log output to prevent data leakage
of case-related dates, evidence text, and document identifiers.
"""

import logging
from typing import Any


class ReferenceEventLogFilter(logging.Filter):
    """Logging filter that redacts sensitive M6-A fields.

    Redacts the following fields from log records:
    - confirmed_date
    - evidence_text
    - evidence_note
    - source_text
    - document_id
    - confirmation_id
    """

    SENSITIVE_FIELDS = [
        "confirmed_date",
        "evidence_text",
        "evidence_note",
        "source_text",
        "document_id",
        "confirmation_id",
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter and redact sensitive fields in log messages."""
        if hasattr(record, "msg") and isinstance(record.msg, str):
            for field in self.SENSITIVE_FIELDS:
                record.msg = record.msg.replace(field, "[REDACTED]")
        if hasattr(record, "args") and isinstance(record.args, dict):
            record.args = self._redact_dict(record.args)
        elif hasattr(record, "args") and isinstance(record.args, tuple):
            record.args = tuple(
                self._redact_dict(a) if isinstance(a, dict) else a for a in record.args
            )
        return True

    @classmethod
    def redact(cls, message: str) -> str:
        """Redact sensitive fields from a string message.

        Can be used directly without the filter mechanism for
        explicit redaction in service code.

        Args:
            message: The message to redact.

        Returns:
            Redacted message with sensitive fields replaced by [REDACTED].
        """
        for field in cls.SENSITIVE_FIELDS:
            message = message.replace(field, "[REDACTED]")
        return message

    @staticmethod
    def _redact_dict(d: dict[str, Any]) -> dict[str, Any]:
        """Redact sensitive values in a dictionary."""
        redacted = dict(d)
        for key in list(redacted.keys()):
            if key in ReferenceEventLogFilter.SENSITIVE_FIELDS:
                redacted[key] = "[REDACTED]"
        return redacted
