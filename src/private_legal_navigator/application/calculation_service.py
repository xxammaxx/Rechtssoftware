"""Application service for calendar calculation previews.

Orchestrates the calculation preview use case:
  1. Validate that a confirmed reference event exists
  2. Validate the duration from the M5 candidate
  3. Perform pure calendar arithmetic
  4. Return non-binding calculation preview with full traceability
"""

import uuid

from private_legal_navigator.application.calendar_arithmetic import CalendarArithmetic
from private_legal_navigator.application.reference_event_repository import (
    ReferenceEventRepository,
)
from private_legal_navigator.domain.reference_event import (
    CalendarCalculationCandidate,
    ConfirmedReferenceEvent,
    Duration,
    DurationUnit,
)


class CalculationService:
    """Application service for calendar calculation previews."""

    def __init__(
        self,
        repo: ReferenceEventRepository,
        arithmetic: CalendarArithmetic,
    ) -> None:
        self._repo = repo
        self._arithmetic = arithmetic

    def calculate_preview(
        self,
        confirmation_id: uuid.UUID,
        amount: int,
        unit: str,
    ) -> CalendarCalculationCandidate:
        """Request a non-binding calculation preview.

        Validates preconditions and performs pure calendar arithmetic.

        Args:
            confirmation_id: The confirmed reference event ID.
            amount: The duration amount from the M5 candidate.
            unit: The duration unit from the M5 candidate (e.g., "day", "week").

        Returns:
            CalendarCalculationCandidate with full traceability.

        Raises:
            ValueError: If confirmation not found or not active.
            ValueError: If duration unit is unsupported.
            ValueError: If duration amount is invalid.
        """
        # Validate confirmation exists and is active
        event = self._repo.get_confirmation(confirmation_id)
        if event is None:
            raise ValueError("REFERENCE_EVENT_NOT_CONFIRMED")

        # Validate duration
        duration = self._validate_duration(amount, unit)

        # Calculate
        return self._arithmetic.calculate(event, duration)

    def calculate_preview_from_event(
        self,
        event: ConfirmedReferenceEvent,
        amount: int,
        unit: str,
    ) -> CalendarCalculationCandidate:
        """Calculate preview directly from a confirmed event (no DB lookup).

        Args:
            event: The confirmed reference event.
            amount: The duration amount.
            unit: The duration unit.

        Returns:
            CalendarCalculationCandidate with full traceability.
        """
        duration = self._validate_duration(amount, unit)
        return self._arithmetic.calculate(event, duration)

    @staticmethod
    def _validate_duration(amount: int, unit: str) -> Duration:
        """Validate and create a Duration from raw M5 output.

        Args:
            amount: The duration amount.
            unit: The duration unit string.

        Returns:
            Validated Duration object.

        Raises:
            ValueError: If unit is unsupported or amount is invalid.
        """
        unit_map: dict[str, DurationUnit] = {
            "day": DurationUnit.DAY,
            "Tag": DurationUnit.DAY,
            "Tage": DurationUnit.DAY,
            "week": DurationUnit.WEEK,
            "Woche": DurationUnit.WEEK,
            "Wochen": DurationUnit.WEEK,
        }

        if unit not in unit_map:
            raise ValueError(f"UNSUPPORTED_DURATION_UNIT: {unit}")

        duration_unit = unit_map[unit]
        return Duration(amount=amount, unit=duration_unit)
