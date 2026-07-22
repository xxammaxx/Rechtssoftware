"""Unit tests for M6-A reference event domain models."""

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from private_legal_navigator.domain.reference_event import (
    CalculationOperation,
    CalculationStep,
    CalculationWarningCode,
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

# ── Enum stability tests ──


class TestEventType:
    """Enum values are stable."""

    def test_values(self) -> None:
        assert EventType.DELIVERY == "delivery"
        assert EventType.ANNOUNCEMENT == "announcement"
        assert EventType.RECEIPT == "receipt"
        assert EventType.ISSUE_DATE == "issue_date"
        assert EventType.PUBLICATION == "publication"
        assert EventType.APPLICATION == "application"
        assert EventType.USER_DEFINED == "user_defined"
        assert EventType.UNKNOWN == "unknown"


class TestConfirmationStatus:
    """Enum values are stable."""

    def test_values(self) -> None:
        assert ConfirmationStatus.UNCONFIRMED == "unconfirmed"
        assert ConfirmationStatus.CONFIRMED == "confirmed"
        assert ConfirmationStatus.REJECTED == "rejected"
        assert ConfirmationStatus.REVOKED == "revoked"
        assert ConfirmationStatus.SUPERSEDED == "superseded"


class TestSourceType:
    """Enum values are stable."""

    def test_values(self) -> None:
        assert SourceType.AUTO_DETECTED == "auto_detected"
        assert SourceType.USER_MANUAL == "user_manual"
        assert SourceType.USER_CORRECTED == "user_corrected"


class TestConfirmationMethod:
    """Enum values are stable."""

    def test_values(self) -> None:
        assert ConfirmationMethod.AUTO_SUGGESTED == "auto_suggested"
        assert ConfirmationMethod.MANUALLY_ENTERED == "manually_entered"
        assert ConfirmationMethod.CORRECTED == "corrected"


class TestDurationUnit:
    """Enum values are stable."""

    def test_values(self) -> None:
        assert DurationUnit.DAY == "day"
        assert DurationUnit.WEEK == "week"


class TestCalculationOperation:
    """Enum values are stable."""

    def test_values(self) -> None:
        assert CalculationOperation.ADD_CALENDAR_DAYS == "ADD_CALENDAR_DAYS"
        assert CalculationOperation.ADD_CALENDAR_WEEKS == "ADD_CALENDAR_WEEKS"


class TestCalculationWarningCode:
    """Warning codes are stable and must not change between releases."""

    def test_all_codes_defined(self) -> None:
        expected = {
            "LEGAL_CALCULATION_NOT_PERFORMED",
            "MULTIPLE_DEADLINE_CANDIDATES",
            "REFERENCE_EVENT_NOT_CONFIRMED",
            "REFERENCE_EVENT_REJECTED",
            "REFERENCE_EVENT_REVOKED",
            "MULTIPLE_REFERENCE_EVENTS",
            "REFERENCE_DATE_REQUIRED",
            "DURATION_NOT_AVAILABLE",
            "UNSUPPORTED_DURATION_UNIT",
            "INVALID_DURATION_AMOUNT",
            "DURATION_LIMIT_EXCEEDED",
            "INVALID_CANDIDATE_REFERENCE",
            "NO_WEEKEND_OR_HOLIDAY_ADJUSTMENT",
            "NO_DELIVERY_OR_ANNOUNCEMENT_RULE_APPLIED",
            "HUMAN_REVIEW_REQUIRED",
            "CALCULATION_PREVIEW_ONLY",
            "CALCULATION_NOT_PERFORMED",
        }
        actual = set(CalculationWarningCode.__members__.keys())
        assert actual == expected


# ── ReferenceEventCandidate tests ──


class TestReferenceEventCandidate:
    """Post-init validation enforces invariants."""

    def test_default_status_is_unconfirmed(self) -> None:
        c = ReferenceEventCandidate(
            candidate_id=uuid4(),
            document_id=uuid4(),
            deadline_candidate_index=0,
        )
        assert c.confirmation_status == ConfirmationStatus.UNCONFIRMED
        assert c.event_type == EventType.UNKNOWN

    def test_valid_auto_detected(self) -> None:
        c = ReferenceEventCandidate(
            candidate_id=uuid4(),
            document_id=uuid4(),
            deadline_candidate_index=0,
            event_type=EventType.ISSUE_DATE,
            suggested_date=date(2026, 7, 15),
            source_type=SourceType.AUTO_DETECTED,
            evidence_text="Bescheid vom 15.07.2026",
            start_offset=10,
            end_offset=33,
        )
        assert c.suggested_date == date(2026, 7, 15)
        assert c.source_type == SourceType.AUTO_DETECTED

    def test_negative_start_offset_raises(self) -> None:
        with pytest.raises(ValueError, match="start_offset must be >= 0"):
            ReferenceEventCandidate(
                candidate_id=uuid4(),
                document_id=uuid4(),
                deadline_candidate_index=0,
                start_offset=-1,
                end_offset=10,
            )

    def test_end_before_start_raises(self) -> None:
        with pytest.raises(ValueError, match="end_offset must be >= start_offset"):
            ReferenceEventCandidate(
                candidate_id=uuid4(),
                document_id=uuid4(),
                deadline_candidate_index=0,
                start_offset=20,
                end_offset=10,
            )

    def test_evidence_text_too_long_raises(self) -> None:
        with pytest.raises(ValueError, match="evidence_text exceeds 2000 character limit"):
            ReferenceEventCandidate(
                candidate_id=uuid4(),
                document_id=uuid4(),
                deadline_candidate_index=0,
                evidence_text="x" * 2001,
            )

    def test_source_reference_too_long_raises(self) -> None:
        with pytest.raises(ValueError, match="source_reference exceeds 100 character limit"):
            ReferenceEventCandidate(
                candidate_id=uuid4(),
                document_id=uuid4(),
                deadline_candidate_index=0,
                source_reference="x" * 101,
            )


# ── ConfirmedReferenceEvent tests ──


class TestConfirmedReferenceEvent:
    """Post-init validation enforces invariants."""

    def test_valid_confirmation(self) -> None:
        now = datetime.now(UTC)
        c = ConfirmedReferenceEvent(
            confirmation_id=uuid4(),
            document_id=uuid4(),
            deadline_candidate_index=0,
            event_type=EventType.DELIVERY,
            confirmed_at=now,
            confirmed_date=date(2026, 7, 15),
            source_type=SourceType.AUTO_DETECTED,
            confirmation_method=ConfirmationMethod.AUTO_SUGGESTED,
        )
        assert c.confirmed_date == date(2026, 7, 15)
        assert c.confirmed_by == ""

    def test_manual_entry_no_candidate(self) -> None:
        now = datetime.now(UTC)
        c = ConfirmedReferenceEvent(
            confirmation_id=uuid4(),
            document_id=uuid4(),
            deadline_candidate_index=0,
            event_type=EventType.USER_DEFINED,
            confirmed_at=now,
            confirmed_date=date(2026, 7, 20),
            source_type=SourceType.USER_MANUAL,
            confirmation_method=ConfirmationMethod.MANUALLY_ENTERED,
            candidate_id=None,
        )
        assert c.candidate_id is None
        assert c.confirmation_method == ConfirmationMethod.MANUALLY_ENTERED

    def test_confirmed_by_too_long_raises(self) -> None:
        with pytest.raises(ValueError, match="confirmed_by exceeds 100 character limit"):
            ConfirmedReferenceEvent(
                confirmation_id=uuid4(),
                document_id=uuid4(),
                deadline_candidate_index=0,
                event_type=EventType.DELIVERY,
                confirmed_at=datetime.now(UTC),
                confirmed_date=date(2026, 7, 15),
                source_type=SourceType.AUTO_DETECTED,
                confirmation_method=ConfirmationMethod.AUTO_SUGGESTED,
                confirmed_by="x" * 101,
            )

    def test_evidence_note_too_long_raises(self) -> None:
        with pytest.raises(ValueError, match="evidence_note exceeds 2000 character limit"):
            ConfirmedReferenceEvent(
                confirmation_id=uuid4(),
                document_id=uuid4(),
                deadline_candidate_index=0,
                event_type=EventType.DELIVERY,
                confirmed_at=datetime.now(UTC),
                confirmed_date=date(2026, 7, 15),
                source_type=SourceType.AUTO_DETECTED,
                confirmation_method=ConfirmationMethod.AUTO_SUGGESTED,
                evidence_note="x" * 2001,
            )

    def test_supersedes_chain(self) -> None:
        now = datetime.now(UTC)
        first_id = uuid4()
        second_id = uuid4()
        first = ConfirmedReferenceEvent(
            confirmation_id=first_id,
            document_id=uuid4(),
            deadline_candidate_index=0,
            event_type=EventType.ISSUE_DATE,
            confirmed_at=now,
            confirmed_date=date(2026, 7, 15),
            source_type=SourceType.AUTO_DETECTED,
            confirmation_method=ConfirmationMethod.AUTO_SUGGESTED,
        )
        second = ConfirmedReferenceEvent(
            confirmation_id=second_id,
            document_id=first.document_id,
            deadline_candidate_index=0,
            event_type=EventType.ISSUE_DATE,
            confirmed_at=now,
            confirmed_date=date(2026, 7, 20),
            source_type=SourceType.USER_CORRECTED,
            confirmation_method=ConfirmationMethod.CORRECTED,
            supersedes_confirmation_id=first_id,
        )
        assert second.supersedes_confirmation_id == first_id
        assert second.confirmed_date == date(2026, 7, 20)


# ── Duration tests ──


class TestDuration:
    """Duration validation and calendar_days conversion."""

    def test_days_calendar_days(self) -> None:
        d = Duration(amount=14, unit=DurationUnit.DAY)
        assert d.calendar_days == 14

    def test_weeks_calendar_days(self) -> None:
        d = Duration(amount=2, unit=DurationUnit.WEEK)
        assert d.calendar_days == 14

    def test_single_week(self) -> None:
        d = Duration(amount=1, unit=DurationUnit.WEEK)
        assert d.calendar_days == 7

    def test_frozen(self) -> None:
        d = Duration(amount=5, unit=DurationUnit.DAY)
        with pytest.raises(AttributeError):
            d.amount = 10  # type: ignore[misc]

    def test_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="Duration amount must be positive"):
            Duration(amount=0, unit=DurationUnit.DAY)

    def test_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="Duration amount must be positive"):
            Duration(amount=-5, unit=DurationUnit.DAY)

    def test_maximum_limit(self) -> None:
        Duration(amount=36500, unit=DurationUnit.DAY)

    def test_exceeds_maximum_raises(self) -> None:
        with pytest.raises(ValueError, match="Duration exceeds maximum"):
            Duration(amount=36501, unit=DurationUnit.DAY)


