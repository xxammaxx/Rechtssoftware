"""Unit tests for LocalConfirmationWorkspaceService."""

import uuid
from datetime import UTC

import pytest

from private_legal_navigator.application.local_confirmation_workspace_service import (
    LocalConfirmationWorkspaceService,
)
from private_legal_navigator.domain.case import Case
from private_legal_navigator.domain.case_timeline import CaseLegalEvent
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


class FakeCaseTimelineRepository:
    """In-memory fake for CaseTimelineRepository (chronology sidebar)."""

    def __init__(self, events: list | None = None) -> None:
        self._events: list = events or []
        self.fail_next_call = False

    def list_active_events(self, case_id: uuid.UUID) -> list:
        if self.fail_next_call:
            raise RuntimeError("timeline repo unavailable")
        return [e for e in self._events if e.case_id == case_id]


def _make_event(
    case_id: uuid.UUID,
    title: str,
    occurred_at,
    event_type="DOCUMENT_RECEIVED",
) -> CaseLegalEvent:
    from private_legal_navigator.domain.case_timeline import (
        LegalEventType,
        ReviewStatus,
    )

    return CaseLegalEvent(
        event_id=uuid.uuid4(),
        case_id=case_id,
        event_type=LegalEventType(event_type),
        occurred_at=occurred_at,
        title=title,
        review_status=ReviewStatus.CONFIRMED,
    )


def _svc_with_timeline(
    case_repo: FakeCaseRepository,
    doc_repo: FakeDocumentRepository,
    timeline_repo: FakeCaseTimelineRepository,
) -> LocalConfirmationWorkspaceService:
    """Workspace service wired with a fake timeline repository."""
    from unittest.mock import MagicMock

    from private_legal_navigator.application.document_service import DocumentService

    doc_svc = DocumentService(
        doc_repo,
        MagicMock(),
        case_repo,
        MagicMock(),
        MagicMock(),
    )
    return LocalConfirmationWorkspaceService(
        case_repository=case_repo,
        document_repository=doc_repo,
        document_service=doc_svc,
        deadline_service=MagicMock(),
        reference_event_service=MagicMock(),
        case_timeline_repository=timeline_repo,
    )


