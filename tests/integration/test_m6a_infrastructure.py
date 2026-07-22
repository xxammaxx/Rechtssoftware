"""Integration tests for M6-A infrastructure layer."""

import uuid
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from private_legal_navigator.domain.reference_event import (
    ConfirmationMethod,
    ConfirmedReferenceEvent,
    Duration,
    DurationUnit,
    EventType,
    SourceType,
)
from private_legal_navigator.infrastructure.database import get_connection, initialize_schema
from private_legal_navigator.infrastructure.deterministic_calendar_arithmetic import (
    DeterministicCalendarArithmetic,
)
from private_legal_navigator.infrastructure.sqlite_reference_event_repository import (
    SqliteReferenceEventRepository,
)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "test_m6a.db"
    initialize_schema(path)
    # Create documents table for FK constraint
    from private_legal_navigator.infrastructure.database import get_connection

    conn = get_connection(path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            document_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            mime_type TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            storage_path TEXT NOT NULL,
            created_at TEXT NOT NULL,
            text_content TEXT NOT NULL DEFAULT '',
            doc_type TEXT NOT NULL DEFAULT 'sonstiges',
            classification_confidence REAL NOT NULL DEFAULT 0.0
        )
    """)
    conn.commit()
    conn.close()
    return path


def _create_document(db_path: Path, doc_id: uuid.UUID) -> None:
    """Helper to create a document record for FK constraint."""
    case_id = uuid.uuid4()
    conn = get_connection(db_path)
    # Create parent case first to satisfy FK constraint
    conn.execute(
        """INSERT OR IGNORE INTO cases
           (case_id, title, status, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?)""",
        (
            str(case_id),
            "SYNTHETISCH – Test Case",
            "open",
            "2026-01-01T00:00:00Z",
            "2026-01-01T00:00:00Z",
        ),
    )
    conn.execute(
        """INSERT OR IGNORE INTO documents
           (document_id, case_id, filename, mime_type, size_bytes, storage_path, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            str(doc_id),
            str(case_id),
            "test.pdf",
            "application/pdf",
            100,
            "/tmp/test.pdf",
            "2026-01-01T00:00:00Z",
        ),
    )
    conn.commit()
    conn.close()


@pytest.fixture
def repo(db_path: Path) -> SqliteReferenceEventRepository:
    return SqliteReferenceEventRepository(db_path)


@pytest.fixture
def arithmetic() -> DeterministicCalendarArithmetic:
    return DeterministicCalendarArithmetic()


@pytest.fixture
def doc_id(db_path: Path) -> uuid.UUID:
    _id = uuid.uuid4()
    _create_document(db_path, _id)
    return _id


# ── SQLite Repository Tests ──


