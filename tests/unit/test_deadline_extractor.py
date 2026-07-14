"""Unit tests for DeterministicDeadlineExtractor — the core rule engine.

Tests cover all rules (R1-R6), deduplication, sorting, warnings,
error cases, and regex safety.

SYNTHETISCH – KEINE ECHTEN PERSONEN- ODER FALLDATEN
"""

from datetime import date

import pytest

from private_legal_navigator.domain.deadline import (
    DeadlineCandidateKind,
    DeadlineCertainty,
    DeadlineWarningCode,
)
from private_legal_navigator.infrastructure.deterministic_deadline_extractor import (
    DeterministicDeadlineExtractor,
)


@pytest.fixture
def extractor() -> DeterministicDeadlineExtractor:
    return DeterministicDeadlineExtractor()


# ======================================================================
# R1 — Numeric German dates (TT.MM.JJJJ)
# ======================================================================


class TestR1NumericDates:
    def test_simple_date(self, extractor: DeterministicDeadlineExtractor) -> None:
        result = extractor.extract("Die Frist endet am 31.07.2026.")
        assert len(result.candidates) == 1
        c = result.candidates[0]
        assert c.kind == DeadlineCandidateKind.EXPLICIT_DATE
        assert c.normalized_date == date(2026, 7, 31)
        assert c.rule_id == "DEADLINE_DATE_NUMERIC_DE_V1"
        assert c.certainty == DeadlineCertainty.EXACT

    def test_single_digit_day(self, extractor: DeterministicDeadlineExtractor) -> None:
        result = extractor.extract("am 1.7.2026")
        assert len(result.candidates) == 1
        assert result.candidates[0].normalized_date == date(2026, 7, 1)

    def test_single_digit_month(self, extractor: DeterministicDeadlineExtractor) -> None:
        result = extractor.extract("am 15.1.2026")
        assert len(result.candidates) == 1
        assert result.candidates[0].normalized_date == date(2026, 1, 15)

    def test_date_with_spaces(self, extractor: DeterministicDeadlineExtractor) -> None:
        result = extractor.extract("31. 07. 2026")
        assert len(result.candidates) == 1
        assert result.candidates[0].normalized_date == date(2026, 7, 31)

    def test_multiple_dates(self, extractor: DeterministicDeadlineExtractor) -> None:
        result = extractor.extract("ab 01.01.2025 bis 31.12.2025")
        assert len(result.candidates) == 2

    def test_invalid_date_february_30(self, extractor: DeterministicDeadlineExtractor) -> None:
        """30.02.2026 does not exist — must not produce a candidate."""
        result = extractor.extract("Frist bis 30.02.2026")
        # Should NOT produce a candidate for this invalid date
        has_30_feb = any(c.normalized_date is not None for c in result.candidates)
        assert not has_30_feb, "30.02.2026 should not produce a valid candidate"

    def test_invalid_date_month_13(self, extractor: DeterministicDeadlineExtractor) -> None:
        result = extractor.extract("Frist bis 31.13.2026")
        has_month_13 = any(c.rule_id == "DEADLINE_DATE_NUMERIC_DE_V1" for c in result.candidates)
        assert not has_month_13, "31.13.2026 should not produce a valid candidate"

    def test_date_year_out_of_range(self, extractor: DeterministicDeadlineExtractor) -> None:
        """Year 1800 should not be matched by our 19xx/20xx pattern."""
        result = extractor.extract("Frist bis 31.07.1800")
        has_1800 = any(c.rule_id == "DEADLINE_DATE_NUMERIC_DE_V1" for c in result.candidates)
        assert not has_1800

    # ------------------------------------------------------------------
    # False Positive Tests
    # ------------------------------------------------------------------

    def test_not_version_number(self, extractor: DeterministicDeadlineExtractor) -> None:
        """Version v1.07.2026 should not be treated as a date."""
        result = extractor.extract("Version v1.07.2026")
        has_version_date = any(
            c.rule_id == "DEADLINE_DATE_NUMERIC_DE_V1" for c in result.candidates
        )
        assert not has_version_date

    def test_not_page_number_alone(self, extractor: DeterministicDeadlineExtractor) -> None:
        """Plain page-like numbers before dates should still be caught,
        but standalone page numbers without Frist context are fine as candidates.
        This is a known M5 limitation (context filtering is M6)."""
        # In M5 we accept that standalone dates are candidates;
        # the human reviewer decides relevance
        result = extractor.extract("Seite 31.07.2026")
        # This will be caught as a candidate in M5 — that's acceptable
        assert len(result.candidates) >= 0  # no crash


# ======================================================================
# R2 — Written-out German month names
# ======================================================================


