"""Unit tests for DeterministicCalendarArithmetic (M6-A)."""

from datetime import UTC, date, datetime
from uuid import uuid4

from private_legal_navigator.domain.calendar import (
    CalculationOperation,
    ConfirmationMethod,
    ConfirmedReferenceEvent,
    Duration,
    DurationUnit,
    EventType,
    SourceType,
)
from private_legal_navigator.infrastructure.deterministic_calendar import (
    MIN_DATE,
    DeterministicCalendarArithmetic,
)


def _make_event(confirmed_date: date) -> ConfirmedReferenceEvent:
    return ConfirmedReferenceEvent(
        confirmation_id=uuid4(),
        candidate_id=uuid4(),
        document_id=uuid4(),
        event_type=EventType.ISSUE_DATE,
        confirmed_date=confirmed_date,
        source_type=SourceType.AUTO_DETECTED,
        confirmation_method=ConfirmationMethod.AUTO_SUGGESTED,
        confirmed_at=datetime.now(UTC),
    )


class TestArithmetic:
    def setup_method(self) -> None:
        self.arithmetic = DeterministicCalendarArithmetic()

    # --- Day Arithmetic (TV-010 to TV-018) ---

    def test_add_1_day(self) -> None:
        """TV-010: 2026-07-15 + 1 day = 2026-07-16."""
        event = _make_event(date(2026, 7, 15))
        duration = Duration(amount=1, unit=DurationUnit.DAY)
        result = self.arithmetic.calculate(event, duration)
        assert result.calculated_date == date(2026, 7, 16)
        assert len(result.calculation_steps) == 1
        assert result.calculation_steps[0].operation == CalculationOperation.ADD_CALENDAR_DAYS

    def test_add_14_days(self) -> None:
        """TV-011: 2026-07-15 + 14 days = 2026-07-29."""
        event = _make_event(date(2026, 7, 15))
        duration = Duration(amount=14, unit=DurationUnit.DAY)
        result = self.arithmetic.calculate(event, duration)
        assert result.calculated_date == date(2026, 7, 29)

    def test_month_boundary_forward(self) -> None:
        """TV-012: 2026-01-31 + 1 day = 2026-02-01."""
        event = _make_event(date(2026, 1, 31))
        duration = Duration(amount=1, unit=DurationUnit.DAY)
        result = self.arithmetic.calculate(event, duration)
        assert result.calculated_date == date(2026, 2, 1)

    def test_month_boundary_non_leap(self) -> None:
        """TV-013: 2026-02-28 + 1 day = 2026-03-01."""
        event = _make_event(date(2026, 2, 28))
        duration = Duration(amount=1, unit=DurationUnit.DAY)
        result = self.arithmetic.calculate(event, duration)
        assert result.calculated_date == date(2026, 3, 1)

    def test_year_boundary(self) -> None:
        """TV-014: 2026-12-31 + 1 day = 2027-01-01."""
        event = _make_event(date(2026, 12, 31))
        duration = Duration(amount=1, unit=DurationUnit.DAY)
        result = self.arithmetic.calculate(event, duration)
        assert result.calculated_date == date(2027, 1, 1)

    def test_leap_year_feb_29(self) -> None:
        """TV-015: 2024-02-28 + 1 day = 2024-02-29 (leap year)."""
        event = _make_event(date(2024, 2, 28))
        duration = Duration(amount=1, unit=DurationUnit.DAY)
        result = self.arithmetic.calculate(event, duration)
        assert result.calculated_date == date(2024, 2, 29)

    def test_non_leap_year_feb(self) -> None:
        """TV-016: 2025-02-28 + 1 day = 2025-03-01."""
        event = _make_event(date(2025, 2, 28))
        duration = Duration(amount=1, unit=DurationUnit.DAY)
        result = self.arithmetic.calculate(event, duration)
        assert result.calculated_date == date(2025, 3, 1)

    def test_leap_year_plus_365(self) -> None:
        """TV-017: 2024-02-29 + 365 days = 2025-02-28."""
        event = _make_event(date(2024, 2, 29))
        duration = Duration(amount=365, unit=DurationUnit.DAY)
        result = self.arithmetic.calculate(event, duration)
        assert result.calculated_date == date(2025, 2, 28)

    def test_full_year(self) -> None:
        """TV-018: 2026-07-15 + 365 days = 2027-07-15."""
        event = _make_event(date(2026, 7, 15))
        duration = Duration(amount=365, unit=DurationUnit.DAY)
        result = self.arithmetic.calculate(event, duration)
        assert result.calculated_date == date(2027, 7, 15)

    # --- Week Arithmetic (TV-019 to TV-022) ---

    def test_add_1_week(self) -> None:
        """TV-019: 2026-07-15 + 1 week = 2026-07-22."""
        event = _make_event(date(2026, 7, 15))
        duration = Duration(amount=1, unit=DurationUnit.WEEK)
        result = self.arithmetic.calculate(event, duration)
        assert result.calculated_date == date(2026, 7, 22)
        assert result.calculation_steps[0].operation == CalculationOperation.ADD_CALENDAR_WEEKS

    def test_add_2_weeks(self) -> None:
        """TV-020: 2026-07-15 + 2 weeks = 2026-07-29."""
        event = _make_event(date(2026, 7, 15))
        duration = Duration(amount=2, unit=DurationUnit.WEEK)
        result = self.arithmetic.calculate(event, duration)
        assert result.calculated_date == date(2026, 7, 29)

    def test_add_4_weeks_year_boundary(self) -> None:
        """TV-021: 2026-12-15 + 4 weeks = 2027-01-12."""
        event = _make_event(date(2026, 12, 15))
        duration = Duration(amount=4, unit=DurationUnit.WEEK)
        result = self.arithmetic.calculate(event, duration)
        assert result.calculated_date == date(2027, 1, 12)

    def test_add_1_week_leap_year(self) -> None:
        """TV-022: 2024-02-22 + 1 week = 2024-02-29."""
        event = _make_event(date(2024, 2, 22))
        duration = Duration(amount=1, unit=DurationUnit.WEEK)
        result = self.arithmetic.calculate(event, duration)
        assert result.calculated_date == date(2024, 2, 29)

    # --- Safety Gates (TV-036 to TV-050) ---

    def test_human_review_always_true(self) -> None:
        """TV-036: human_review_required is always true."""
        event = _make_event(date(2026, 7, 15))
        duration = Duration(amount=1, unit=DurationUnit.DAY)
        result = self.arithmetic.calculate(event, duration)
        assert result.human_review_required is True

    def test_legal_validity_always_false(self) -> None:
        """TV-037: legal_validity_assessed is always false."""
        event = _make_event(date(2026, 7, 15))
        duration = Duration(amount=1, unit=DurationUnit.DAY)
        result = self.arithmetic.calculate(event, duration)
        assert result.legal_validity_assessed is False

    def test_no_weekend_adjustment(self) -> None:
        """TV-038: weekend_adjustment_applied is false."""
        event = _make_event(date(2026, 7, 15))
        duration = Duration(amount=1, unit=DurationUnit.DAY)
        result = self.arithmetic.calculate(event, duration)
        assert result.adjustments_applied["weekend_adjustment_applied"] is False

    def test_no_holiday_adjustment(self) -> None:
        """TV-039: holiday_adjustment_applied is false."""
        event = _make_event(date(2026, 7, 15))
        duration = Duration(amount=1, unit=DurationUnit.DAY)
        result = self.arithmetic.calculate(event, duration)
        assert result.adjustments_applied["holiday_adjustment_applied"] is False

    def test_no_legal_rule(self) -> None:
        """TV-040: legal_rule_applied is false."""
        event = _make_event(date(2026, 7, 15))
        duration = Duration(amount=1, unit=DurationUnit.DAY)
        result = self.arithmetic.calculate(event, duration)
        assert result.adjustments_applied["legal_rule_applied"] is False

    def test_no_delivery_fiction(self) -> None:
        """TV-041: delivery_fiction_applied is false."""
        event = _make_event(date(2026, 7, 15))
        duration = Duration(amount=1, unit=DurationUnit.DAY)
        result = self.arithmetic.calculate(event, duration)
        assert result.adjustments_applied["delivery_fiction_applied"] is False

    def test_no_announcement_fiction(self) -> None:
        """TV-042: announcement_fiction_applied is false."""
        event = _make_event(date(2026, 7, 15))
        duration = Duration(amount=1, unit=DurationUnit.DAY)
        result = self.arithmetic.calculate(event, duration)
        assert result.adjustments_applied["announcement_fiction_applied"] is False

    def test_calculation_steps_present(self) -> None:
        """TV-046: calculation_steps is present and non-empty."""
        event = _make_event(date(2026, 7, 15))
        duration = Duration(amount=1, unit=DurationUnit.DAY)
        result = self.arithmetic.calculate(event, duration)
        assert len(result.calculation_steps) == 1
        assert result.calculation_steps[0].step == 1

    def test_calculated_date_is_iso_compatible(self) -> None:
        """TV-047: calculated_date is a valid date object."""
        event = _make_event(date(2026, 7, 15))
        duration = Duration(amount=1, unit=DurationUnit.DAY)
        result = self.arithmetic.calculate(event, duration)
        assert result.calculated_date is not None
        assert result.calculated_date.isoformat() == "2026-07-16"

    def test_deterministic_output(self) -> None:
        """TV-048: Same inputs -> same outputs."""
        event = _make_event(date(2026, 7, 15))
        duration = Duration(amount=14, unit=DurationUnit.DAY)
        r1 = self.arithmetic.calculate(event, duration)
        r2 = self.arithmetic.calculate(event, duration)
        assert r1.calculated_date == r2.calculated_date

    # --- Range Validation (TV-023 to TV-026, TV-053 to TV-054) ---

    def test_min_date_1900(self) -> None:
        """Input at lower boundary (1900-01-01) is valid."""
        event = _make_event(MIN_DATE)
        duration = Duration(amount=1, unit=DurationUnit.DAY)
        result = self.arithmetic.calculate(event, duration)
        assert result.calculated_date is not None

    def test_before_1900_returns_error(self) -> None:
        """Input before 1900-01-01 returns out of range."""
        event = _make_event(date(1899, 12, 31))
        duration = Duration(amount=1, unit=DurationUnit.DAY)
        result = self.arithmetic.calculate(event, duration)
        assert result.calculated_date is None
        assert "CALCULATED_DATE_OUT_OF_RANGE" in result.warnings

    def test_max_date_2099(self) -> None:
        """Input at upper boundary (2099-12-31) is valid."""
        event_before = _make_event(date(2099, 12, 30))
        duration = Duration(amount=1, unit=DurationUnit.DAY)
        result = self.arithmetic.calculate(event_before, duration)
        assert result.calculated_date == date(2099, 12, 31)

    def test_exceeds_max_date_returns_error(self) -> None:
        """Result beyond 2099-12-31 returns out of range."""
        event = _make_event(date(2099, 12, 31))
        duration = Duration(amount=1, unit=DurationUnit.DAY)
        result = self.arithmetic.calculate(event, duration)
        assert result.calculated_date is None
        assert "CALCULATED_DATE_OUT_OF_RANGE" in result.warnings

    # --- No confirmed date ---

    def test_no_confirmed_date(self) -> None:
        """TV-001: Event with no confirmed_date returns warning."""
        event = ConfirmedReferenceEvent(
            confirmation_id=uuid4(),
            candidate_id=uuid4(),
            document_id=uuid4(),
            event_type=EventType.UNKNOWN,
            confirmed_date=None,
            source_type=SourceType.AUTO_DETECTED,
            confirmation_method=ConfirmationMethod.AUTO_SUGGESTED,
            confirmed_at=datetime.now(UTC),
        )
        duration = Duration(amount=1, unit=DurationUnit.DAY)
        result = self.arithmetic.calculate(event, duration)
        assert result.calculated_date is None
        assert "REFERENCE_EVENT_NOT_CONFIRMED" in result.warnings

    # --- Warning presence ---

    def test_warnings_present(self) -> None:
        """All calculations include standard safety warnings."""
        event = _make_event(date(2026, 7, 15))
        duration = Duration(amount=1, unit=DurationUnit.DAY)
        result = self.arithmetic.calculate(event, duration)
        assert "CALCULATION_PREVIEW_ONLY" in result.warnings
        assert "NO_WEEKEND_OR_HOLIDAY_ADJUSTMENT" in result.warnings
        assert "NO_DELIVERY_OR_ANNOUNCEMENT_RULE_APPLIED" in result.warnings
        assert "HUMAN_REVIEW_REQUIRED" in result.warnings
        assert "LEGAL_CALCULATION_NOT_PERFORMED" in result.warnings

    # --- Operation resolution ---

    def test_resolve_day_operation(self) -> None:
        duration = Duration(amount=5, unit=DurationUnit.DAY)
        op = self.arithmetic.resolve_operation(duration)
        assert op == CalculationOperation.ADD_CALENDAR_DAYS

    def test_resolve_week_operation(self) -> None:
        duration = Duration(amount=2, unit=DurationUnit.WEEK)
        op = self.arithmetic.resolve_operation(duration)
        assert op == CalculationOperation.ADD_CALENDAR_WEEKS