class TestSqliteReferenceEventRepository:
    """SQLite repository integration tests."""

    def test_save_and_get_confirmation(
        self, repo: SqliteReferenceEventRepository, doc_id: uuid.UUID
    ) -> None:
        now = datetime.now(UTC)
        event = ConfirmedReferenceEvent(
            confirmation_id=uuid.uuid4(),
            document_id=doc_id,
            deadline_candidate_index=0,
            event_type=EventType.ISSUE_DATE,
            confirmed_at=now,
            confirmed_date=date(2026, 7, 15),
            source_type=SourceType.AUTO_DETECTED,
            confirmation_method=ConfirmationMethod.AUTO_SUGGESTED,
        )
        repo.save_confirmation(event)

        loaded = repo.get_confirmation(event.confirmation_id)
        assert loaded is not None
        assert loaded.confirmation_id == event.confirmation_id
        assert loaded.confirmed_date == date(2026, 7, 15)
        assert loaded.event_type == EventType.ISSUE_DATE

    def test_get_nonexistent_confirmation(self, repo: SqliteReferenceEventRepository) -> None:
        result = repo.get_confirmation(uuid.uuid4())
        assert result is None

    def test_save_manual_entry(
        self, repo: SqliteReferenceEventRepository, doc_id: uuid.UUID
    ) -> None:
        now = datetime.now(UTC)
        event = ConfirmedReferenceEvent(
            confirmation_id=uuid.uuid4(),
            document_id=doc_id,
            deadline_candidate_index=0,
            event_type=EventType.USER_DEFINED,
            confirmed_at=now,
            confirmed_date=date(2026, 7, 20),
            source_type=SourceType.USER_MANUAL,
            confirmation_method=ConfirmationMethod.MANUALLY_ENTERED,
            candidate_id=None,
        )
        repo.save_confirmation(event)

        loaded = repo.get_confirmation(event.confirmation_id)
        assert loaded is not None
        assert loaded.candidate_id is None
        assert loaded.confirmation_method == ConfirmationMethod.MANUALLY_ENTERED

    def test_get_history_for_candidate(
        self, repo: SqliteReferenceEventRepository, doc_id: uuid.UUID
    ) -> None:
        now = datetime.now(UTC)
        first = ConfirmedReferenceEvent(
            confirmation_id=uuid.uuid4(),
            document_id=doc_id,
            deadline_candidate_index=0,
            event_type=EventType.ISSUE_DATE,
            confirmed_at=now,
            confirmed_date=date(2026, 7, 15),
        )
        second = ConfirmedReferenceEvent(
            confirmation_id=uuid.uuid4(),
            document_id=doc_id,
            deadline_candidate_index=0,
            event_type=EventType.ISSUE_DATE,
            confirmed_at=now,
            confirmed_date=date(2026, 7, 20),
            supersedes_confirmation_id=first.confirmation_id,
        )
        repo.save_confirmation(first)
        repo.save_confirmation(second)

        history = repo.get_history_for_candidate(doc_id, 0)
        assert len(history) == 2

    def test_history_empty(self, repo: SqliteReferenceEventRepository) -> None:
        history = repo.get_history_for_candidate(uuid.uuid4(), 0)
        assert history == []

    def test_delete_by_document(
        self, repo: SqliteReferenceEventRepository, doc_id: uuid.UUID
    ) -> None:
        now = datetime.now(UTC)
        event = ConfirmedReferenceEvent(
            confirmation_id=uuid.uuid4(),
            document_id=doc_id,
            deadline_candidate_index=0,
            event_type=EventType.ISSUE_DATE,
            confirmed_at=now,
            confirmed_date=date(2026, 7, 15),
        )
        repo.save_confirmation(event)
        repo.delete_by_document(doc_id)

        loaded = repo.get_confirmation(event.confirmation_id)
        assert loaded is None

    def test_active_confirmation(
        self, repo: SqliteReferenceEventRepository, doc_id: uuid.UUID
    ) -> None:
        now = datetime.now(UTC)
        first = ConfirmedReferenceEvent(
            confirmation_id=uuid.uuid4(),
            document_id=doc_id,
            deadline_candidate_index=0,
            event_type=EventType.ISSUE_DATE,
            confirmed_at=now,
            confirmed_date=date(2026, 7, 15),
        )
        repo.save_confirmation(first)

        active = repo.get_active_confirmation(doc_id, 0)
        assert active is not None
        assert active.confirmation_id == first.confirmation_id

    def test_active_confirmation_none(self, repo: SqliteReferenceEventRepository) -> None:
        active = repo.get_active_confirmation(uuid.uuid4(), 0)
        assert active is None


# ── Calendar Arithmetic Tests ──