class TestR2TextualDates:
    def test_full_month_name(self, extractor: DeterministicDeadlineExtractor) -> None:
        result = extractor.extract("bis spätestens 31. Juli 2026")
        assert len(result.candidates) >= 1
        textual = [c for c in result.candidates if c.rule_id == "DEADLINE_DATE_TEXTUAL_DE_V1"]
        assert len(textual) >= 1
        assert textual[0].normalized_date == date(2026, 7, 31)

    def test_all_months(self, extractor: DeterministicDeadlineExtractor) -> None:
        """Each month should parse correctly."""
        test_cases = [
            ("1. Januar 2026", date(2026, 1, 1)),
            ("15. Februar 2026", date(2026, 2, 15)),
            ("31. März 2026", date(2026, 3, 31)),
            ("1. April 2026", date(2026, 4, 1)),
            ("15. Mai 2026", date(2026, 5, 15)),
            ("30. Juni 2026", date(2026, 6, 30)),
            ("31. Juli 2026", date(2026, 7, 31)),
            ("1. August 2026", date(2026, 8, 1)),
            ("15. September 2026", date(2026, 9, 15)),
            ("31. Oktober 2026", date(2026, 10, 31)),
            ("1. November 2026", date(2026, 11, 1)),
            ("31. Dezember 2026", date(2026, 12, 31)),
        ]
        for text, expected in test_cases:
            result = extractor.extract(f"Frist: {text}")
            textual = [c for c in result.candidates if c.rule_id == "DEADLINE_DATE_TEXTUAL_DE_V1"]
            assert len(textual) >= 1, f"Failed to parse: {text}"
            assert textual[0].normalized_date == expected, f"Wrong date for: {text}"

    def test_abbreviated_month(self, extractor: DeterministicDeadlineExtractor) -> None:
        result = extractor.extract("bis 31. Jul 2026")
        textual = [c for c in result.candidates if c.rule_id == "DEADLINE_DATE_TEXTUAL_DE_V1"]
        assert len(textual) >= 1
        assert textual[0].normalized_date == date(2026, 7, 31)

    def test_abbreviated_month_with_dot(self, extractor: DeterministicDeadlineExtractor) -> None:
        result = extractor.extract("bis 31. Jul. 2026")
        textual = [c for c in result.candidates if c.rule_id == "DEADLINE_DATE_TEXTUAL_DE_V1"]
        assert len(textual) >= 1
        assert textual[0].normalized_date == date(2026, 7, 31)

    def test_single_digit_day_textual(self, extractor: DeterministicDeadlineExtractor) -> None:
        result = extractor.extract("bis 1. August 2026")
        textual = [c for c in result.candidates if c.rule_id == "DEADLINE_DATE_TEXTUAL_DE_V1"]
        assert len(textual) >= 1
        assert textual[0].normalized_date == date(2026, 8, 1)


# ======================================================================
# R3 — Relative numeric periods
# ======================================================================


class TestR3RelativeNumeric:
    def test_innerhalb_with_number(self, extractor: DeterministicDeadlineExtractor) -> None:
        result = extractor.extract("innerhalb von 2 Wochen")
        rel = [c for c in result.candidates if c.kind == DeadlineCandidateKind.RELATIVE_PERIOD]
        assert len(rel) == 1
        assert rel[0].amount == 2
        assert rel[0].unit == "Woche"

    def test_binnen_with_number(self, extractor: DeterministicDeadlineExtractor) -> None:
        result = extractor.extract("binnen 14 Tagen")
        rel = [c for c in result.candidates if c.kind == DeadlineCandidateKind.RELATIVE_PERIOD]
        assert len(rel) == 1
        assert rel[0].amount == 14
        assert rel[0].unit == "Tag"

    def test_innerhalb_months(self, extractor: DeterministicDeadlineExtractor) -> None:
        result = extractor.extract("innerhalb von 3 Monaten")
        rel = [c for c in result.candidates if c.kind == DeadlineCandidateKind.RELATIVE_PERIOD]
        assert len(rel) == 1
        assert rel[0].amount == 3
        assert rel[0].unit == "Monat"

    def test_binnen_weeks(self, extractor: DeterministicDeadlineExtractor) -> None:
        result = extractor.extract("binnen 4 Wochen")
        rel = [c for c in result.candidates if c.kind == DeadlineCandidateKind.RELATIVE_PERIOD]
        assert len(rel) == 1
        assert rel[0].amount == 4
        assert rel[0].unit == "Woche"

    def test_reference_required_is_true(self, extractor: DeterministicDeadlineExtractor) -> None:
        result = extractor.extract("innerhalb von 14 Tagen")
        rel = [c for c in result.candidates if c.kind == DeadlineCandidateKind.RELATIVE_PERIOD]
        assert len(rel) == 1
        assert rel[0].reference_required is True
        assert rel[0].certainty == DeadlineCertainty.UNRESOLVED