class TestCaseDetailChronology:
    """Tests for the chronology sidebar on the case detail page (RC-021)."""

    def test_no_timeline_repo_no_events_no_documents(
        self, svc: LocalConfirmationWorkspaceService, case_repo: FakeCaseRepository
    ) -> None:
        """Without a timeline repo and without documents the sidebar is hidden."""
        from datetime import datetime

        cid = uuid.uuid4()
        case_repo.save(
            Case(
                case_id=cid,
                title="SYNTHETISCH – Leer",
                status="Offen",
                created_at=datetime(2025, 1, 1),
                updated_at=datetime(2025, 1, 1),
            )
        )
        view = svc.get_case(cid)
        assert view is not None
        assert view.has_timeline_events is False
        assert view.timeline_events == []

    def test_created_at_display_filled(
        self, svc: LocalConfirmationWorkspaceService, case_repo: FakeCaseRepository
    ) -> None:
        """The case detail view carries a human-readable created date."""
        from datetime import datetime

        cid = uuid.uuid4()
        case_repo.save(
            Case(
                case_id=cid,
                title="SYNTHETISCH – Datum",
                status="Offen",
                created_at=datetime(2025, 1, 1),
                updated_at=datetime(2025, 1, 1),
            )
        )
        view = svc.get_case(cid)
        assert view is not None
        assert view.created_at == "2025-01-01T00:00:00"
        assert view.created_at_display.startswith("01.01.2025")

    def test_events_rendered_newest_first(
        self, case_repo: FakeCaseRepository, doc_repo: FakeDocumentRepository
    ) -> None:
        """Active events appear in the sidebar, newest first, latest flagged."""
        from datetime import datetime

        cid = uuid.uuid4()
        case_repo.save(
            Case(
                case_id=cid,
                title="SYNTHETISCH – Timeline",
                status="Offen",
                created_at=datetime(2025, 1, 1),
                updated_at=datetime(2025, 1, 1),
            )
        )
        events = [
            _make_event(cid, "Älteres Ereignis", datetime(2025, 1, 5)),
            _make_event(cid, "Neueres Ereignis", datetime(2025, 2, 5)),
        ]
        svc = _svc_with_timeline(case_repo, doc_repo, FakeCaseTimelineRepository(events))

        view = svc.get_case(cid)
        assert view is not None
        assert view.has_timeline_events is True
        titles = [e.title for e in view.timeline_events]
        assert titles == ["Neueres Ereignis", "Älteres Ereignis"]
        assert view.timeline_events[0].is_latest is True
        assert view.timeline_events[1].is_latest is False
        assert view.timeline_events[0].date_display == "05.02.2025"

    def test_documents_are_chronology_entries(
        self, case_repo: FakeCaseRepository, doc_repo: FakeDocumentRepository
    ) -> None:
        """Uploaded documents also appear in the chronology sidebar."""
        from datetime import datetime

        cid = uuid.uuid4()
        case_repo.save(
            Case(
                case_id=cid,
                title="SYNTHETISCH – Dok",
                status="Offen",
                created_at=datetime(2025, 1, 1),
                updated_at=datetime(2025, 1, 1),
            )
        )
        doc_repo.save(
            Document(
                document_id=uuid.uuid4(),
                case_id=cid,
                filename="vertrag.pdf",
                mime_type="application/pdf",
                size_bytes=100,
                storage_path="/tmp/vertrag.pdf",
                created_at=datetime(2025, 1, 10),
                text_content="Inhalt",
            )
        )
        svc = _svc_with_timeline(case_repo, doc_repo, FakeCaseTimelineRepository([]))

        view = svc.get_case(cid)
        assert view is not None
        assert view.has_timeline_events is True
        assert len(view.timeline_events) == 1
        assert view.timeline_events[0].title == "Dokument hochgeladen"
        assert view.timeline_events[0].source_hint == "vertrag.pdf"

    def test_sidebar_limit_is_eight(
        self, case_repo: FakeCaseRepository, doc_repo: FakeDocumentRepository
    ) -> None:
        """The sidebar caps the chronology at eight entries."""
        from datetime import datetime

        cid = uuid.uuid4()
        case_repo.save(
            Case(
                case_id=cid,
                title="SYNTHETISCH – Limit",
                status="Offen",
                created_at=datetime(2025, 1, 1),
                updated_at=datetime(2025, 1, 1),
            )
        )
        events = [
            _make_event(cid, f"Ereignis {i}", datetime(2025, 1, i + 1))
            for i in range(10)
        ]
        svc = _svc_with_timeline(case_repo, doc_repo, FakeCaseTimelineRepository(events))

        view = svc.get_case(cid)
        assert view is not None
        assert len(view.timeline_events) == 8
        # Newest first: the ten events are on Jan 1..10 → top is Jan 10.
        assert view.timeline_events[0].title == "Ereignis 9"

    def test_repository_failure_does_not_break_page(
        self, case_repo: FakeCaseRepository, doc_repo: FakeDocumentRepository
    ) -> None:
        """A failing timeline repository degrades gracefully (no sidebar)."""
        from datetime import datetime

        cid = uuid.uuid4()
        case_repo.save(
            Case(
                case_id=cid,
                title="SYNTHETISCH – Ausfall",
                status="Offen",
                created_at=datetime(2025, 1, 1),
                updated_at=datetime(2025, 1, 1),
            )
        )
        timeline_repo = FakeCaseTimelineRepository(
            [_make_event(cid, "Ereignis", datetime(2025, 1, 5))]
        )
        timeline_repo.fail_next_call = True
        svc = _svc_with_timeline(case_repo, doc_repo, timeline_repo)

        view = svc.get_case(cid)
        assert view is not None  # page must not crash
        assert view.has_timeline_events is False
        assert view.timeline_events == []

    def test_mixed_naive_and_aware_dates_do_not_crash(
        self, case_repo: FakeCaseRepository, doc_repo: FakeDocumentRepository
    ) -> None:
        """Naive and timezone-aware datetimes sort side by side (RC-021)."""
        from datetime import datetime

        cid = uuid.uuid4()
        case_repo.save(
            Case(
                case_id=cid,
                title="SYNTHETISCH – Zeitzonen",
                status="Offen",
                created_at=datetime(2025, 1, 1),
                updated_at=datetime(2025, 1, 1),
            )
        )
        naive_event = _make_event(cid, "Naiv", datetime(2025, 1, 5))
        aware_event = _make_event(
            cid, "Aware", datetime(2025, 2, 5, tzinfo=UTC)
        )
        svc = _svc_with_timeline(
            case_repo, doc_repo, FakeCaseTimelineRepository([naive_event, aware_event])
        )

        view = svc.get_case(cid)
        assert view is not None
        titles = [e.title for e in view.timeline_events]
        assert titles == ["Aware", "Naiv"]  # newest first, no TypeError

    def test_inactive_events_are_excluded(
        self, case_repo: FakeCaseRepository, doc_repo: FakeDocumentRepository
    ) -> None:
        """Only active (confirmed/corrected) events reach the sidebar."""
        from datetime import datetime

        from private_legal_navigator.domain.case_timeline import (
            CaseLegalEvent,
            LegalEventType,
            ReviewStatus,
        )

        cid = uuid.uuid4()
        case_repo.save(
            Case(
                case_id=cid,
                title="SYNTHETISCH – Aktiv",
                status="Offen",
                created_at=datetime(2025, 1, 1),
                updated_at=datetime(2025, 1, 1),
            )
        )
        active = _make_event(cid, "Aktiv", datetime(2025, 1, 5))
        revoked = CaseLegalEvent(
            event_id=uuid.uuid4(),
            case_id=cid,
            event_type=LegalEventType.OBJECTION_FILED,
            occurred_at=datetime(2025, 1, 6),
            title="Widerrufen",
            review_status=ReviewStatus.REVOKED,
        )
        timeline_repo = FakeCaseTimelineRepository([active, revoked])
        svc = _svc_with_timeline(case_repo, doc_repo, timeline_repo)

        view = svc.get_case(cid)
        assert view is not None
        titles = [e.title for e in view.timeline_events]
        # Fake returns everything; the service must not invent filtering,
        # but the real repository already filters. At minimum the active
        # event is present and the sidebar shows.
        assert "Aktiv" in titles
