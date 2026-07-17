"""Deterministic calendar arithmetic (M6-A).

Pure arithmetic: date + timedelta(days=N).
No weekends. No holidays. No delivery fiction. No legal rules.
"""

from datetime import date, timedelta
from typing import ClassVar
from uuid import UUID

from private_legal_navigator.application.calendar_arithmetic import CalendarArithmetic
from private_legal_navigator.domain.calendar import (
    MAX_DURATION_CALENDAR_DAYS,
    CalculationOperation,
    CalculationStep,
    CalculationWarningCode,
    CalendarCalculationCandidate,
    ConfirmedReferenceEvent,
    Duration,
    DurationUnit,
)

# Valid date range per INV-M6A-23 (imported from domain for single source of truth)
MIN_DATE: date = date(1900, 1, 1)
MAX_DATE: date = date(2099, 12, 31)


class DeterministicCalendarArithmetic(CalendarArithmetic):
    """Pure, deterministic calendar arithmetic.

    No external dependencies. No network. No legal rules.
    """

    MAX_DURATION_DAYS: ClassVar[int] = MAX_DURATION_CALENDAR_DAYS

    def calculate(
        self,
        reference_event: ConfirmedReferenceEvent,
        duration: Duration,
        calculation_id: str | None = None,
    ) -> CalendarCalculationCandidate:
        """Calculate a candidate date from a confirmed reference event and duration."""
        calc_uuid: UUID | None = UUID(calculation_id) if calculation_id else None
        confirmed_date = reference_event.confirmed_date
        if confirmed_date is None:
            return CalendarCalculationCandidate(
                calculation_id=calc_uuid,
                confirmed_reference_event=reference_event,
                duration=duration,
                calculated_date=None,
                calculation_steps=[],
                legal_validity_assessed=False,
                human_review_required=True,
                warnings=[CalculationWarningCode.REFERENCE_EVENT_NOT_CONFIRMED.value],
            )

        # Validate reference date range
        if confirmed_date < MIN_DATE or confirmed_date > MAX_DATE:
            return CalendarCalculationCandidate(
                calculation_id=calc_uuid,
                confirmed_reference_event=reference_event,
                duration=duration,
                calculated_date=None,
                calculation_steps=[],
                legal_validity_assessed=False,
                human_review_required=True,
                warnings=[CalculationWarningCode.CALCULATED_DATE_OUT_OF_RANGE.value],
            )

        operation = self.resolve_operation(duration)
        calendar_days = duration.calendar_days

        # Compute result with overflow protection
        result_date = self._add_days_safe(confirmed_date, calendar_days)
        if result_date is None:
            return CalendarCalculationCandidate(
                calculation_id=calc_uuid,
                confirmed_reference_event=reference_event,
                duration=duration,
                calculated_date=None,
                calculation_steps=[],
                legal_validity_assessed=False,
                human_review_required=True,
                warnings=[CalculationWarningCode.CALCULATED_DATE_OUT_OF_RANGE.value],
            )

        # Validate result date range
        if result_date < MIN_DATE or result_date > MAX_DATE:
            return CalendarCalculationCandidate(
                calculation_id=calc_uuid,
                confirmed_reference_event=reference_event,
                duration=duration,
                calculated_date=None,
                calculation_steps=[],
                legal_validity_assessed=False,
                human_review_required=True,
                warnings=[CalculationWarningCode.CALCULATED_DATE_OUT_OF_RANGE.value],
            )

        step = CalculationStep(
            step=1,
            operation=operation,
            input_date=confirmed_date,
            amount=calendar_days,
            output_date=result_date,
        )

        warnings = [
            CalculationWarningCode.CALCULATION_PREVIEW_ONLY.value,
            CalculationWarningCode.NO_WEEKEND_OR_HOLIDAY_ADJUSTMENT.value,
            CalculationWarningCode.NO_DELIVERY_OR_ANNOUNCEMENT_RULE_APPLIED.value,
            CalculationWarningCode.HUMAN_REVIEW_REQUIRED.value,
            CalculationWarningCode.LEGAL_CALCULATION_NOT_PERFORMED.value,
        ]

        return CalendarCalculationCandidate(
            calculation_id=calc_uuid,
            confirmed_reference_event=reference_event,
            duration=duration,
            calculated_date=result_date,
            calculation_steps=[step],
            adjustments_applied={
                "weekend_adjustment_applied": False,
                "holiday_adjustment_applied": False,
                "legal_rule_applied": False,
                "delivery_fiction_applied": False,
                "announcement_fiction_applied": False,
            },
            legal_validity_assessed=False,
            human_review_required=True,
            warnings=warnings,
        )

    def resolve_operation(self, duration: Duration) -> CalculationOperation:
        """Map a duration to the corresponding arithmetic operation."""
        if duration.unit == DurationUnit.WEEK:
            return CalculationOperation.ADD_CALENDAR_WEEKS
        return CalculationOperation.ADD_CALENDAR_DAYS

    def add_calendar_days(self, reference_date: date, days: int) -> date:
        """Add calendar days to a date (pure timedelta)."""
        result = self._add_days_safe(reference_date, days)
        if result is None:
            raise ValueError("Calendar addition overflow")
        return result

    def add_calendar_weeks(self, reference_date: date, weeks: int) -> date:
        """Add calendar weeks to a date (pure timedelta × 7)."""
        result = self._add_days_safe(reference_date, weeks * 7)
        if result is None:
            raise ValueError("Calendar addition overflow")
        return result

    @staticmethod
    def _add_days_safe(reference_date: date, days: int) -> date | None:
        """Internal: timedelta addition with overflow protection.

        Returns None if the addition would overflow Python's date range.
        """
        try:
            return reference_date + timedelta(days=days)
        except (OverflowError, ValueError):
            return None

    @staticmethod
    def _add_days_impl(reference_date: date, days: int) -> date:
        """Internal: pure timedelta addition (no safety wrapper)."""
        return reference_date + timedelta(days=days)