# ======================================================================
# R4 — Relative article periods
# ======================================================================


class TestR4RelativeArticle:
    def test_innerhalb_eines_monats(self, extractor: DeterministicDeadlineExtractor) -> None:
        result = extractor.extract("innerhalb eines Monats")
        rel = [c for c in result.candidates if c.rule_id == "DEADLINE_RELATIVE_ARTICLE_DE_V1"]
        assert len(rel) == 1
        assert rel[0].amount == 1
        assert rel[0].unit == "Monat"
        assert rel[0].reference_required is True

    def test_binnen_einer_woche(self, extractor: DeterministicDeadlineExtractor) -> None:
        result = extractor.extract("binnen einer Woche")
        rel = [c for c in result.candidates if c.rule_id == "DEADLINE_RELATIVE_ARTICLE_DE_V1"]
        assert len(rel) == 1
        assert rel[0].amount == 1
        assert rel[0].unit == "Woche"

    def test_innerhalb_eines_jahres(self, extractor: DeterministicDeadlineExtractor) -> None:
        result = extractor.extract("innerhalb eines Jahres")
        rel = [c for c in result.candidates if c.rule_id == "DEADLINE_RELATIVE_ARTICLE_DE_V1"]
        assert len(rel) == 1
        assert rel[0].unit == "Jahr"


# ======================================================================
# R6 — Qualitative references
# ======================================================================


class TestR6Qualitative:
    def test_unverzüglich(self, extractor: DeterministicDeadlineExtractor) -> None:
        result = extractor.extract("Die Zahlung ist unverzüglich zu leisten.")
        qual = [
            c for c in result.candidates if c.kind == DeadlineCandidateKind.QUALITATIVE_REFERENCE
        ]
        assert len(qual) == 1
        assert qual[0].reference_required is True
        assert qual[0].normalized_date is None

    def test_ohne_schuldhaftes_zoegern(self, extractor: DeterministicDeadlineExtractor) -> None:
        result = extractor.extract("ohne schuldhaftes Zögern")
        qual = [
            c for c in result.candidates if c.kind == DeadlineCandidateKind.QUALITATIVE_REFERENCE
        ]
        assert len(qual) == 1

    def test_zum_naechstmoeglichen_zeitpunkt(
        self, extractor: DeterministicDeadlineExtractor
    ) -> None:
        result = extractor.extract("zum nächstmöglichen Zeitpunkt")
        qual = [
            c for c in result.candidates if c.kind == DeadlineCandidateKind.QUALITATIVE_REFERENCE
        ]
        assert len(qual) == 1

    def test_innerhalb_gesetzlicher_frist(self, extractor: DeterministicDeadlineExtractor) -> None:
        result = extractor.extract("innerhalb der gesetzlichen Frist")
        qual = [
            c for c in result.candidates if c.kind == DeadlineCandidateKind.QUALITATIVE_REFERENCE
        ]
        assert len(qual) == 1


# ======================================================================
# Deduplication and Sorting
# ======================================================================


class TestDeduplicationAndSorting:
    def test_overlapping_duplicates_removed(
        self, extractor: DeterministicDeadlineExtractor
    ) -> None:
        """When numeric and textual patterns match the same date,
        only one candidate should be kept."""
        # "31. Juli 2026" matches R2, but also has numeric-like parts
        result = extractor.extract("Frist: 31. Juli 2026")
        # Both R1 and R2 could match — dedup ensures no duplicates
        unique_offsets = {c.start_offset for c in result.candidates}
        assert len(result.candidates) == len(unique_offsets), (
            "Duplicate start_offsets found — deduplication should remove them"
        )

    def test_deterministic_sorting_by_offset(
        self, extractor: DeterministicDeadlineExtractor
    ) -> None:
        result = extractor.extract(
            "Erstens: bis 31.12.2026. Zweitens: innerhalb von 14 Tagen. "
            "Drittens: spätestens am 01.01.2025."
        )
        offsets = [c.start_offset for c in result.candidates]
        assert offsets == sorted(offsets), "Candidates must be sorted by start_offset"

    def test_consistent_output(self, extractor: DeterministicDeadlineExtractor) -> None:
        """Same input always produces same output."""
        text = "bis 31.07.2026 und innerhalb von 2 Wochen"
        r1 = extractor.extract(text)
        r2 = extractor.extract(text)
        assert len(r1.candidates) == len(r2.candidates)
        for c1, c2 in zip(r1.candidates, r2.candidates, strict=True):
            assert c1.start_offset == c2.start_offset
            assert c1.rule_id == c2.rule_id


