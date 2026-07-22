"""Unit tests for LocalConfirmationWorkspaceService."""

import uuid

import pytest

from private_legal_navigator.application.local_confirmation_workspace_service import (
    LocalConfirmationWorkspaceService,
)
from private_legal_navigator.domain.case import Case
from private_legal_navigator.domain.document import Document


class FakeCaseRepository:
    """In-memory fake for CaseRepository."""

    def __init__(self) -> None:
        self._cases: dict[uuid.UUID, Case] = {}

    def save(self, case: Case) -> None:
        self._cases[case.case_id] = case

    def get_by_id(self, case_id: uuid.UUID) -> Case | None:
        return self._cases.get(case_id)

    def list_all(self) -> list[Case]:
        return list(self._cases.values())


class FakeDocumentRepository:
    """In-memory fake for DocumentRepository."""

    def __init__(self) -> None:
        self._docs: dict[uuid.UUID, Document] = {}

    def save(self, doc: Document) -> None:
        self._docs[doc.document_id] = doc

    def get_by_id(self, document_id: uuid.UUID) -> Document | None:
        return self._docs.get(document_id)

    def list_by_case(self, case_id: uuid.UUID) -> list[Document]:
        return [d for d in self._docs.values() if d.case_id == case_id]


@pytest.fixture
def case_repo() -> FakeCaseRepository:
    return FakeCaseRepository()


@pytest.fixture
def doc_repo() -> FakeDocumentRepository:
    return FakeDocumentRepository()


@pytest.fixture
def svc(
    case_repo: FakeCaseRepository, doc_repo: FakeDocumentRepository
) -> LocalConfirmationWorkspaceService:
    """Create a workspace service with fake repos and a real document service."""
    from unittest.mock import MagicMock

    from private_legal_navigator.application.document_service import DocumentService

    # Create a DocumentService that uses our fake repos
    mock_file_storage = MagicMock()
    mock_text_extractor = MagicMock()
    mock_classifier = MagicMock()
    doc_svc = DocumentService(
        doc_repo,
        mock_file_storage,
        case_repo,
        mock_text_extractor,
        mock_classifier,
    )

    return LocalConfirmationWorkspaceService(
        case_repository=case_repo,
        document_repository=doc_repo,
        document_service=doc_svc,
        deadline_service=MagicMock(),
        reference_event_service=MagicMock(),
    )


class TestCaseListing:
    """Tests for workspace service case listing."""

    def test_empty_case_list(self, svc: LocalConfirmationWorkspaceService) -> None:
        view = svc.list_cases()
        assert view.case_count == 0
        assert view.has_cases is False
        assert view.cases == []

    def test_case_list_with_items(
        self, svc: LocalConfirmationWorkspaceService, case_repo: FakeCaseRepository
    ) -> None:
        from datetime import datetime

        c1 = Case(
            case_id=uuid.uuid4(),
            title="SYNTHETISCH – Fall 1",
            status="Offen",
            created_at=datetime(2025, 1, 1),
            updated_at=datetime(2025, 1, 1),
        )
        c2 = Case(
            case_id=uuid.uuid4(),
            title="SYNTHETISCH – Fall 2",
            status="Geschlossen",
            created_at=datetime(2025, 2, 1),
            updated_at=datetime(2025, 2, 1),
        )
        case_repo.save(c1)
        case_repo.save(c2)

        view = svc.list_cases()
        assert view.case_count == 2
        assert view.has_cases is True
        assert len(view.cases) == 2
        assert view.cases[0].title == "SYNTHETISCH – Fall 1"
        assert view.cases[0].status == "Offen"

    def test_case_list_includes_document_count(
        self,
        svc: LocalConfirmationWorkspaceService,
        case_repo: FakeCaseRepository,
        doc_repo: FakeDocumentRepository,
    ) -> None:
        from datetime import datetime

        cid = uuid.uuid4()
        case_repo.save(
            Case(
                case_id=cid,
                title="SYNTHETISCH – Fall",
                status="Offen",
                created_at=datetime(2025, 1, 1),
                updated_at=datetime(2025, 1, 1),
            )
        )
        doc_repo.save(
            Document(
                document_id=uuid.uuid4(),
                case_id=cid,
                filename="doc1.pdf",
                mime_type="application/pdf",
                size_bytes=100,
                storage_path="/tmp/doc1.pdf",
                created_at=datetime(2025, 1, 1),
            )
        )
        doc_repo.save(
            Document(
                document_id=uuid.uuid4(),
                case_id=cid,
                filename="doc2.pdf",
                mime_type="application/pdf",
                size_bytes=200,
                storage_path="/tmp/doc2.pdf",
                created_at=datetime(2025, 1, 2),
            )
        )

        view = svc.list_cases()
        assert view.cases[0].document_count == 2


class TestCaseDetail:
    """Tests for workspace service case detail."""

    def test_get_existing_case(
        self, svc: LocalConfirmationWorkspaceService, case_repo: FakeCaseRepository
    ) -> None:
        from datetime import datetime

        cid = uuid.uuid4()
        case_repo.save(
            Case(
                case_id=cid,
                title="SYNTHETISCH – Detail",
                status="Offen",
                created_at=datetime(2025, 1, 1),
                updated_at=datetime(2025, 1, 1),
            )
        )

        view = svc.get_case(cid)
        assert view is not None
        assert view.case_id == str(cid)
        assert view.title == "SYNTHETISCH – Detail"
        assert view.status == "Offen"
        assert view.has_documents is False

    def test_get_nonexistent_case(self, svc: LocalConfirmationWorkspaceService) -> None:
        view = svc.get_case(uuid.uuid4())
        assert view is None

    def test_case_detail_with_documents(
        self,
        svc: LocalConfirmationWorkspaceService,
        case_repo: FakeCaseRepository,
        doc_repo: FakeDocumentRepository,
    ) -> None:
        from datetime import datetime

        cid = uuid.uuid4()
        case_repo.save(
            Case(
                case_id=cid,
                title="SYNTHETISCH – Mit Doks",
                status="Offen",
                created_at=datetime(2025, 1, 1),
                updated_at=datetime(2025, 1, 1),
            )
        )
        doc_repo.save(
            Document(
                document_id=uuid.uuid4(),
                case_id=cid,
                filename="a.pdf",
                mime_type="application/pdf",
                size_bytes=100,
                storage_path="/tmp/a.pdf",
                created_at=datetime(2025, 1, 1),
                text_content="Some text",
            )
        )

        view = svc.get_case(cid)
        assert view is not None
        assert view.has_documents is True
        assert len(view.documents) == 1
        assert view.documents[0].has_text is True
        assert view.documents[0].classification == "sonstiges"


class TestCalculatePreview:
    """Tests for calculate_preview error paths."""

    def test_calculate_preview_raises_without_arithmetic(
        self, svc: LocalConfirmationWorkspaceService
    ) -> None:
        """calculate_preview raises ValueError when calendar_arithmetic is None."""
        with pytest.raises(ValueError, match="Rechenvorschau ist nicht verfügbar."):
            svc.calculate_preview(
                case_id=uuid.uuid4(),
                document_id=uuid.uuid4(),
                candidate_index=0,
                expected_active_confirmation_id=str(uuid.uuid4()),
            )
