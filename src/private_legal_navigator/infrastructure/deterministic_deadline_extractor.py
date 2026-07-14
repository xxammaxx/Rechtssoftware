"""Deterministic, rule-based deadline candidate extractor.

Pure deterministic extraction — no ML, no LLM, no cloud, no locale dependency.
All patterns are hard-coded and ReDoS-safe.

M5 erkennt ausschließlich mögliche Frist- und Terminangaben im Text.
Es berechnet keine verbindliche Rechtsfrist.
"""

from __future__ import annotations

import concurrent.futures
import re
from datetime import date

from private_legal_navigator.application.deadline_extractor import DeadlineExtractor
from private_legal_navigator.domain.deadline import (
    DeadlineCandidate,
    DeadlineCandidateKind,
    DeadlineCertainty,
    DeadlineExtractionResult,
    DeadlineWarning,
    DeadlineWarningCode,
)

# ---------------------------------------------------------------------------
# Maximum text length for safety (500K chars ≈ ~100 pages of legal text)
# ---------------------------------------------------------------------------
MAX_TEXT_LENGTH: int = 500_000

# Regex timeout in seconds
REGEX_TIMEOUT: float = 5.0

# ---------------------------------------------------------------------------
# Hardcoded German month names (no locale dependency, fully deterministic)
# ---------------------------------------------------------------------------
GERMAN_MONTHS: dict[str, int] = {
    "januar": 1,
    "februar": 2,
    "märz": 3,
    "april": 4,
    "mai": 5,
    "juni": 6,
    "juli": 7,
    "august": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "dezember": 12,
    # Common abbreviations
    "jan": 1,
    "feb": 2,
    "mär": 3,
    "apr": 4,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "okt": 10,
    "nov": 11,
    "dez": 12,
    # With dots
    "jan.": 1,
    "feb.": 2,
    "mär.": 3,
    "apr.": 4,
    "jun.": 6,
    "jul.": 7,
    "aug.": 8,
    "sep.": 9,
    "okt.": 10,
    "nov.": 11,
    "dez.": 12,
}

# ---------------------------------------------------------------------------
# German number words (for relative periods)
# ---------------------------------------------------------------------------
GERMAN_NUMBER_WORDS: dict[str, int] = {
    "eins": 1,
    "einem": 1,
    "einer": 1,
    "eines": 1,
    "ein": 1,
    "zwei": 2,
    "drei": 3,
    "vier": 4,
    "fünf": 5,
    "fuenf": 5,
    "sechs": 6,
    "sieben": 7,
    "acht": 8,
    "neun": 9,
    "zehn": 10,
    "elf": 11,
    "zwölf": 12,
    "zwoelf": 12,
    "zwanzig": 20,
    "dreissig": 30,
}

# ---------------------------------------------------------------------------
# Time unit mapping
# ---------------------------------------------------------------------------
GERMAN_UNIT_MAP: dict[str, str] = {
    "tag": "Tag",
    "tagen": "Tag",
    "tage": "Tag",
    "woche": "Woche",
    "wochen": "Woche",
    "monat": "Monat",
    "monaten": "Monat",
    "monate": "Monat",
    "jahr": "Jahr",
    "jahren": "Jahr",
    "jahre": "Jahr",
    "werktag": "Werktag",
    "werktagen": "Werktag",
    "werktage": "Werktag",
    "arbeitstag": "Arbeitstag",
    "arbeitstagen": "Arbeitstag",
}

# ---------------------------------------------------------------------------
# REGEX PATTERNS — All ReDoS-safe by design:
#   - No nested quantifiers
#   - Mutually exclusive alternation branches
#   - No unbounded .*? in repeated groups
#   - Bounded quantifiers {1,4} instead of +
#   - Negative lookarounds for false-positive prevention
# ---------------------------------------------------------------------------