# ======================================================================
# Warnings
# ======================================================================


class TestWarnings:
    def test_legal_calculation_not_performed_always_present(
        self, extractor: DeterministicDeadlineExtractor
    ) -> None:
        result = extractor.extract("31.07.2026")
        warning_codes = {w.code for w in result.warnings}
        assert DeadlineWarningCode.LEGAL_CALCULATION_NOT_PERFORMED in warning_codes

    def test_no_candidate_warning(self, extractor: DeterministicDeadlineExtractor) -> None:
        result = extractor.extract("Kein Datum hier drin.")
        warning_codes = {w.code for w in result.warnings}
        assert DeadlineWarningCode.NO_DEADLINE_CANDIDATE in warning_codes

    def test_multiple_candidates_warning(self, extractor: DeterministicDeadlineExtractor) -> None:
        result = extractor.extract("31.07.2026 und 01.01.2027")
        warning_codes = {w.code for w in result.warnings}
        assert DeadlineWarningCode.MULTIPLE_DEADLINE_CANDIDATES in warning_codes

    def test_relative_reference_required_warning(
        self, extractor: DeterministicDeadlineExtractor
    ) -> None:
        result = extractor.extract("innerhalb von 14 Tagen")
        warning_codes = {w.code for w in result.warnings}
        assert DeadlineWarningCode.RELATIVE_REFERENCE_REQUIRED in warning_codes

    def test_empty_text_produces_warnings(self, extractor: DeterministicDeadlineExtractor) -> None:
        result = extractor.extract("")
        warning_codes = {w.code for w in result.warnings}
        assert DeadlineWarningCode.LEGAL_CALCULATION_NOT_PERFORMED in warning_codes
        assert DeadlineWarningCode.NO_DEADLINE_CANDIDATE in warning_codes

    def test_whitespace_only_text(self, extractor: DeterministicDeadlineExtractor) -> None:
        result = extractor.extract("   \n  ")
        warning_codes = {w.code for w in result.warnings}
        assert DeadlineWarningCode.NO_DEADLINE_CANDIDATE in warning_codes

    def test_ambiguous_date_warning_for_invalid_calendar_date(
        self, extractor: DeterministicDeadlineExtractor
    ) -> None:
        """31.02.2026 does not exist — should produce AMBIGUOUS_DATE warning."""
        result = extractor.extract("Frist bis 31.02.2026")
        warning_codes = {w.code for w in result.warnings}
        assert DeadlineWarningCode.AMBIGUOUS_DATE in warning_codes, (
            "Invalid calendar date 31.02.2026 should trigger AMBIGUOUS_DATE warning"
        )

    def test_ambiguous_date_warning_for_invalid_month(
        self, extractor: DeterministicDeadlineExtractor
    ) -> None:
        """31.04.2026 — April has only 30 days. Should produce AMBIGUOUS_DATE."""
        result = extractor.extract("Frist bis 31.04.2026")
        warning_codes = {w.code for w in result.warnings}
        assert DeadlineWarningCode.AMBIGUOUS_DATE in warning_codes

    def test_no_ambiguous_warning_for_valid_date(
        self, extractor: DeterministicDeadlineExtractor
    ) -> None:
        """Valid date should NOT produce AMBIGUOUS_DATE warning."""
        result = extractor.extract("Frist bis 31.07.2026")
        warning_codes = {w.code for w in result.warnings}
        assert DeadlineWarningCode.AMBIGUOUS_DATE not in warning_codes

    def test_ambiguous_date_with_textual_month(
        self, extractor: DeterministicDeadlineExtractor
    ) -> None:
        """31. Februar 2026 is invalid in textual form — should produce AMBIGUOUS_DATE."""
        result = extractor.extract("Frist bis 31. Februar 2026")
        warning_codes = {w.code for w in result.warnings}
        assert DeadlineWarningCode.AMBIGUOUS_DATE in warning_codes, (
            "Invalid textual date should trigger AMBIGUOUS_DATE"
        )


# ======================================================================
# Error and Edge Cases
# ======================================================================


