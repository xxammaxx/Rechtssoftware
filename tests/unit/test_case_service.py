"""Unit tests for the CaseService application layer."""

import uuid
from unittest.mock import MagicMock

import pytest

from private_legal_navigator.application.case_service import CaseService
from private_legal_navigator.domain.case import Case


class TestCaseService:
    """Tests for CaseService using a mocked repository."""

    @pytest.fixture
    def mock_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def service(self, mock_repo: MagicMock) -> CaseService:
        return CaseService(mock_repo)

    def test_create_case_generates_uuid(self, service: CaseService, mock_repo: MagicMock) -> None:
        """create_case should return a case with a server-generated UUID."""
        result = service.create_case(title="SYNTHETISCH – Service-Test")

        assert isinstance(result.case_id, uuid.UUID)
        assert result.title == "SYNTHETISCH – Service-Test"
        assert result.status == "open"
        mock_repo.save.assert_called_once_with(result)

    def test_create_case_trims_title(self, service: CaseService, mock_repo: MagicMock) -> None:
        """create_case should trim the title."""
        result = service.create_case(title="  SYNTHETISCH – Trim  ")
        assert result.title == "SYNTHETISCH – Trim"

    def test_create_case_empty_title_raises(
        self, service: CaseService, mock_repo: MagicMock
    ) -> None:
        """create_case with empty title should raise ValueError."""
        with pytest.raises(ValueError, match="Titel darf nicht leer sein"):
            service.create_case(title="")
        mock_repo.save.assert_not_called()

    def test_get_case_returns_case(
        self, service: CaseService, mock_repo: MagicMock
    ) -> None:
        """get_case should return the case from the repository."""
        case = Case(title="SYNTHETISCH – Get")
        mock_repo.get_by_id.return_value = case

        result = service.get_case(case.case_id)
        assert result == case
        mock_repo.get_by_id.assert_called_once_with(case.case_id)

    def test_get_case_returns_none_for_unknown(
        self, service: CaseService, mock_repo: MagicMock
    ) -> None:
        """get_case should return None for an unknown ID."""
        mock_repo.get_by_id.return_value = None
        unknown_id = uuid.uuid4()

        result = service.get_case(unknown_id)
        assert result is None

    def test_list_cases_delegates_to_repo(
        self, service: CaseService, mock_repo: MagicMock
    ) -> None:
        """list_cases should delegate to the repository."""
        cases = [Case(title="SYNTHETISCH – A"), Case(title="SYNTHETISCH – B")]
        mock_repo.list_all.return_value = cases

        result = service.list_cases()
        assert result == cases
        assert len(result) == 2

    def test_list_cases_empty(self, service: CaseService, mock_repo: MagicMock) -> None:
        """list_cases should return an empty list when repository is empty."""
        mock_repo.list_all.return_value = []
        result = service.list_cases()
        assert result == []
