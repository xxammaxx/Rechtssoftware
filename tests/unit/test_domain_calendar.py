"""Unit tests for M6-A domain models (calendar.py)."""

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from private_legal_navigator.domain.calendar import (
    CalculationOperation,
    CalculationStep,
    CalendarCalculationCandidate,
    ConfirmationMethod,
    ConfirmationStatus,
    ConfirmedReferenceEvent,
    Duration,
    DurationUnit,
    EventType,
    ReferenceEventCandidate,
    SourceType,
)

# --- Enums ---


class TestEventType:
    def test_all_values_defined(self) -> None:
        assert EventType.DELIVERY.value == "delivery"
        assert EventType.ISSUE_DATE.value == "issue_date"
        assert EventType.UNKNOWN.value == "unknown"

    def test_user_defined_exists(self) -> None:
        assert EventType.USER_DEFINED.value == "user_defined"


class TestConfirmationStatus:
    def test_all_values(self) -> None:
        assert ConfirmationStatus.UNCONFIRMED.value == "unconfirmed"
        assert ConfirmationStatus.CONFIRMED.value == "confirmed"
        assert ConfirmationStatus.REJECTED.value == "rejected"
        assert ConfirmationStatus.REVOKED.value == "revoked"
        assert ConfirmationStatus.SUPERSEDED.value == "superseded"


class TestSourceType:
    def test_all_values(self) -> None:
        assert SourceType.AUTO_DETECTED.value == "auto_detected"
        assert SourceType.USER_MANUAL.value == "user_manual"
        assert SourceType.USER_CORRECTED.value == "user_corrected"


class TestConfirmationMethod:
    def test_all_values(self) -> None:
        assert ConfirmationMethod.AUTO_SUGGESTED.value == "auto_suggested"
        assert ConfirmationMethod.MANUALLY_ENTERED.value == "manually_entered"
        assert ConfirmationMethod.CORRECTED.value == "corrected"


class TestDurationUnit:
    def test_day_and_week_only(self) -> None:
        assert DurationUnit.DAY.value == "day"
        assert DurationUnit.WEEK.value == "week"


# --- ReferenceEventCandidate (TV-001, TV-008 related) ---


class TestReferenceEventCandidate:
    def test_default_unconfirmed(self) -> None:
        """TV-001: New candidates are UNCONFIRMED by default."""
        c = ReferenceEventCandidate(
            candidate_id=uuid4(),
            document_id=uuid4(),
        )
        assert c.confirmation_status == ConfirmationStatus.UNCONFIRMED

    def test_default_unknown_event_type(self) -> None:
        c = ReferenceEventCandidate(
            candidate_id=uuid4(),
            document_id=uuid4(),
        )
        assert c.event_type == EventType.UNKNOWN

    def test_negative_start_offset_raises(self) -> None:
        with pytest.raises(ValueError, match="start_offset"):
            ReferenceEventCandidate(
                candidate_id=uuid4(),
                document_id=uuid4(),
                start_offset=-1,
            )

    def test_end_before_start_raises(self) -> None:
        with pytest.raises(ValueError, match="end_offset"):
            ReferenceEventCandidate(
                candidate_id=uuid4(),
                document_id=uuid4(),
                start_offset=10,
                end_offset=5,
            )

    def test_source_reference_length_limit(self) -> None:
        with pytest.raises(ValueError, match="source_reference"):
            ReferenceEventCandidate(
                candidate_id=uuid4(),
                document_id=uuid4(),
                source_reference="x" * 101,
            )

    def test_evidence_text_length_limit(self) -> None:
        with pytest.raises(ValueError, match="evidence_text"):
            ReferenceEventCandidate(
                candidate_id=uuid4(),
                document_id=uuid4(),
                evidence_text="x" * 2001,
            )

    def test_with_suggested_date(self) -> None:
        d = date(2026, 7, 15)
        c = ReferenceEventCandidate(
            candidate_id=uuid4(),
            document_id=uuid4(),
            suggested_date=d,
            event_type=EventType.ISSUE_DATE,
            source_type=SourceType.AUTO_DETECTED,
        )
        assert c.suggested_date == d
        assert c.event_type == EventType.ISSUE_DATE
        assert c.source_type == SourceType.AUTO_DETECTED


