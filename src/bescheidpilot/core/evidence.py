"""Evidence layer — anchors every critical extraction to its source text.

No network, no I/O, no external dependencies. Purely functional.
"""

from __future__ import annotations

from .models import EvidenceSpan


def make_evidence(
    field: str,
    value: str,
    text: str,
    match_start: int,
    match_end: int,
    confidence: float = 1.0,
    context_chars: int = 60,
) -> EvidenceSpan:
    """Create an EvidenceSpan anchored in *text*.

    Parameters
    ----------
    field: Analytical field name ('deadline', 'authority', etc.).
    value: Extracted value.
    text: The full source text (for context extraction).
    match_start: Character offset where the match begins.
    match_end: Character offset where the match ends.
    confidence: 0.0–1.0.
    context_chars: Number of surrounding characters for the quote.
    """
    quote_start = max(0, match_start - context_chars // 2)
    quote_end = min(len(text), match_end + context_chars // 2)
    quote = text[quote_start:quote_end].strip()

    return EvidenceSpan(
        field=field,
        value=value,
        quote=quote,
        start=match_start,
        end=match_end,
        confidence=confidence,
    )


def evidence_for_match(
    field: str,
    text: str,
    start: int,
    end: int,
    confidence: float = 1.0,
) -> EvidenceSpan:
    """Create evidence from a regex match position."""
    value = text[start:end].strip()
    return make_evidence(
        field=field,
        value=value,
        text=text,
        match_start=start,
        match_end=end,
        confidence=confidence,
    )


def evidence_for_line(
    field: str,
    text: str,
    line_start: int,
    line_end: int,
    confidence: float = 0.8,
) -> EvidenceSpan:
    """Create evidence spanning a line range (lower confidence)."""
    value = text[line_start:line_end].strip()
    return make_evidence(
        field=field,
        value=value,
        text=text,
        match_start=line_start,
        match_end=line_end,
        confidence=confidence,
    )