# R1: Numeric German dates: TT.MM.JJJJ
# Safe: negated char classes for digits, no nested quantifiers
_NUMERIC_DATE_RE = re.compile(
    r"""
    (?<![A-Za-z0-9])             # Not preceded by alphanumeric (avoids version numbers)
    (0?[1-9]|[12]\d|3[01])       # Day: 01-31 or 1-31
    \.\s*                         # Dot, optional whitespace
    (0?[1-9]|1[0-2])             # Month: 01-12 or 1-12
    \.\s*                         # Dot, optional whitespace
    (19\d{2}|20\d{2})            # Year: 1900-2099
    (?![A-Za-z0-9])              # Not followed by alphanumeric
    """,
    re.VERBOSE,
)

# R2: Written-out German month names: T. Monat JJJJ
# Safe: alternation branches for months are mutually exclusive
_TEXTUAL_DATE_RE = re.compile(
    r"""
    (?<![A-Za-z0-9])
    (0?[1-9]|[12]\d|3[01])       # Day
    \.\s+                         # Dot + whitespace
    (Januar|Februar|März|April|Mai|Juni|Juli|
     August|September|Oktober|November|Dezember|
     Jan\.?|Feb\.?|Mär\.?|Apr\.?|Jun\.?|Jul\.?|
     Aug\.?|Sep\.?|Okt\.?|Nov\.?|Dez\.?)
    \s+
    (19\d{2}|20\d{2})
    (?![A-Za-z0-9])
    """,
    re.VERBOSE | re.IGNORECASE,
)

# R3: Relative periods with numeric amount
# "innerhalb von 14 Tagen", "binnen 4 Wochen", etc.
# Safe: distinct literal prefixes, no nested quantifiers
_RELATIVE_NUMERIC_RE = re.compile(
    r"""
    (?i)
    (?:
        innerhalb\s+(?:von\s+)?(?:ca\.?\s*)?
        (\d+)\s*
        (Tagen?|Wochen?|Monaten?|Jahren?|Werktagen?|Arbeitstagen?)
    )
    |
    (?:
        binnen\s+(?:ca\.?\s*)?
        (\d+)\s*
        (Tagen?|Wochen?|Monaten?|Jahren?|Werktagen?|Arbeitstagen?)
    )
    """,
    re.VERBOSE,
)

# R4: Relative periods with article (singular)
# "innerhalb eines Monats", "binnen einer Woche"
# Safe: distinct literal prefixes
_RELATIVE_ARTICLE_RE = re.compile(
    r"""
    (?i)
    (?:
        innerhalb\s+(?:von\s+)?
        (?:einem|einer|eines|ein)\s+
        (Tag|Woche|Monat|Jahr|Werktag|Arbeitstag)
    )
    |
    (?:
        binnen\s+
        (?:einem|einer|eines|ein)\s+
        (Tag|Woche|Monat|Jahr|Werktag|Arbeitstag)
    )
    """,
    re.VERBOSE,
)

# R5: Fristkontext-Präfix (context for explicit dates)
# We scan for date-like patterns prefixed with deadline-related words
# and include the prefix in the match for richer raw_text.
# Safe: bounded quantifiers, literal alternation
_FRISTKONTEXT_PREFIX_RE = re.compile(
    r"""
    (?i)
    (?:
        bis\s+(?:spätestens\s+)?(?:zum\s+|einschließlich\s+)?
        |spätestens\s+(?:am\s+)?(?:zum\s+)?
        |zum\s+
        |ab\s+(?:dem\s+)?
    )
    (?=\d{1,2}\.\s*\d{1,2}\.\s*\d{4})
    """,
    re.VERBOSE,
)

# R6: Qualitative references (unresolvable legal terms)
# "unverzüglich", "ohne schuldhaftes Zögern", etc.
# Safe: only literal alternation, no quantifiers at all
_QUALITATIVE_RE = re.compile(
    r"""
    (?i)
    (?:
        unverzüglich
        |ohne\s+schuldhaftes\s+Zögern
        |zum\s+nächstmöglichen\s+Zeitpunkt
        |innerhalb\s+der\s+gesetzlichen\s+Frist
        |fristgerecht
        |fristwahrend
        |rechtzeitig
    )
    """,
    re.VERBOSE,
)


