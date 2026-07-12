"""Integration tests for the SQLite CaseRepository implementation."""

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from private_legal_navigator.domain.case import Case
from private_legal_navigator.infrastructure.sqlite_case_repository import (
    SqliteCaseRepository,
)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Provide a temporary database path."""
    return tmp_path / "test.db"


@pytest.fixture
def repository(db_path: Path) -> SqliteCaseRepository:
    """Provide a fresh repository connected to a temporary database."""
    repo = SqliteCaseRepository(db_path)
    repo.initialize_schema()
    return repo


def _make_case(title: str = "SYNTHETISCH – Repo-Test") -> Case:
    """Create a test case with stable timestamps."""
    return Case(
        title=title,
        created_at=datetime(2026, 7, 12, 10, 0, 0, tzinfo=UTC),
        updated_at=datetime(2026, 7, 12, 10, 0, 0, tzinfo=UTC),
    )


class TestSchemaInitialization:
    """Tests for database schema setup."""

    def test_schema_creates_table(self, db_path: Path) -> None:
        """The schema initialization should create the cases table."""
        repo = SqliteCaseRepository(db_path)
        repo.initialize_schema()

        # Verify the table exists by listing tables
        import sqlite3

        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='cases'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_initialize_schema_is_idempotent(self, repository: SqliteCaseRepository) -> None:
        """Calling initialize_schema twice should not raise an error."""
        repository.initialize_schema()  # Should not raise


class TestSaveAndRetrieve:
    """Tests for saving and retrieving cases."""

    def test_save_and_get_by_id(self, repository: SqliteCaseRepository) -> None:
        """Saving a case and retrieving it by ID should return the same data."""
        case = _make_case("SYNTHETISCH – Speichern und Laden")
        repository.save(case)

        retrieved = repository.get_by_id(case.case_id)
        assert retrieved is not None
        assert retrieved.case_id == case.case_id
        assert retrieved.title == case.title
        assert retrieved.status == case.status

    def test_list_all_returns_all_cases(self, repository: SqliteCaseRepository) -> None:
        """list_all should return all saved cases."""
        case1 = _make_case("SYNTHETISCH – Alpha")
        case2 = _make_case("SYNTHETISCH – Beta")
        repository.save(case1)
        repository.save(case2)

        cases = repository.list_all()
        assert len(cases) == 2
        titles = {c.title for c in cases}
        assert "SYNTHETISCH – Alpha" in titles
        assert "SYNTHETISCH – Beta" in titles

    def test_list_all_returns_empty_list(self, repository: SqliteCaseRepository) -> None:
        """list_all on an empty database should return an empty list."""
        cases = repository.list_all()
        assert cases == []

    def test_get_by_id_returns_none_for_unknown(self, repository: SqliteCaseRepository) -> None:
        """get_by_id for a non-existent ID should return None."""
        unknown_id = uuid.uuid4()
        result = repository.get_by_id(unknown_id)
        assert result is None

    def test_persistence_survives_reconnect(self, db_path: Path) -> None:
        """Data should persist after closing and reopening the connection."""
        # First connection: save a case
        repo1 = SqliteCaseRepository(db_path)
        repo1.initialize_schema()
        case = _make_case("SYNTHETISCH – Persistenz")
        repo1.save(case)

        # Second connection: retrieve the case
        repo2 = SqliteCaseRepository(db_path)
        retrieved = repo2.get_by_id(case.case_id)
        assert retrieved is not None
        assert retrieved.title == "SYNTHETISCH – Persistenz"
