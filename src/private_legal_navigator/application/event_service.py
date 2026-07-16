"""Application service for reference event confirmation (M6-A).

Orchestrates the confirmation state machine and calendar arithmetic.
"""

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from private_legal_navigator.application.calendar_arithmetic import CalendarArithmetic
from private_legal_navigator.application.event_repository import ReferenceEventRepository
from private_legal_navigator.domain.calendar import (
    CalculationWarningCode,
    CalendarCalculationCandidate,
    ConfirmationMethod,
    ConfirmedReferenceEvent,
    Duration,
    DurationUnit,
    EventType,
    SourceType,
)


def _map_source_type_to_method(source_type: SourceType) -> ConfirmationMethod:
    """Map source_type to confirmation_method per API contract."""
    mapping: dict[SourceType, ConfirmationMethod] = {
        SourceType.AUTO_DETECTED: ConfirmationMethod.AUTO_SUGGESTED,
        SourceType.USER_MANUAL: ConfirmationMethod.MANUALLY_ENTERED,
        SourceType.USER_CORRECTED: ConfirmationMethod.CORRECTED,
    }
    return mapping[source_type]


class ReferenceEventService:
    """Orchestrates reference event confirmation and calculation workflows."""

    def __init__(
        self,
        repository: ReferenceEventRepository,
        arithmetic: CalendarArithmetic,
    ) -> None:
        self._repo = repository
        self._arithmetic = arithmetic

    def confirm(
        self,
        document_id: UUID,
        candidate_id: UUID | None,
        event_type: EventType,
        confirmed_date: date | None,
        source_type: SourceType,
        confirmed_by: str = "",
        evidence_note: str = "",
        supersedes_confirmation_id: UUID | None = None,
    ) -> ConfirmedReferenceEvent:
        """Create a new confirmation for a reference date.

        If a prior CONFIRMED event exists for the same candidate,
        it is superseded.
        """
        confirmation_method = _map_source_type_to_method(source_type)

        event = ConfirmedReferenceEvent(
            confirmation_id=uuid4(),
            candidate_id=candidate_id,
            document_id=document_id,
            event_type=event_type,
            confirmed_date=confirmed_date,
            source_type=source_type,
            confirmation_method=confirmation_method,
            confirmed_at=datetime.now(UTC),
            confirmed_by=confirmed_by[:100],
            evidence_note=evidence_note[:2000],
            supersedes_confirmation_id=supersedes_confirmation_id,
        )
        self._repo.save(event)
        return event

    def reject(
        self,
        document_id: UUID,
        candidate_id: UUID | None,
        event_type: EventType,
    ) -> ConfirmedReferenceEvent:
        """Reject a candidate reference event."""
        event = ConfirmedReferenceEvent(
            confirmation_id=uuid4(),
            candidate_id=candidate_id,
            document_id=document_id,
            event_type=event_type,
            confirmed_date=None,
            source_type=SourceType.AUTO_DETECTED,
            confirmation_method=ConfirmationMethod.AUTO_SUGGESTED,
            confirmed_at=datetime.now(UTC),
        )
        self._repo.save(event)
        return event

    def revoke(
        self,
        confirmation_id: UUID,
        document_id: UUID,
    ) -> ConfirmedReferenceEvent:
        """Revoke an existing confirmation.

        Creates a REVOKED record. The prior record is marked SUPERSEDED.
        """
        prior = self._repo.get_by_id(confirmation_id)
        if prior is None:
            raise ValueError(f"Confirmation {confirmation_id} not found")

        event = ConfirmedReferenceEvent(
            confirmation_id=uuid4(),
            candidate_id=prior.candidate_id,
            document_id=document_id,
            event_type=EventType.UNKNOWN,
            confirmed_date=None,
            source_type=SourceType.AUTO_DETECTED,
            confirmation_method=ConfirmationMethod.AUTO_SUGGESTED,
            confirmed_at=datetime.now(UTC),
            supersedes_confirmation_id=confirmation_id,
        )
        self._repo.save(event)
        return event

    def get_active(self, document_id: UUID, candidate_index: int) -> ConfirmedReferenceEvent | None:
        """Get the currently active confirmed reference event."""
        return self._repo.get_active(document_id, candidate_index)

    def get_history(self, document_id: UUID, candidate_index: int) -> list[ConfirmedReferenceEvent]:
        """Get full confirmation audit trail."""
        return self._repo.get_history(document_id, candidate_index)

    def calculate_preview(
        self,
        document_id: UUID,
        candidate_index: int,
        confirmation_id: UUID,
        duration_amount: int,
        duration_unit: str,
    ) -> CalendarCalculationCandidate:
        """Calculate a non-binding preview based on a confirmed reference event.

        Validates the duration, confirms the reference event exists and is active,
        then computes the arithmetic result.
        """
        # Validate duration
        if duration_amount <= 0:
            result = CalendarCalculationCandidate(
                human_review_required=True,
                legal_validity_assessed=False,
                warnings=[CalculationWarningCode.INVALID_DURATION_AMOUNT.value],
            )
            return result

        if duration_amount > 36500:
            result = CalendarCalculationCandidate(
                human_review_required=True,
                legal_validity_assessed=False,
                warnings=[CalculationWarningCode.DURATION_LIMIT_EXCEEDED.value],
            )
            return result

        # Map duration unit
        unit_map: dict[str, DurationUnit | None] = {
            "day": DurationUnit.DAY,
            "Tag": DurationUnit.DAY,
            "tag": DurationUnit.DAY,
            "week": DurationUnit.WEEK,
            "Woche": DurationUnit.WEEK,
            "woche": DurationUnit.WEEK,
        }
        unit = unit_map.get(duration_unit)
        if unit is None:
            result = CalendarCalculationCandidate(
                human_review_required=True,
                legal_validity_assessed=False,
                warnings=[CalculationWarningCode.UNSUPPORTED_DURATION_UNIT.value],
            )
            return result

        # Get the confirmed reference event
        event = self._repo.get_by_id(confirmation_id)
        if event is None:
            result = CalendarCalculationCandidate(
                human_review_required=True,
                legal_validity_assessed=False,
                warnings=[CalculationWarningCode.REFERENCE_EVENT_NOT_CONFIRMED.value],
            )
            return result

        if event.confirmed_date is None:
            result = CalendarCalculationCandidate(
                human_review_required=True,
                legal_validity_assessed=False,
                warnings=[CalculationWarningCode.REFERENCE_EVENT_NOT_CONFIRMED.value],
            )
            return result

        duration = Duration(amount=duration_amount, unit=unit)
        return self._arithmetic.calculate(
            reference_event=event,
            duration=duration,
            calculation_id=str(uuid4()),
        )
