"""Unit tests for deadline domain models."""

from datetime import date

import pytest

from private_legal_navigator.domain.deadline import (
    DeadlineCandidate,
    DeadlineCandidateKind,
    DeadlineCertainty,
    DeadlineExtractionResult,
    DeadlineWarning,
    DeadlineWarningCode,
)


class TestDeadlineCandidateKind:
    """Enum values are stable."""

    def test_explicit_date_value(self) -> None:
        assert DeadlineCandidateKind.EXPLICIT_DATE == "explicit_date"

    def test_relative_period_value(self) -> None:
        assert DeadlineCandidateKind.RELATIVE_PERIOD == "relative_period"

    def test_qualitative_reference_value(self) -> None:
        assert DeadlineCandidateKind.QUALITATIVE_REFERENCE == "qualitative_reference"


class TestDeadlineCertainty:
    """Enum values are stable."""

    def test_exact_value(self) -> None:
        assert DeadlineCertainty.EXACT == "exact"

    def test_unresolved_value(self) -> None:
        assert DeadlineCertainty.UNRESOLVED == "unresolved"

    def test_ambiguous_value(self) -> None:
        assert DeadlineCertainty.AMBIGUOUS == "ambiguous"


class TestDeadlineWarningCode:
    """Warning codes are stable and must not change between releases."""

    def test_all_codes_defined(self) -> None:
        expected = {
            "LEGAL_CALCULATION_NOT_PERFORMED",
            "NO_DEADLINE_CANDIDATE",
            "MULTIPLE_DEADLINE_CANDIDATES",
            "RELATIVE_REFERENCE_REQUIRED",
            "AMBIGUOUS_DATE",
        }
        actual = set(DeadlineWarningCode.__members__.keys())
        assert actual == expected


class TestDeadlineCandidate:
    """Post-init validation enforces invariants."""

    def test_valid_explicit_date(self) -> None:
        c = DeadlineCandidate(
            kind=DeadlineCandidateKind.EXPLICIT_DATE,
            raw_text="31.07.2026",
            start_offset=0,
            end_offset=10,
            normalized_date=date(2026, 7, 31),
            rule_id="DEADLINE_DATE_NUMERIC_DE_V1",
        )
        assert c.kind == DeadlineCandidateKind.EXPLICIT_DATE
        assert c.normalized_date == date(2026, 7, 31)

    def test_valid_relative_period(self) -> None:
        c = DeadlineCandidate(
            kind=DeadlineCandidateKind.RELATIVE_PERIOD,
            raw_text="innerhalb von zwei Wochen",
            start_offset=0,
            end_offset=25,
            amount=2,
            unit="Woche",
            reference_required=True,
            certainty=DeadlineCertainty.UNRESOLVED,
            rule_id="DEADLINE_RELATIVE_NUMERIC_DE_V1",
        )
        assert c.reference_required is True
        assert c.amount == 2

    def test_negative_start_offset_raises(self) -> None:
        with pytest.raises(ValueError, match="start_offset must be >= 0"):
            DeadlineCandidate(
                kind=DeadlineCandidateKind.EXPLICIT_DATE,
                raw_text="test",
                start_offset=-1,
                end_offset=10,
                normalized_date=date(2026, 7, 31),
                rule_id="R1",
            )

    def test_end_before_start_raises(self) -> None:
        with pytest.raises(ValueError, match="end_offset must be >= start_offset"):
            DeadlineCandidate(
                kind=DeadlineCandidateKind.EXPLICIT_DATE,
                raw_text="test",
                start_offset=10,
                end_offset=5,
                normalized_date=date(2026, 7, 31),
                rule_id="R1",
            )

    def test_explicit_date_without_normalized_date_raises(self) -> None:
        with pytest.raises(ValueError, match="must have normalized_date"):
            DeadlineCandidate(
                kind=DeadlineCandidateKind.EXPLICIT_DATE,
                raw_text="test",
                start_offset=0,
                end_offset=10,
                rule_id="R1",
            )

    def test_relative_without_amount_raises(self) -> None:
        with pytest.raises(ValueError, match="must have amount and unit"):
            DeadlineCandidate(
                kind=DeadlineCandidateKind.RELATIVE_PERIOD,
                raw_text="test",
                start_offset=0,
                end_offset=10,
                amount=None,
                unit="Woche",
                reference_required=True,
                certainty=DeadlineCertainty.UNRESOLVED,
                rule_id="R3",
            )

    def test_relative_without_unit_raises(self) -> None:
        with pytest.raises(ValueError, match="must have amount and unit"):
            DeadlineCandidate(
                kind=DeadlineCandidateKind.RELATIVE_PERIOD,
                raw_text="test",
                start_offset=0,
                end_offset=10,
                amount=2,
                unit=None,
                reference_required=True,
                certainty=DeadlineCertainty.UNRESOLVED,
                rule_id="R3",
            )

    def test_qualitative_reference_valid(self) -> None:
        c = DeadlineCandidate(
            kind=DeadlineCandidateKind.QUALITATIVE_REFERENCE,
            raw_text="unverzüglich",
            start_offset=0,
            end_offset=12,
            reference_required=True,
            certainty=DeadlineCertainty.UNRESOLVED,
            rule_id="DEADLINE_QUALITATIVE_DE_V1",
        )
        assert c.kind == DeadlineCandidateKind.QUALITATIVE_REFERENCE
        assert c.normalized_date is None


class TestDeadlineWarning:
    """Warning struct is straightforward."""

    def test_warning_creation(self) -> None:
        w = DeadlineWarning(
            code=DeadlineWarningCode.LEGAL_CALCULATION_NOT_PERFORMED,
            message="Keine rechtliche Frist berechnet.",
        )
        assert w.code == DeadlineWarningCode.LEGAL_CALCULATION_NOT_PERFORMED
        assert "rechtliche" in w.message


class TestDeadlineExtractionResult:
    """Result container holds candidates, warnings, and review flag."""

    def test_empty_result(self) -> None:
        r = DeadlineExtractionResult(document_id="abc")
        assert r.document_id == "abc"
        assert r.candidates == []
        assert r.warnings == []
        assert r.human_review_required is True

    def test_human_review_always_true_by_default(self) -> None:
        r = DeadlineExtractionResult(document_id="x")
        assert r.human_review_required is True

    def test_result_with_candidates(self) -> None:
        c = DeadlineCandidate(
            kind=DeadlineCandidateKind.EXPLICIT_DATE,
            raw_text="31.07.2026",
            start_offset=0,
            end_offset=10,
            normalized_date=date(2026, 7, 31),
            rule_id="R1",
        )
        w = DeadlineWarning(
            code=DeadlineWarningCode.LEGAL_CALCULATION_NOT_PERFORMED,
            message="test",
        )
        r = DeadlineExtractionResult(
            document_id="doc-1",
            candidates=[c],
            warnings=[w],
        )
        assert len(r.candidates) == 1
        assert len(r.warnings) == 1