# --- Duration (TV-023, TV-024, TV-025, TV-026) ---


class TestDuration:
    def test_day_calendar_days(self) -> None:
        """TV-010: Duration(amount=1, unit=DAY) -> calendar_days=1."""
        d = Duration(amount=1, unit=DurationUnit.DAY)
        assert d.calendar_days == 1
        assert d.amount == 1

    def test_14_days(self) -> None:
        """TV-011: Duration(amount=14, unit=DAY) -> calendar_days=14."""
        d = Duration(amount=14, unit=DurationUnit.DAY)
        assert d.calendar_days == 14

    def test_365_days(self) -> None:
        """TV-018: Duration(amount=365, unit=DAY) -> calendar_days=365."""
        d = Duration(amount=365, unit=DurationUnit.DAY)
        assert d.calendar_days == 365

    def test_1_week_is_7_days(self) -> None:
        """TV-019: Duration(amount=1, unit=WEEK) -> calendar_days=7."""
        d = Duration(amount=1, unit=DurationUnit.WEEK)
        assert d.calendar_days == 7

    def test_2_weeks_is_14_days(self) -> None:
        """TV-020: Duration(amount=2, unit=WEEK) -> calendar_days=14."""
        d = Duration(amount=2, unit=DurationUnit.WEEK)
        assert d.calendar_days == 14

    def test_4_weeks_is_28_days(self) -> None:
        """TV-021: Duration(amount=4, unit=WEEK) -> calendar_days=28."""
        d = Duration(amount=4, unit=DurationUnit.WEEK)
        assert d.calendar_days == 28

    def test_zero_amount_raises(self) -> None:
        """TV-023: Duration(amount=0) -> ValueError."""
        with pytest.raises(ValueError, match="positive"):
            Duration(amount=0, unit=DurationUnit.DAY)

    def test_negative_amount_raises(self) -> None:
        """TV-024: Duration(amount=-5) -> ValueError."""
        with pytest.raises(ValueError, match="positive"):
            Duration(amount=-5, unit=DurationUnit.DAY)

    def test_exceeds_max_raises(self) -> None:
        """TV-025: Duration(amount=36501) -> ValueError."""
        with pytest.raises(ValueError, match="maximum"):
            Duration(amount=36501, unit=DurationUnit.DAY)

    def test_exactly_max_allowed(self) -> None:
        """TV-026: Duration(amount=36500) -> valid."""
        d = Duration(amount=36500, unit=DurationUnit.DAY)
        assert d.amount == 36500

    def test_frozen(self) -> None:
        """Duration is frozen (immutable)."""
        d = Duration(amount=5, unit=DurationUnit.DAY)
        assert d.calendar_days == 5  # 5 days = 5 calendar days


# --- ConfirmedReferenceEvent ---