class TestDeterministicCalendarArithmetic:
    """Pure arithmetic tests."""

    def test_add_days(self, arithmetic: DeterministicCalendarArithmetic) -> None:
        event = ConfirmedReferenceEvent(
            confirmation_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            deadline_candidate_index=0,
            event_type=EventType.ISSUE_DATE,
            confirmed_at=datetime.now(UTC),
            confirmed_date=date(2026, 7, 15),
        )
        duration = Duration(amount=14, unit=DurationUnit.DAY)
        result = arithmetic.calculate(event, duration)

        assert result.calculated_date == date(2026, 7, 29)
        assert len(result.calculation_steps) == 1
        assert result.calculation_steps[0].operation == "ADD_CALENDAR_DAYS"
        assert result.calculation_steps[0].amount == 14
        assert result.legal_validity_assessed is False
        assert result.human_review_required is True

    def test_add_weeks(self, arithmetic: DeterministicCalendarArithmetic) -> None:
        event = ConfirmedReferenceEvent(
            confirmation_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            deadline_candidate_index=0,
            event_type=EventType.ISSUE_DATE,
            confirmed_at=datetime.now(UTC),
            confirmed_date=date(2026, 7, 15),
        )
        duration = Duration(amount=2, unit=DurationUnit.WEEK)
        result = arithmetic.calculate(event, duration)

        assert result.calculated_date == date(2026, 7, 29)
        assert result.calculation_steps[0].operation == "ADD_CALENDAR_WEEKS"

    def test_year_boundary(self, arithmetic: DeterministicCalendarArithmetic) -> None:
        event = ConfirmedReferenceEvent(
            confirmation_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            deadline_candidate_index=0,
            event_type=EventType.ISSUE_DATE,
            confirmed_at=datetime.now(UTC),
            confirmed_date=date(2026, 12, 31),
        )
        duration = Duration(amount=1, unit=DurationUnit.DAY)
        result = arithmetic.calculate(event, duration)

        assert result.calculated_date == date(2027, 1, 1)

    def test_leap_year(self, arithmetic: DeterministicCalendarArithmetic) -> None:
        event = ConfirmedReferenceEvent(
            confirmation_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            deadline_candidate_index=0,
            event_type=EventType.ISSUE_DATE,
            confirmed_at=datetime.now(UTC),
            confirmed_date=date(2024, 2, 28),
        )
        duration = Duration(amount=1, unit=DurationUnit.DAY)
        result = arithmetic.calculate(event, duration)

        assert result.calculated_date == date(2024, 2, 29)

    def test_non_leap_year(self, arithmetic: DeterministicCalendarArithmetic) -> None:
        event = ConfirmedReferenceEvent(
            confirmation_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            deadline_candidate_index=0,
            event_type=EventType.ISSUE_DATE,
            confirmed_at=datetime.now(UTC),
            confirmed_date=date(2025, 2, 28),
        )
        duration = Duration(amount=1, unit=DurationUnit.DAY)
        result = arithmetic.calculate(event, duration)

        assert result.calculated_date == date(2025, 3, 1)

    def test_out_of_range_raises(self, arithmetic: DeterministicCalendarArithmetic) -> None:
        event = ConfirmedReferenceEvent(
            confirmation_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            deadline_candidate_index=0,
            event_type=EventType.ISSUE_DATE,
            confirmed_at=datetime.now(UTC),
            confirmed_date=date(2099, 12, 31),
        )
        duration = Duration(amount=1, unit=DurationUnit.DAY)
        with pytest.raises(ValueError, match="CALCULATED_DATE_OUT_OF_RANGE"):
            arithmetic.calculate(event, duration)

    def test_safety_flags(self, arithmetic: DeterministicCalendarArithmetic) -> None:
        event = ConfirmedReferenceEvent(
            confirmation_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            deadline_candidate_index=0,
            event_type=EventType.ISSUE_DATE,
            confirmed_at=datetime.now(UTC),
            confirmed_date=date(2026, 7, 15),
        )
        duration = Duration(amount=7, unit=DurationUnit.DAY)
        result = arithmetic.calculate(event, duration)

        assert result.legal_validity_assessed is False
        assert result.human_review_required is True
        assert result.adjustments_applied["weekend_adjustment_applied"] is False
        assert result.adjustments_applied["holiday_adjustment_applied"] is False
        assert result.adjustments_applied["legal_rule_applied"] is False
        assert "CALCULATION_PREVIEW_ONLY" in result.warnings
        assert "HUMAN_REVIEW_REQUIRED" in result.warnings

    def test_deterministic_output(self, arithmetic: DeterministicCalendarArithmetic) -> None:
        event = ConfirmedReferenceEvent(
            confirmation_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            deadline_candidate_index=0,
            event_type=EventType.ISSUE_DATE,
            confirmed_at=datetime.now(UTC),
            confirmed_date=date(2026, 7, 15),
        )
        duration = Duration(amount=14, unit=DurationUnit.DAY)
        result1 = arithmetic.calculate(event, duration)
        result2 = arithmetic.calculate(event, duration)

        assert result1.calculated_date == result2.calculated_date
        assert result1.calculation_steps == result2.calculation_steps