# ── CalendarCalculationCandidate tests ──


class TestCalendarCalculationCandidate:
    """Safety flags are structurally set."""

    def test_default_safety_flags(self) -> None:
        c = CalendarCalculationCandidate()
        assert c.legal_validity_assessed is False
        assert c.human_review_required is True

    def test_no_adjustments_by_default(self) -> None:
        c = CalendarCalculationCandidate()
        assert c.adjustments_applied["weekend_adjustment_applied"] is False
        assert c.adjustments_applied["holiday_adjustment_applied"] is False
        assert c.adjustments_applied["legal_rule_applied"] is False
        assert c.adjustments_applied["delivery_fiction_applied"] is False
        assert c.adjustments_applied["announcement_fiction_applied"] is False

    def test_with_calculation_steps(self) -> None:
        steps = [
            CalculationStep(
                step=1,
                operation=CalculationOperation.ADD_CALENDAR_DAYS,
                input_date=date(2026, 7, 15),
                amount=14,
                output_date=date(2026, 7, 29),
            )
        ]
        c = CalendarCalculationCandidate(
            calculation_id=uuid4(),
            calculated_date=date(2026, 7, 29),
            calculation_steps=steps,
            warnings=["CALCULATION_PREVIEW_ONLY"],
        )
        assert len(c.calculation_steps) == 1
        assert c.calculation_steps[0].operation == CalculationOperation.ADD_CALENDAR_DAYS
        assert c.calculated_date == date(2026, 7, 29)

    def test_without_calculation_id(self) -> None:
        c = CalendarCalculationCandidate()
        assert c.calculation_id is None
        assert c.confirmed_reference_event is None
        assert c.duration is None
        assert c.calculated_date is None

    def test_calculation_step_negative_amount_raises(self) -> None:
        """CalculationStep with amount < 0 raises ValueError."""
        with pytest.raises(ValueError, match="amount must be >= 0"):
            CalculationStep(
                step=1,
                operation=CalculationOperation.ADD_CALENDAR_DAYS,
                input_date=date(2026, 1, 1),
                amount=-1,
                output_date=date(2026, 1, 1),
            )
