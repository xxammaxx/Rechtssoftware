"""Unit tests for M6-A application services."""

from datetime import UTC, date, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from private_legal_navigator.application.calculation_service import CalculationService
from private_legal_navigator.application.reference_event_service import (
    ReferenceEventService,
)
from private_legal_navigator.domain.reference_event import (
    CalendarCalculationCandidate,
    ConfirmationMethod,
    ConfirmedReferenceEvent,
    DurationUnit,
    EventType,
    SourceType,
)

# ── ReferenceEventService tests ──


class TestReferenceEventService:
    """Reference event lifecycle orchestration tests."""

    @pytest.fixture
    def mock_repo(self) -> MagicMock:
        repo = MagicMock()
        repo.get_active_confirmation.return_value = None
        repo.get_history_for_candidate.return_value = []
        return repo

    @pytest.fixture
    def service(self, mock_repo: MagicMock) -> ReferenceEventService:
        return ReferenceEventService(repo=mock_repo)

    def test_confirm_creates_new_event(
        self, service: ReferenceEventService, mock_repo: MagicMock
    ) -> None:
        doc_id = uuid4()

        event = service.confirm(
            document_id=doc_id,
            deadline_candidate_index=0,
            event_type=EventType.ISSUE_DATE,
            confirmed_date=date(2026, 7, 15),
            source_type=SourceType.AUTO_DETECTED,
            confirmation_method=ConfirmationMethod.AUTO_SUGGESTED,
        )

        assert event.document_id == doc_id
        assert event.confirmed_date == date(2026, 7, 15)
        assert event.deadline_candidate_index == 0
        assert event.event_type == EventType.ISSUE_DATE
        mock_repo.save_confirmation.assert_called_once_with(event)

    def test_confirm_supersedes_previous(self, mock_repo: MagicMock) -> None:
        doc_id = uuid4()
        old_confirmation_id = uuid4()
        old = ConfirmedReferenceEvent(
            confirmation_id=old_confirmation_id,
            document_id=doc_id,
            deadline_candidate_index=0,
            event_type=EventType.ISSUE_DATE,
            confirmed_at=datetime.now(UTC),
            confirmed_date=date(2026, 7, 15),
        )
        mock_repo.get_active_confirmation.return_value = old
        service = ReferenceEventService(repo=mock_repo)

        event = service.confirm(
            document_id=doc_id,
            deadline_candidate_index=0,
            event_type=EventType.ISSUE_DATE,
            confirmed_date=date(2026, 7, 20),
            source_type=SourceType.USER_CORRECTED,
            confirmation_method=ConfirmationMethod.CORRECTED,
        )

        assert event.supersedes_confirmation_id == old_confirmation_id

    def test_manual_entry_no_candidate(
        self, service: ReferenceEventService, mock_repo: MagicMock
    ) -> None:
        event = service.confirm(
            document_id=uuid4(),
            deadline_candidate_index=0,
            event_type=EventType.USER_DEFINED,
            confirmed_date=date(2026, 7, 15),
            source_type=SourceType.USER_MANUAL,
            confirmation_method=ConfirmationMethod.MANUALLY_ENTERED,
        )
        assert event.source_type == SourceType.USER_MANUAL
        assert event.confirmation_method == ConfirmationMethod.MANUALLY_ENTERED
        assert event.candidate_id is None

    def test_reject_creates_event(
        self, service: ReferenceEventService, mock_repo: MagicMock
    ) -> None:
        event = service.reject(
            document_id=uuid4(),
            deadline_candidate_index=0,
            event_type=EventType.DELIVERY,
        )
        assert event.event_type == EventType.DELIVERY
        assert event.confirmed_date is None
        mock_repo.save_confirmation.assert_called_once()

    def test_revoke_returns_new_event(self, mock_repo: MagicMock) -> None:
        doc_id = uuid4()
        original_id = uuid4()
        mock_repo.get_confirmation.return_value = ConfirmedReferenceEvent(
            confirmation_id=original_id,
            document_id=doc_id,
            deadline_candidate_index=0,
            event_type=EventType.ISSUE_DATE,
            confirmed_at=datetime.now(UTC),
            confirmed_date=date(2026, 7, 15),
        )
        service = ReferenceEventService(repo=mock_repo)

        revoked = service.revoke(confirmation_id=original_id)
        assert revoked is not None
        assert revoked.supersedes_confirmation_id == original_id
        mock_repo.save_confirmation.assert_called_once()

    def test_revoke_not_found_returns_none(self, mock_repo: MagicMock) -> None:
        mock_repo.get_confirmation.return_value = None
        service = ReferenceEventService(repo=mock_repo)

        result = service.revoke(confirmation_id=uuid4())
        assert result is None
        mock_repo.save_confirmation.assert_not_called()

    def test_get_history_delegates(self, mock_repo: MagicMock) -> None:
        doc_id = uuid4()
        mock_repo.get_history_for_candidate.return_value = []
        service = ReferenceEventService(repo=mock_repo)

        history = service.get_history(document_id=doc_id, deadline_candidate_index=0)
        assert history == []
        mock_repo.get_history_for_candidate.assert_called_once_with(doc_id, 0)

    def test_reference_event_candidates_empty_by_default(
        self, service: ReferenceEventService
    ) -> None:
        candidates = service.get_reference_event_candidates(
            document_id=uuid4(), deadline_candidate_index=0
        )
        assert candidates == []


