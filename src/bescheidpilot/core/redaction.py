"""Redact sensitive personal data from text for safe logging and output.

This module provides regex-based pattern matching for common German
administrative and personal data markers. It is a guardrail helper,
not a perfect anonymization engine. No network, no external deps.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Sensitive pattern definitions
# ---------------------------------------------------------------------------

# German email address
_EMAIL_PATTERN = re.compile(
    r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b",
)

# German phone numbers (various formats)
_PHONE_PATTERN = re.compile(
    r"\b(?:\+49[\s.-]?|0)\d{1,5}[\s./-]?\d{3,8}[\s./-]?\d{1,8}\b",
)

# German IBAN
_IBAN_PATTERN = re.compile(
    r"\bDE\d{2}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{2}\b",
)

# Aktenzeichen (case IDs): various formats like JC-12345/2026, 12345/67, AZ: 12345/2026
_CASE_ID_PATTERN = re.compile(
    r"\b(?:Aktenzeichen|AZ)\s*[:.]?\s*[\w-]+(?:/[\w-]+)*\b",
    re.IGNORECASE,
)

# Short case ID without prefix: JC-12345/2026, BG-12345/67
_SHORT_CASE_ID_PATTERN = re.compile(
    r"\b[A-Z]{2,4}[-/]\d{3,6}(?:[-/]\d{2,4})?\b",
)

# Kundennummer / customer number
_CUSTOMER_ID_PATTERN = re.compile(
    r"\b(?:Kundennummer|Kunden-Nr\.?)\s*[:.]?\s*\d+\b",
    re.IGNORECASE,
)

# BG-Nummer (Bedarfsgemeinschaft)
_BG_NUMBER_PATTERN = re.compile(
    r"\bBG[- ]?[\w-]{3,20}\b",
    re.IGNORECASE,
)

# Sozialversicherungsnummer
_SV_NUMBER_PATTERN = re.compile(
    r"\b\d{2}\s?\d{6}\s?[A-Z]\s?\d{3}\b",
)

# German postal address (street + number, simplified)
_ADDRESS_PATTERN = re.compile(
    r"\b[A-ZÄÖÜ][a-zäöüß]+(?:straße|str\.?|allee|platz|weg|gasse|damm|ring)\s+\d{1,4}[a-z]?\b",
    re.IGNORECASE,
)

# Postal code + city
_POSTAL_CITY_PATTERN = re.compile(
    r"\b\d{5}\s+[A-ZÄÖÜ][a-zäöüß]+(?:\s+(?:am|an|bei|in|im|ob|auf)\s+[A-ZÄÖÜ][a-zäöüß]+)?\b",
)

# Date of birth
_BIRTH_DATE_PATTERN = re.compile(
    r"\b(?:geb\.?|geboren|Geburtsdatum)\s*[:.]?\s*\d{1,2}[.]\d{1,2}[.]\d{2,4}\b",
    re.IGNORECASE,
)

# German personal names (simplified: two capitalized words)
# Only applied when surrounded by other redaction markers to avoid
# over-matching. Used selectively in context.
_NAME_PATTERN = re.compile(
    r"\b(?:Herrn?|Frau|Familie)\s+[A-ZÄÖÜ][a-zäöüß-]+\s+[A-ZÄÖÜ][a-zäöüß-]+\b",
)

# Deadline pattern: "Frist bis zum 15.07.2026", "innerhalb von 14 Tagen"
_DEADLINE_PATTERN = re.compile(
    r"\b(?:Frist|spätestens|bis zum|bis\s+zum|innerhalb von)\s+\S+(?:\s+\S+){0,4}\b",
    re.IGNORECASE,
)

# Bescheid-Rohtext-Marker (typical opening/closing phrases)
_BESCHEID_MARKER_PATTERN = re.compile(
    r"\b(?:Bescheid|Widerspruchsbescheid|Leistungsbescheid|"
    r"Bewilligungsbescheid|Ablehnungsbescheid|Änderungsbescheid)\s+vom\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Pattern list (ordered: more specific first)
# ---------------------------------------------------------------------------

_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    ("EMAIL", _EMAIL_PATTERN, "[REDACTED_EMAIL]"),
    ("IBAN", _IBAN_PATTERN, "[REDACTED_IBAN]"),
    ("CASE_ID_LABELED", _CASE_ID_PATTERN, "[REDACTED_CASE_ID]"),
    ("CUSTOMER_ID", _CUSTOMER_ID_PATTERN, "[REDACTED_CUSTOMER_ID]"),
    ("BG_NUMBER", _BG_NUMBER_PATTERN, "[REDACTED_BG_NUMBER]"),
    ("SV_NUMBER", _SV_NUMBER_PATTERN, "[REDACTED_SV_NUMBER]"),
    ("BIRTH_DATE", _BIRTH_DATE_PATTERN, "[REDACTED_BIRTH_DATE]"),
    ("ADDRESS", _ADDRESS_PATTERN, "[REDACTED_ADDRESS]"),
    ("POSTAL_CITY", _POSTAL_CITY_PATTERN, "[REDACTED_LOCATION]"),
    ("PHONE", _PHONE_PATTERN, "[REDACTED_PHONE]"),
    ("NAME_PREFIXED", _NAME_PATTERN, "[REDACTED_NAME]"),
    ("SHORT_CASE_ID", _SHORT_CASE_ID_PATTERN, "[REDACTED_CASE_ID]"),
    ("DEADLINE", _DEADLINE_PATTERN, "[REDACTED_DEADLINE]"),
]


def redact_sensitive_text(text: str) -> str:
    """Return *text* with recognised sensitive patterns replaced by
    ``[REDACTED_...]`` placeholders.

    No network access. No external dependencies. Purely regex-based.
    """
    result = text
    for _name, pattern, replacement in _PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def contains_sensitive_pattern(text: str) -> bool:
    """Return ``True`` when at least one known sensitive pattern is found."""
    return any(pattern.search(text) for _, pattern, _ in _PATTERNS)


def list_detected_patterns(text: str) -> list[str]:
    """Return the names of all sensitive pattern types found in *text*."""
    found: list[str] = []
    for name, pattern, _ in _PATTERNS:
        if pattern.search(text):
            found.append(name)
    return found


# ---------------------------------------------------------------------------
# Safe logging helper
# ---------------------------------------------------------------------------


def safe_log(text: str, allow_technical: bool = True) -> str:
    """Return a log-safe version of *text*.

    If *allow_technical* is ``True`` (default), technical terms like
    ``analysis_mode`` and ``execution_mode`` are preserved. Otherwise
    everything is redacted.
    """
    return redact_sensitive_text(text)
