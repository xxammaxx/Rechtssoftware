"""Calendar arithmetic port (interface).

The calendar arithmetic is a pure function — no side effects,
no external dependencies. Only DAY and WEEK units are supported.
"""

from abc import ABC, abstractmethod

from private_legal_navigator.domain.reference_event import (
    CalendarCalculationCandidate,
    ConfirmedReferenceEvent,
    Duration,
)


class CalendarArithmetic(ABC):
    """Abstract calendar arithmetic for non-binding calculation previews.

    Implementations perform pure date arithmetic (no legal rules,
    no holiday/weekend adjustment). The result is always a
    non-binding calculation preview.
    """

    @abstractmethod
    def calculate(
        self,
        reference_event: ConfirmedReferenceEvent,
        duration: Duration,
    ) -> CalendarCalculationCandidate:
        """Calculate a non-binding calendar preview.

        Adds the duration to the confirmed reference date and returns
        the result with full calculation steps.

        Args:
            reference_event: The user-confirmed reference event with date.
            duration: The duration to add (DAY or WEEK units only).

        Returns:
            CalendarCalculationCandidate with calculation steps and
            safety flags set to non-binding defaults.

        Raises:
            ValueError: If duration unit is not DAY or WEEK.
            ValueError: If duration amount is zero or negative.
            ValueError: If duration exceeds maximum limit.
        """
        ...