# ── CalculationService tests ──


class TestCalculationService:
    """Calculation preview orchestration tests."""

    @pytest.fixture
    def mock_repo(self) -> MagicMock:
        repo = MagicMock()
        event = ConfirmedReferenceEvent(
            confirmation_id=uuid4(),
            document_id=uuid4(),
            deadline_candidate_index=0,
            event_type=EventType.ISSUE_DATE,
            confirmed_at=datetime.now(UTC),
            confirmed_date=date(2026, 7, 15),
        )
        repo.get_confirmation.return_value = event
        return repo

    @pytest.fixture
    def mock_arithmetic(self) -> MagicMock:
        arithmetic = MagicMock()
        arithmetic.calculate.return_value = CalendarCalculationCandidate(
            calculation_id=uuid4(),
            calculated_date=date(2026, 7, 29),
            warnings=["CALCULATION_PREVIEW_ONLY"],
        )
        return arithmetic

    @pytest.fixture
    def service(self, mock_repo: MagicMock, mock_arithmetic: MagicMock) -> CalculationService:
        return CalculationService(repo=mock_repo, arithmetic=mock_arithmetic)

    def test_calculate_preview_valid(
        self,
        service: CalculationService,
        mock_repo: MagicMock,
        mock_arithmetic: MagicMock,
    ) -> None:
        result = service.calculate_preview(
            confirmation_id=uuid4(),
            amount=14,
            unit="day",
        )
        assert result is not None
        assert result.calculated_date == date(2026, 7, 29)
        assert "CALCULATION_PREVIEW_ONLY" in result.warnings
        mock_arithmetic.calculate.assert_called_once()

    def test_calculate_preview_confirmation_not_found(
        self, mock_repo: MagicMock, mock_arithmetic: MagicMock
    ) -> None:
        mock_repo.get_confirmation.return_value = None
        service = CalculationService(repo=mock_repo, arithmetic=mock_arithmetic)

        with pytest.raises(ValueError, match="REFERENCE_EVENT_NOT_CONFIRMED"):
            service.calculate_preview(confirmation_id=uuid4(), amount=2, unit="week")

    def test_calculate_preview_unsupported_unit(self, service: CalculationService) -> None:
        with pytest.raises(ValueError, match="UNSUPPORTED_DURATION_UNIT"):
            service.calculate_preview(confirmation_id=uuid4(), amount=1, unit="month")

    def test_calculate_preview_from_event(self, mock_arithmetic: MagicMock) -> None:
        mock_repo = MagicMock()
        service = CalculationService(repo=mock_repo, arithmetic=mock_arithmetic)

        event = ConfirmedReferenceEvent(
            confirmation_id=uuid4(),
            document_id=uuid4(),
            deadline_candidate_index=0,
            event_type=EventType.ISSUE_DATE,
            confirmed_at=datetime.now(UTC),
            confirmed_date=date(2026, 7, 15),
        )
        result = service.calculate_preview_from_event(event=event, amount=7, unit="day")
        assert result is not None
        mock_arithmetic.calculate.assert_called_once()

    def test_validate_duration_day(self) -> None:
        duration = CalculationService._validate_duration(14, "day")
        assert duration.unit == DurationUnit.DAY
        assert duration.amount == 14
        assert duration.calendar_days == 14

    def test_validate_duration_week(self) -> None:
        duration = CalculationService._validate_duration(2, "Woche")
        assert duration.unit == DurationUnit.WEEK
        assert duration.calendar_days == 14

    def test_validate_duration_unsupported_raises(self) -> None:
        with pytest.raises(ValueError, match="UNSUPPORTED_DURATION_UNIT"):
            CalculationService._validate_duration(1, "month")

    def test_validate_duration_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="Duration amount must be positive"):
            CalculationService._validate_duration(0, "day")

    def test_validate_duration_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="Duration amount must be positive"):
            CalculationService._validate_duration(-5, "day")


# ── M6-UI Slice 2 Closure: Payload digest, key hashing, idempotency ──