class DeterministicDeadlineExtractor(DeadlineExtractor):
    """Deterministic, rule-based deadline candidate extractor.

    Pure Python — no external APIs, no ML models, no locale dependency.
    All regex patterns are ReDoS-safe and hard-coded.
    """

    MAX_TEXT_LENGTH: int = MAX_TEXT_LENGTH
    REGEX_TIMEOUT: float = REGEX_TIMEOUT

    def extract(self, text: str, *, document_id: str = "") -> DeadlineExtractionResult:
        """Extract deadline candidates from document text."""
        # Gate 1: Empty text
        if not text.strip():
            return DeadlineExtractionResult(
                document_id=document_id,
                candidates=[],
                warnings=[
                    DeadlineWarning(
                        code=DeadlineWarningCode.LEGAL_CALCULATION_NOT_PERFORMED,
                        message="Es wurde keine rechtliche Frist berechnet.",
                    ),
                    DeadlineWarning(
                        code=DeadlineWarningCode.NO_DEADLINE_CANDIDATE,
                        message="Kein Dokumenttext vorhanden.",
                    ),
                ],
            )

        # Gate 2: Text size limit
        if len(text) > self.MAX_TEXT_LENGTH:
            raise TextTooLargeError(
                f"Der Dokumenttext ist zu groß "
                f"({len(text):,} Zeichen, max. {self.MAX_TEXT_LENGTH:,})."
            )

        # Gate 3: Run with timeout
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._extract_impl, text, document_id)
            try:
                return future.result(timeout=self.REGEX_TIMEOUT)
            except concurrent.futures.TimeoutError as e:
                raise ExtractionTimeoutError(
                    f"Die Fristextraktion hat das Zeitlimit "
                    f"({self.REGEX_TIMEOUT:.0f} s) überschritten."
                ) from e

    def _extract_impl(self, text: str, document_id: str) -> DeadlineExtractionResult:
        """Internal extraction implementation (called with timeout wrapper)."""
        candidates: list[DeadlineCandidate] = []

        # R1: Numeric dates
        candidates.extend(self._extract_numeric_dates(text))

        # R2: Written-out month dates
        candidates.extend(self._extract_textual_dates(text))

        # R3: Relative numeric periods
        candidates.extend(self._extract_relative_numeric(text))

        # R4: Relative article periods
        candidates.extend(self._extract_relative_article(text))

        # R6: Qualitative references
        candidates.extend(self._extract_qualitative(text))

        # Deduplicate overlapping matches (keep first by start_offset)
        candidates = self._deduplicate(candidates)

        # Sort deterministically by start_offset
        candidates.sort(key=lambda c: c.start_offset)

        # Generate warnings
        warnings = self._generate_warnings(candidates)

        return DeadlineExtractionResult(
            document_id=document_id,
            candidates=candidates,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # R1: Numeric dates (TT.MM.JJJJ)
    # ------------------------------------------------------------------

    def _extract_numeric_dates(self, text: str) -> list[DeadlineCandidate]:
        """Extract numeric German dates from text."""
        candidates: list[DeadlineCandidate] = []
        for match in _NUMERIC_DATE_RE.finditer(text):
            raw = match.group(0)
            day_str, month_str, year_str = match[1], match[2], match[3]
            try:
                normalized = date(int(year_str), int(month_str), int(day_str))
            except ValueError:
                # Invalid calendar date — skip but don't crash
                continue

            # Check for Fristkontext prefix to extend raw_text
            extended_raw = raw
            extended_start = match.start()
            prefix_match = _FRISTKONTEXT_PREFIX_RE.search(
                text, max(0, match.start() - 40), match.start()
            )
            if prefix_match:
                extended_raw = text[prefix_match.start() : match.end()]
                extended_start = prefix_match.start()

            candidates.append(
                DeadlineCandidate(
                    kind=DeadlineCandidateKind.EXPLICIT_DATE,
                    raw_text=extended_raw.strip(),
                    start_offset=extended_start,
                    end_offset=match.end(),
                    normalized_date=normalized,
                    certainty=DeadlineCertainty.EXACT,
                    rule_id="DEADLINE_DATE_NUMERIC_DE_V1",
                )
            )
        return candidates

    # ------------------------------------------------------------------
    # R2: Written-out month dates
    # ------------------------------------------------------------------

    def _extract_textual_dates(self, text: str) -> list[DeadlineCandidate]:
        """Extract dates with written-out German month names."""
        candidates: list[DeadlineCandidate] = []
        for match in _TEXTUAL_DATE_RE.finditer(text):
            raw = match.group(0)
            day_str = match[1]
            month_name = match[2].lower().rstrip(".")
            year_str = match[3]

            month_num = GERMAN_MONTHS.get(month_name)
            if month_num is None:
                continue

            try:
                normalized = date(int(year_str), month_num, int(day_str))
            except ValueError:
                continue  # Invalid date

            # Extend with Fristkontext prefix
            extended_raw = raw
            extended_start = match.start()
            prefix_match = _FRISTKONTEXT_PREFIX_RE.search(
                text, max(0, match.start() - 40), match.start()
            )
            if prefix_match:
                extended_raw = text[prefix_match.start() : match.end()]
                extended_start = prefix_match.start()

            candidates.append(
                DeadlineCandidate(
                    kind=DeadlineCandidateKind.EXPLICIT_DATE,
                    raw_text=extended_raw.strip(),
                    start_offset=extended_start,
                    end_offset=match.end(),
                    normalized_date=normalized,
                    certainty=DeadlineCertainty.EXACT,
                    rule_id="DEADLINE_DATE_TEXTUAL_DE_V1",
                )
            )
        return candidates

    # ------------------------------------------------------------------
    # R3: Relative numeric periods
    # ------------------------------------------------------------------

    def _extract_relative_numeric(self, text: str) -> list[DeadlineCandidate]:
        """Extract relative period expressions with numeric amounts."""
        candidates: list[DeadlineCandidate] = []
        for match in _RELATIVE_NUMERIC_RE.finditer(text):
            raw = match.group(0)
            # Capturing groups: numeric patterns have (amount, unit) pairs
            # Determine which groups matched
            groups = match.groups()
            amount: int | None = None
            unit: str | None = None

            # Try the drei alternation positions
            if groups[0] is not None:  # "innerhalb von N Einheit"
                amount = int(groups[0])
                unit = groups[1].lower() if groups[1] else None
            elif groups[2] is not None:  # "binnen N Einheit"
                amount = int(groups[2])
                unit = groups[3].lower() if groups[3] else None

            # Map unit to canonical form
            canonical_unit = GERMAN_UNIT_MAP.get(unit or "")
            if canonical_unit is None:
                canonical_unit = unit.capitalize() if unit else ""

            candidates.append(
                DeadlineCandidate(
                    kind=DeadlineCandidateKind.RELATIVE_PERIOD,
                    raw_text=raw.strip(),
                    start_offset=match.start(),
                    end_offset=match.end(),
                    amount=amount,
                    unit=canonical_unit,
                    reference_required=True,
                    certainty=DeadlineCertainty.UNRESOLVED,
                    rule_id="DEADLINE_RELATIVE_NUMERIC_DE_V1",
                )
            )
        return candidates

    # ------------------------------------------------------------------
    # R4: Relative article periods
    # ------------------------------------------------------------------

    def _extract_relative_article(self, text: str) -> list[DeadlineCandidate]:
        """Extract relative period expressions with article (singular)."""
        candidates: list[DeadlineCandidate] = []
        for match in _RELATIVE_ARTICLE_RE.finditer(text):
            raw = match.group(0)
            groups = match.groups()
            unit = groups[0] if groups[0] is not None else groups[1]

            canonical_unit = GERMAN_UNIT_MAP.get((unit or "").lower(), "")
            if not canonical_unit and unit:
                canonical_unit = unit.capitalize()

            candidates.append(
                DeadlineCandidate(
                    kind=DeadlineCandidateKind.RELATIVE_PERIOD,
                    raw_text=raw.strip(),
                    start_offset=match.start(),
                    end_offset=match.end(),
                    amount=1,
                    unit=canonical_unit,
                    reference_required=True,
                    certainty=DeadlineCertainty.UNRESOLVED,
                    rule_id="DEADLINE_RELATIVE_ARTICLE_DE_V1",
                )
            )
        return candidates

    # ------------------------------------------------------------------
    # R6: Qualitative references
    # ------------------------------------------------------------------

    def _extract_qualitative(self, text: str) -> list[DeadlineCandidate]:
        """Extract qualitative deadline references."""
        candidates: list[DeadlineCandidate] = []
        for match in _QUALITATIVE_RE.finditer(text):
            raw = match.group(0)
            candidates.append(
                DeadlineCandidate(
                    kind=DeadlineCandidateKind.QUALITATIVE_REFERENCE,
                    raw_text=raw.strip(),
                    start_offset=match.start(),
                    end_offset=match.end(),
                    reference_required=True,
                    certainty=DeadlineCertainty.UNRESOLVED,
                    rule_id="DEADLINE_QUALITATIVE_DE_V1",
                )
            )
        return candidates

    # ------------------------------------------------------------------
    # Deduplication and Warning Generation
    # ------------------------------------------------------------------

    @staticmethod
    def _deduplicate(candidates: list[DeadlineCandidate]) -> list[DeadlineCandidate]:
        """Remove candidates with overlapping offsets.

        When two candidates share the same start_offset, keep the first one
        (which typically has richer information like the prefix).
        """
        if len(candidates) <= 1:
            return candidates

        seen_offsets: set[int] = set()
        unique: list[DeadlineCandidate] = []
        for c in sorted(candidates, key=lambda x: (x.start_offset, x.end_offset)):
            if c.start_offset not in seen_offsets:
                seen_offsets.add(c.start_offset)
                unique.append(c)
        return unique

    @staticmethod
    def _generate_warnings(
        candidates: list[DeadlineCandidate],
    ) -> list[DeadlineWarning]:
        """Generate structured warnings for the extraction result."""
        warnings: list[DeadlineWarning] = []

        # Mandatory: legal calculation not performed
        warnings.append(
            DeadlineWarning(
                code=DeadlineWarningCode.LEGAL_CALCULATION_NOT_PERFORMED,
                message="Es wurde keine rechtliche Frist berechnet. Nur Textstellen erkannt.",
            )
        )

        # No candidates found
        if len(candidates) == 0:
            warnings.append(
                DeadlineWarning(
                    code=DeadlineWarningCode.NO_DEADLINE_CANDIDATE,
                    message="Keine Fristkandidaten im Text gefunden.",
                )
            )

        # Multiple candidates
        if len(candidates) > 1:
            warnings.append(
                DeadlineWarning(
                    code=DeadlineWarningCode.MULTIPLE_DEADLINE_CANDIDATES,
                    message=f"{len(candidates)} Fristkandidaten gefunden. "
                    "Manuelle Prüfung der Priorisierung erforderlich.",
                )
            )

        # Relative reference required
        has_relative = any(c.reference_required for c in candidates)
        if has_relative:
            warnings.append(
                DeadlineWarning(
                    code=DeadlineWarningCode.RELATIVE_REFERENCE_REQUIRED,
                    message="Mindestens ein Fristkandidat ist relativ und "
                    "benötigt einen externen Bezugspunkt (z.B. Zustelldatum).",
                )
            )

        return warnings


# ---------------------------------------------------------------------------
# M5-specific exceptions
# ---------------------------------------------------------------------------


class TextTooLargeError(ValueError):
    """Raised when document text exceeds the maximum allowed length."""


class ExtractionTimeoutError(TimeoutError):
    """Raised when deadline extraction exceeds the time limit."""