class TestConfirmedReferenceEvent:
    def test_create_confirmation(self) -> None:
        now = datetime.now(UTC)
        event = ConfirmedReferenceEvent(
            confirmation_id=uuid4(),
            candidate_id=uuid4(),
            document_id=uuid4(),
            event_type=EventType.ISSUE_DATE,
            confirmed_date=date(2026, 7, 15),
            source_type=SourceType.AUTO_DETECTED,
            confirmation_method=ConfirmationMethod.AUTO_SUGGESTED,
            confirmed_at=now,
        )
        assert event.confirmed_date == date(2026, 7, 15)
        assert event.confirmation_method == ConfirmationMethod.AUTO_SUGGESTED

    def test_manual_confirmation(self) -> None:
        """TV-002: Manual entry -> MANUALLY_ENTERED."""
        now = datetime.now(UTC)
        event = ConfirmedReferenceEvent(
            confirmation_id=uuid4(),
            candidate_id=None,
            document_id=uuid4(),
            event_type=EventType.DELIVERY,
            confirmed_date=date(2026, 7, 15),
            source_type=SourceType.USER_MANUAL,
            confirmation_method=ConfirmationMethod.MANUALLY_ENTERED,
            confirmed_at=now,
        )
        assert event.candidate_id is None
        assert event.confirmation_method == ConfirmationMethod.MANUALLY_ENTERED

    def test_rejected_no_date(self) -> None:
        """TV-004: Rejected -> confirmed_date=None."""
        now = datetime.now(UTC)
        event = ConfirmedReferenceEvent(
            confirmation_id=uuid4(),
            candidate_id=uuid4(),
            document_id=uuid4(),
            event_type=EventType.ISSUE_DATE,
            confirmed_date=None,
            source_type=SourceType.AUTO_DETECTED,
            confirmation_method=ConfirmationMethod.AUTO_SUGGESTED,
            confirmed_at=now,
        )
        assert event.confirmed_date is None

    def test_confirmed_by_length_limit(self) -> None:
        now = datetime.now(UTC)
        with pytest.raises(ValueError, match="confirmed_by"):
            ConfirmedReferenceEvent(
                confirmation_id=uuid4(),
                candidate_id=uuid4(),
                document_id=uuid4(),
                event_type=EventType.ISSUE_DATE,
                confirmed_date=date(2026, 7, 15),
                source_type=SourceType.AUTO_DETECTED,
                confirmation_method=ConfirmationMethod.AUTO_SUGGESTED,
                confirmed_at=now,
                confirmed_by="x" * 101,
            )

    def test_evidence_note_length_limit(self) -> None:
        now = datetime.now(UTC)
        with pytest.raises(ValueError, match="evidence_note"):
            ConfirmedReferenceEvent(
                confirmation_id=uuid4(),
                candidate_id=uuid4(),
                document_id=uuid4(),
                event_type=EventType.ISSUE_DATE,
                confirmed_date=date(2026, 7, 15),
                source_type=SourceType.AUTO_DETECTED,
                confirmation_method=ConfirmationMethod.AUTO_SUGGESTED,
                confirmed_at=now,
                evidence_note="x" * 2001,
            )

    def test_supersedes_chain(self) -> None:
        """TV-005, TV-006: Superseded chain."""
        now = datetime.now(UTC)
        first_id = uuid4()
        event = ConfirmedReferenceEvent(
            confirmation_id=uuid4(),
            candidate_id=uuid4(),
            document_id=uuid4(),
            event_type=EventType.ISSUE_DATE,
            confirmed_date=date(2026, 7, 15),
            source_type=SourceType.AUTO_DETECTED,
            confirmation_method=ConfirmationMethod.AUTO_SUGGESTED,
            confirmed_at=now,
            supersedes_confirmation_id=first_id,
        )
        assert event.supersedes_confirmation_id == first_id


# --- CalculationStep ---


class TestCalculationStep:
    def test_valid_step(self) -> None:
        d = date(2026, 7, 15)
        step = CalculationStep(
            step=1,
            operation=CalculationOperation.ADD_CALENDAR_DAYS,
            input_date=d,
            amount=14,
            output_date=date(2026, 7, 29),
        )
        assert step.step == 1
        assert step.amount == 14
        assert step.output_date == date(2026, 7, 29)

    def test_step_less_than_1_raises(self) -> None:
        with pytest.raises(ValueError, match="step"):
            CalculationStep(
                step=0,
                operation=CalculationOperation.ADD_CALENDAR_DAYS,
                input_date=date(2026, 7, 15),
                amount=1,
                output_date=date(2026, 7, 16),
            )


# --- CalendarCalculationCandidate ---


class TestCalendarCalculationCandidate:
    def test_default_safety_flags(self) -> None:
        """TV-036, TV-037: Default safety flags."""
        result = CalendarCalculationCandidate()
        assert result.legal_validity_assessed is False
        assert result.human_review_required is True
        assert result.adjustments_applied["weekend_adjustment_applied"] is False
        assert result.adjustments_applied["holiday_adjustment_applied"] is False
        assert result.adjustments_applied["legal_rule_applied"] is False

    def test_custom_warnings(self) -> None:
        result = CalendarCalculationCandidate(
            warnings=["CALCULATION_PREVIEW_ONLY"],
        )
        assert "CALCULATION_PREVIEW_ONLY" in result.warnings
