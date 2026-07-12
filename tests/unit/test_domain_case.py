"""Unit tests for the Case domain entity."""

import uuid
from datetime import UTC

import pytest

from private_legal_navigator.domain.case import Case, CaseStatus


class TestCaseCreation:
    """Tests for Case entity creation and validation."""

    def test_valid_case_creation(self) -> None:
        """A case with a valid title should be created successfully."""
        case = Case(title="SYNTHETISCH – Testfall")

        assert case.title == "SYNTHETISCH – Testfall"
        assert case.status == CaseStatus.OPEN
        assert isinstance(case.case_id, uuid.UUID)
        assert case.created_at.tzinfo == UTC
        assert case.updated_at.tzinfo == UTC

    def test_title_is_trimmed(self) -> None:
        """Leading and trailing whitespace should be stripped."""
        case = Case(title="  SYNTHETISCH – Mit Leerzeichen  ")
        assert case.title == "SYNTHETISCH – Mit Leerzeichen"

    def test_empty_title_raises(self) -> None:
        """An empty title should raise ValueError."""
        with pytest.raises(ValueError, match="Titel darf nicht leer sein"):
            Case(title="")

    def test_whitespace_only_title_raises(self) -> None:
        """A whitespace-only title should raise ValueError."""
        with pytest.raises(ValueError, match="Titel darf nicht leer sein"):
            Case(title="   \t\n   ")

    def test_title_too_long_raises(self) -> None:
        """A title longer than 200 characters should raise ValueError."""
        long_title = "A" * 201
        with pytest.raises(ValueError, match="Titel darf maximal 200 Zeichen"):
            Case(title=long_title)

    def test_title_exactly_200_chars(self) -> None:
        """A title of exactly 200 characters should be accepted."""
        title = "A" * 200
        case = Case(title=title)
        assert len(case.title) == 200

    def test_case_id_is_unique(self) -> None:
        """Each case should receive a unique UUID."""
        case1 = Case(title="SYNTHETISCH – Erster")
        case2 = Case(title="SYNTHETISCH – Zweiter")
        assert case1.case_id != case2.case_id

    def test_created_at_is_utc_aware(self) -> None:
        """created_at must be timezone-aware with UTC."""
        case = Case(title="SYNTHETISCH – UTC-Test")
        assert case.created_at.tzinfo is not None
        assert case.created_at.utcoffset() == UTC.utcoffset(None)

    def test_updated_at_equals_created_at_on_creation(self) -> None:
        """On creation, updated_at should equal created_at."""
        case = Case(title="SYNTHETISCH – Gleich")
        assert case.updated_at == case.created_at


class TestCaseStatus:
    """Tests for CaseStatus enum."""

    def test_default_status_is_open(self) -> None:
        """New cases should default to OPEN status."""
        case = Case(title="SYNTHETISCH – Status")
        assert case.status == CaseStatus.OPEN
        assert case.status == "open"

    def test_status_values(self) -> None:
        """CaseStatus should contain the expected value."""
        assert CaseStatus.OPEN == "open"