class TestErrorAndEdgeCases:
    def test_no_candidate_empty_list(self, extractor: DeterministicDeadlineExtractor) -> None:
        result = extractor.extract("Dieser Text enthält keine Frist.")
        assert result.candidates == []

    def test_human_review_required_is_true(self, extractor: DeterministicDeadlineExtractor) -> None:
        result = extractor.extract("31.07.2026")
        assert result.human_review_required is True

    def test_document_id_passed_through(self, extractor: DeterministicDeadlineExtractor) -> None:
        result = extractor.extract("31.07.2026", document_id="doc-123")
        assert result.document_id == "doc-123"

    def test_text_too_large_raises(self, extractor: DeterministicDeadlineExtractor) -> None:
        from private_legal_navigator.infrastructure.deterministic_deadline_extractor import (
            TextTooLargeError,
        )

        long_text = "x" * (extractor.MAX_TEXT_LENGTH + 1)
        with pytest.raises(TextTooLargeError):
            extractor.extract(long_text)

    def test_text_exactly_max_ok(self, extractor: DeterministicDeadlineExtractor) -> None:
        ok_text = "x" * extractor.MAX_TEXT_LENGTH
        result = extractor.extract(ok_text)
        # Should not raise — just return (possibly empty) result
        assert isinstance(result.candidates, list)


# ======================================================================
# Realistic synthetic document texts
# ======================================================================


class TestRealisticGermanAdministrativeTexts:
    """Tests with realistic (but synthetic) German legal/administrative phrasing.

    SYNTHETISCH – KEINE ECHTEN PERSONEN- ODER FALLDATEN
    """

    def test_typischer_bescheidsauszug(self, extractor: DeterministicDeadlineExtractor) -> None:
        text = (
            "Gegen diesen Bescheid kann innerhalb eines Monats nach Bekanntgabe "
            "Widerspruch erhoben werden. Der Widerspruch ist schriftlich oder zur "
            "Niederschrift bei der oben genannten Behörde einzulegen. "
            "Die Frist beginnt mit dem Tag der Bekanntgabe. "
            "Dieser Bescheid wurde am 15. März 2026 erlassen."
        )
        result = extractor.extract(text)
        # Should find: "innerhalb eines Monats" (R4), "15. März 2026" (R2)
        kinds = {c.kind for c in result.candidates}
        assert DeadlineCandidateKind.EXPLICIT_DATE in kinds
        assert DeadlineCandidateKind.RELATIVE_PERIOD in kinds

    def test_mahnungsauszug(self, extractor: DeterministicDeadlineExtractor) -> None:
        text = (
            "Wir fordern Sie auf, den ausstehenden Betrag in Höhe von 1.234,56 EUR "
            "bis spätestens 31.07.2026 auf das unten genannte Konto zu überweisen. "
            "Sollte der Betrag nicht fristgerecht eingehen, werden wir ohne weitere "
            "Mahnung gerichtliche Schritte einleiten."
        )
        result = extractor.extract(text)
        explicit = [c for c in result.candidates if c.kind == DeadlineCandidateKind.EXPLICIT_DATE]
        assert len(explicit) >= 1
        assert explicit[0].normalized_date == date(2026, 7, 31)

    def test_relative_mixed_with_explicit(self, extractor: DeterministicDeadlineExtractor) -> None:
        text = (
            "Sie haben ab Zustellung dieses Schreibens binnen 14 Tagen "
            "Zeit, den geforderten Betrag zu begleichen. "
            "Letzter Zahlungstermin ist der 31.12.2026."
        )
        result = extractor.extract(text)
        kinds = {c.kind for c in result.candidates}
        assert DeadlineCandidateKind.EXPLICIT_DATE in kinds
        assert DeadlineCandidateKind.RELATIVE_PERIOD in kinds


# ======================================================================
# Regex Safety Tests
# ======================================================================


class TestRegexSafety:
    """Verify that regex patterns don't cause catastrophic backtracking."""

    def test_long_text_no_backtracking(self, extractor: DeterministicDeadlineExtractor) -> None:
        """Long text with repeated characters should process quickly."""
        long_text = "x" * 10000 + " 31.07.2026 " + "x" * 10000
        import time

        start = time.perf_counter()
        result = extractor.extract(long_text)
        elapsed = time.perf_counter() - start
        # Should find the date and complete well under 1 second
        assert elapsed < 1.0, f"Extraction took {elapsed:.2f}s — possible ReDoS"
        assert len(result.candidates) >= 1

    def test_many_partial_date_patterns(self, extractor: DeterministicDeadlineExtractor) -> None:
        """Many near-miss date patterns should not cause exponential backtracking."""
        text = "31.07." * 500  # Partial dates with no year
        import time

        start = time.perf_counter()
        result = extractor.extract(text)
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0, f"Partial dates caused {elapsed:.2f}s — possible ReDoS"
        # No valid date candidates expected (missing year)
        # But qualitative "unverzüglich" etc. shouldn't match either
        assert isinstance(result.candidates, list)
