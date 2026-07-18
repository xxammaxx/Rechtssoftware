"""Deterministic calendar arithmetic implementation.

Pure function — no side effects, no external dependencies.
Uses only stdlib datetime.timedelta for date arithmetic.
"""

import uuid
from datetime import date, timedelta

from private_legal_navigator.application.calendar_arithmetic import CalendarArithmetic
from private_legal_navigator.domain.reference_event import (
    CalculationOperation,
    CalculationStep,
    CalendarCalculationCandidate,
    ConfirmedReferenceEvent,
    Duration,
    DurationUnit,
)


class DeterministicCalendarArithmetic(CalendarArithmetic):
    """Pure calendar arithmetic implementation.

    Only DAY and WEEK units are supported. Months, years, business
    days, and working days are rejected before reaching this class.
    """

    MIN_DATE = date(1900, 1, 1)
    MAX_DATE = date(2099, 12, 31)

    def calculate(
        self,
        reference_event: ConfirmedReferenceEvent,
        duration: Duration,
    ) -> CalendarCalculationCandidate:
        """Calculate a non-binding calendar preview.

        Args:
            reference_event: The user-confirmed reference event.
            duration: The duration to add (DAY or WEEK units only).

        Returns:
            CalendarCalculationCandidate with calculation steps.

        Raises:
            ValueError: If the reference_event has no confirmed_date.
        """
        if reference_event.confirmed_date is None:
            raise ValueError("REFERENCE_EVENT_NOT_CONFIRMED")

        ref_date = reference_event.confirmed_date
        calendar_days = duration.calendar_days
        calculated_date = ref_date + timedelta(days=calendar_days)

        # Post-calculation range check
        if calculated_date < self.MIN_DATE or calculated_date > self.MAX_DATE:
            raise ValueError("CALCULATED_DATE_OUT_OF_RANGE")

        operation = (
            CalculationOperation.ADD_CALENDAR_DAYS
            if duration.unit == DurationUnit.DAY
            else CalculationOperation.ADD_CALENDAR_WEEKS
        )

        steps = [
            CalculationStep(
                step=1,
                operation=operation,
                input_date=ref_date,
                amount=calendar_days,
                output_date=calculated_date,
            )
        ]

        return CalendarCalculationCandidate(
            calculation_id=uuid.uuid4(),
            confirmed_reference_event=reference_event,
            duration=duration,
            calculated_date=calculated_date,
            calculation_steps=steps,
            warnings=[
                "CALCULATION_PREVIEW_ONLY",
                "NO_WEEKEND_OR_HOLIDAY_ADJUSTMENT",
                "NO_DELIVERY_OR_ANNOUNCEMENT_RULE_APPLIED",
                "HUMAN_REVIEW_REQUIRED",
            ],
        )
