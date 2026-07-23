"""Tests for cross-case mutation isolation (Track A — M7-A.1).

Verifies that mutation operations are rejected when an entity does not
belong to the target case (cross-case protection).
Ensures same-case operations succeed as expected.
"""

import uuid
from unittest.mock import MagicMock

import pytest

from private_legal_navigator.application.case_timeline_service import CaseTimelineService
from private_legal_navigator.domain.case_timeline import (
    CaseLegalEvent,
    CaseLegalLink,
    LegalEventType,
    LegalLinkStatus,
    ReviewStatus,
)


def _make_event(event_id, case_id):
    """Create a test legal event."""
    return CaseLegalEvent(
        event_id=event_id,
        case_id=case_id,
        event_type=LegalEventType.OTHER,
        title="Test",
        review_status=ReviewStatus.CANDIDATE,
    )


def _make_link(link_id, case_id):
    """Create a test legal link."""
    return CaseLegalLink(
        link_id=link_id,
        case_id=case_id,
        legal_provision_id=uuid.uuid4(),
        status=LegalLinkStatus.CANDIDATE,
    )


@pytest.fixture
def service():
    """Create a CaseTimelineService with mocked repositories."""
    timeline_mock = MagicMock()
    legal_mock = MagicMock()
    return CaseTimelineService(timeline_mock, legal_mock)


class TestCrossCaseEventIsolation:
    """Verify event mutations are rejected for wrong case."""

    def test_confirm_event_wrong_case_rejected(self, service):
        """Confirming an event belonging to case A with case_id=case B must fail."""
        case_a = uuid.uuid4()
        case_b = uuid.uuid4()
        event_in_a = _make_event(uuid.uuid4(), case_a)
        service._timeline_repo.get_event.return_value = event_in_a

        with pytest.raises(ValueError, match="Event not found"):
            service.confirm_event(event_in_a.event_id, case_id=case_b)

    def test_confirm_event_same_case_succeeds(self, service):
        """Confirming an event with the correct case_id must succeed."""
        case_id = uuid.uuid4()
        event = _make_event(uuid.uuid4(), case_id)
        service._timeline_repo.get_event.return_value = event

        result = service.confirm_event(event.event_id, case_id=case_id)
        assert result.review_status == ReviewStatus.CONFIRMED

    def test_reject_event_wrong_case_rejected(self, service):
        """Rejecting an event with a wrong case_id must fail."""
        case_a = uuid.uuid4()
        case_b = uuid.uuid4()
        event = _make_event(uuid.uuid4(), case_a)
        service._timeline_repo.get_event.return_value = event

        with pytest.raises(ValueError, match="Event not found"):
            service.reject_event(event.event_id, case_id=case_b)

    def test_revoke_event_wrong_case_rejected(self, service):
        """Revoking an event with a wrong case_id must fail."""
        case_a = uuid.uuid4()
        case_b = uuid.uuid4()
        event = _make_event(uuid.uuid4(), case_a)
        event.review_status = ReviewStatus.CONFIRMED
        service._timeline_repo.get_event.return_value = event

        with pytest.raises(ValueError, match="Event not found"):
            service.revoke_event(event.event_id, case_id=case_b)

    def test_correct_event_wrong_case_rejected(self, service):
        """Correcting an event with a wrong case_id must fail."""
        case_a = uuid.uuid4()
        case_b = uuid.uuid4()
        event = _make_event(uuid.uuid4(), case_a)
        event.review_status = ReviewStatus.CONFIRMED
        service._timeline_repo.get_event.return_value = event

        with pytest.raises(ValueError, match="Event not found"):
            service.correct_event(event.event_id, case_id=case_b)


class TestCrossCaseLinkIsolation:
    """Verify link mutations are rejected for wrong case."""

    def test_confirm_link_wrong_case_rejected(self, service):
        """Confirming a link belonging to case A with case_id=case B must fail."""
        case_a = uuid.uuid4()
        case_b = uuid.uuid4()
        link = _make_link(uuid.uuid4(), case_a)
        service._timeline_repo.get_link.return_value = link

        with pytest.raises(ValueError, match="Link not found"):
            service.confirm_link(link.link_id, case_id=case_b)

    def test_confirm_link_same_case_succeeds(self, service):
        """Confirming a link with the correct case_id must succeed."""
        case_id = uuid.uuid4()
        link = _make_link(uuid.uuid4(), case_id)
        service._timeline_repo.get_link.return_value = link

        result = service.confirm_link(link.link_id, case_id=case_id)
        assert result.status == LegalLinkStatus.CONFIRMED

    def test_reject_link_wrong_case_rejected(self, service):
        """Rejecting a link with a wrong case_id must fail."""
        case_a = uuid.uuid4()
        case_b = uuid.uuid4()
        link = _make_link(uuid.uuid4(), case_a)
        service._timeline_repo.get_link.return_value = link

        with pytest.raises(ValueError, match="Link not found"):
            service.reject_link(link.link_id, case_id=case_b)

    def test_revoke_link_wrong_case_rejected(self, service):
        """Revoking a link with a wrong case_id must fail."""
        case_a = uuid.uuid4()
        case_b = uuid.uuid4()
        link = _make_link(uuid.uuid4(), case_a)
        link.status = LegalLinkStatus.CONFIRMED
        service._timeline_repo.get_link.return_value = link

        with pytest.raises(ValueError, match="Link not found"):
            service.revoke_link(link.link_id, case_id=case_b)

    def test_correct_link_wrong_case_rejected(self, service):
        """Correcting a link with a wrong case_id must fail."""
        case_a = uuid.uuid4()
        case_b = uuid.uuid4()
        link = _make_link(uuid.uuid4(), case_a)
        link.status = LegalLinkStatus.CONFIRMED
        service._timeline_repo.get_link.return_value = link

        with pytest.raises(ValueError, match="Link not found"):
            service.correct_link(link.link_id, case_id=case_b)