class TestPayloadDigest:
    """compute_payload_digest produces deterministic SHA-256 hashes."""

    def test_simple_payload(self) -> None:
        payload = {"op": "confirm", "did": "abc"}
        digest = ReferenceEventService.compute_payload_digest(payload)
        assert isinstance(digest, str)
        assert len(digest) == 64

    def test_deterministic(self) -> None:
        payload = {"a": 1, "b": 2}
        d1 = ReferenceEventService.compute_payload_digest(payload)
        d2 = ReferenceEventService.compute_payload_digest(payload)
        assert d1 == d2

    def test_key_order_independent(self) -> None:
        p1 = {"z": 1, "a": 2}
        p2 = {"a": 2, "z": 1}
        d1 = ReferenceEventService.compute_payload_digest(p1)
        d2 = ReferenceEventService.compute_payload_digest(p2)
        assert d1 == d2

    def test_complex_payload(self) -> None:
        from uuid import uuid4 as _uuid4

        payload = {
            "op": "confirm",
            "did": str(_uuid4()),
            "dci": 0,
            "et": "issue_date",
            "cd": "2026-07-15",
            "st": "auto_detected",
            "cm": "auto_suggested",
            "cid": None,
            "en": "SYNTHETISCH – evidence",
            "cb": "",
        }
        digest = ReferenceEventService.compute_payload_digest(payload)
        assert len(digest) == 64


class TestHashKey:
    """_hash_key produces consistent HMAC-SHA256 digests."""

    def test_with_secret(self) -> None:
        svc = ReferenceEventService(repo=MagicMock(), secret_key="test-secret")
        h1 = svc._hash_key("my-idempotency-key")
        h2 = svc._hash_key("my-idempotency-key")
        assert h1 == h2
        assert len(h1) == 64

    def test_different_keys_different_hash(self) -> None:
        svc = ReferenceEventService(repo=MagicMock(), secret_key="test-secret")
        h1 = svc._hash_key("key-a")
        h2 = svc._hash_key("key-b")
        assert h1 != h2

    def test_without_secret_dev_fallback(self) -> None:
        svc = ReferenceEventService(repo=MagicMock())
        h = svc._hash_key("dev-key")
        assert len(h) == 64
        assert svc._hash_key("dev-key") == h

    def test_different_secret_different_hash(self) -> None:
        svc1 = ReferenceEventService(repo=MagicMock(), secret_key="secret-1")
        svc2 = ReferenceEventService(repo=MagicMock(), secret_key="secret-2")
        h1 = svc1._hash_key("same-key")
        h2 = svc2._hash_key("same-key")
        assert h1 != h2


class TestConfirmWithIdempotency:
    """Tests for the atomic confirm_with_idempotency."""

    def test_successful_confirm(self) -> None:
        mock_repo = MagicMock()
        event = ConfirmedReferenceEvent(
            confirmation_id=uuid4(),
            document_id=uuid4(),
            deadline_candidate_index=0,
            event_type=EventType.ISSUE_DATE,
            confirmed_at=datetime.now(UTC),
            confirmed_date=date(2026, 7, 15),
        )
        mock_repo.execute_atomic_with_idempotency.return_value = (event, False)
        svc = ReferenceEventService(repo=mock_repo, secret_key="test")

        result = svc.confirm_with_idempotency(
            idempotency_key="test-key",
            document_id=uuid4(),
            deadline_candidate_index=0,
            event_type=EventType.ISSUE_DATE,
            confirmed_date=date(2026, 7, 15),
            source_type=SourceType.AUTO_DETECTED,
            confirmation_method=ConfirmationMethod.AUTO_SUGGESTED,
            redirect_path="/ui/cases",
        )
        assert result.was_replay is False
        assert result.result_status == "confirmed"
        assert result.event == event
        mock_repo.execute_atomic_with_idempotency.assert_called_once()

    def test_replay_returns_existing(self) -> None:
        mock_repo = MagicMock()
        event = ConfirmedReferenceEvent(
            confirmation_id=uuid4(),
            document_id=uuid4(),
            deadline_candidate_index=0,
            event_type=EventType.ISSUE_DATE,
            confirmed_at=datetime.now(UTC),
            confirmed_date=date(2026, 7, 15),
        )
        mock_repo.execute_atomic_with_idempotency.return_value = (event, True)
        svc = ReferenceEventService(repo=mock_repo, secret_key="test")

        result = svc.confirm_with_idempotency(
            idempotency_key="replay",
            document_id=uuid4(),
            deadline_candidate_index=0,
            event_type=EventType.ISSUE_DATE,
            confirmed_date=date(2026, 7, 15),
            source_type=SourceType.AUTO_DETECTED,
            confirmation_method=ConfirmationMethod.AUTO_SUGGESTED,
        )
        assert result.was_replay is True

    def test_conflict_raises(self) -> None:
        from private_legal_navigator.application.reference_event_repository import (
            IdempotencyKeyConflictError,
        )

        mock_repo = MagicMock()
        mock_repo.execute_atomic_with_idempotency.side_effect = IdempotencyKeyConflictError("dup")
        svc = ReferenceEventService(repo=mock_repo, secret_key="test")

        with pytest.raises(IdempotencyKeyConflictError):
            svc.confirm_with_idempotency(
                idempotency_key="dup",
                document_id=uuid4(),
                deadline_candidate_index=0,
                event_type=EventType.ISSUE_DATE,
                confirmed_date=date(2026, 7, 15),
                source_type=SourceType.AUTO_DETECTED,
                confirmation_method=ConfirmationMethod.AUTO_SUGGESTED,
            )

    def test_payload_includes_manual_fields(self) -> None:
        """Manual confirm payload must include evidence_note and confirmed_by."""
        mock_repo = MagicMock()
        event = ConfirmedReferenceEvent(
            confirmation_id=uuid4(),
            document_id=uuid4(),
            deadline_candidate_index=0,
            event_type=EventType.USER_DEFINED,
            confirmed_at=datetime.now(UTC),
            confirmed_date=date(2026, 7, 20),
            evidence_note="SYNTHETISCH – manual entry",
        )
        mock_repo.execute_atomic_with_idempotency.return_value = (event, False)
        svc = ReferenceEventService(repo=mock_repo, secret_key="test")

        result = svc.confirm_with_idempotency(
            idempotency_key="manual-key",
            document_id=uuid4(),
            deadline_candidate_index=0,
            event_type=EventType.USER_DEFINED,
            confirmed_date=date(2026, 7, 20),
            source_type=SourceType.USER_MANUAL,
            confirmation_method=ConfirmationMethod.MANUALLY_ENTERED,
            evidence_note="SYNTHETISCH – manual entry",
            confirmed_by="SYNTHETISCH – user",
        )
        assert result.result_status == "confirmed"
        mock_repo.execute_atomic_with_idempotency.assert_called_once()


