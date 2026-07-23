"""Port for deterministic calendar arithmetic (M6-A).

Pure function: no side effects, no I/O, no network.
"""

from abc import ABC, abstractmethod
from datetime import date

from private_legal_navigator.domain.reference_event import (
    CalculationOperation,
    CalendarCalculationCandidate,
    ConfirmedReferenceEvent,
    Duration,
)


class CalendarArithmetic(ABC):
    """Pure arithmetic for calendar date calculations.

    No legal rules. No weekends. No holidays. No delivery fiction.
    Just `date + timedelta(days=N)`.
    """

    @abstractmethod
    def calculate(
        self,
        reference_event: ConfirmedReferenceEvent,
        duration: Duration,
        calculation_id: str | None = None,
    ) -> CalendarCalculationCandidate:
        """Calculate a candidate date from a confirmed reference event and duration.

        Args:
            reference_event: The user-confirmed reference date.
            duration: The duration to add (days or weeks).
            calculation_id: Optional identifier for the calculation.

        Returns:
            A CalendarCalculationCandidate with the calculated date,
            step-by-step arithmetic trail, safety flags, and warnings.
        """
        ...

    @abstractmethod
    def resolve_operation(self, duration: Duration) -> CalculationOperation:
        """Map a duration to the corresponding arithmetic operation."""
        ...

    @abstractmethod
    def add_calendar_days(self, reference_date: date, days: int) -> date:
        """Add calendar days to a date (pure timedelta)."""
        ...

    @abstractmethod
    def add_calendar_weeks(self, reference_date: date, weeks: int) -> date:
        """Add calendar weeks to a date (pure timedelta × 7)."""
        ...