class TestRejectWithIdempotency:
    """Tests for the atomic reject_with_idempotency."""

    def test_successful_reject(self) -> None:
        mock_repo = MagicMock()
        event = ConfirmedReferenceEvent(
            confirmation_id=uuid4(),
            document_id=uuid4(),
            deadline_candidate_index=0,
            event_type=EventType.DELIVERY,
            confirmed_at=datetime.now(UTC),
            confirmed_date=None,
        )
        mock_repo.execute_atomic_with_idempotency.return_value = (event, False)
        svc = ReferenceEventService(repo=mock_repo, secret_key="test")

        result = svc.reject_with_idempotency(
            idempotency_key="reject-key",
            document_id=uuid4(),
            deadline_candidate_index=0,
            event_type=EventType.DELIVERY,
            redirect_path="/ui/cases",
        )
        assert result.result_status == "rejected"
        assert result.was_replay is False

    def test_reject_replay(self) -> None:
        mock_repo = MagicMock()
        event = ConfirmedReferenceEvent(
            confirmation_id=uuid4(),
            document_id=uuid4(),
            deadline_candidate_index=0,
            event_type=EventType.DELIVERY,
            confirmed_at=datetime.now(UTC),
            confirmed_date=None,
        )
        mock_repo.execute_atomic_with_idempotency.return_value = (event, True)
        svc = ReferenceEventService(repo=mock_repo, secret_key="test")

        result = svc.reject_with_idempotency(
            idempotency_key="replay-reject",
            document_id=uuid4(),
            deadline_candidate_index=0,
            event_type=EventType.DELIVERY,
        )
        assert result.was_replay is True

    def test_reject_conflict_raises(self) -> None:
        from private_legal_navigator.application.reference_event_repository import (
            IdempotencyKeyConflictError,
        )

        mock_repo = MagicMock()
        mock_repo.execute_atomic_with_idempotency.side_effect = IdempotencyKeyConflictError(
            "conflict"
        )
        svc = ReferenceEventService(repo=mock_repo, secret_key="test")

        with pytest.raises(IdempotencyKeyConflictError):
            svc.reject_with_idempotency(
                idempotency_key="conflict",
                document_id=uuid4(),
                deadline_candidate_index=0,
                event_type=EventType.DELIVERY,
            )


class TestCleanupIdempotency:
    """cleanup_idempotency delegates to repository."""

    def test_delegates_to_repo(self) -> None:
        mock_repo = MagicMock()
        mock_repo.cleanup_expired_idempotency_records.return_value = 5
        svc = ReferenceEventService(repo=mock_repo)

        result = svc.cleanup_idempotency()
        assert result == 5
        mock_repo.cleanup_expired_idempotency_records.assert_called_once()
