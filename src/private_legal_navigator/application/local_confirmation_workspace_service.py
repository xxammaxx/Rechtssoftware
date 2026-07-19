"""Local Confirmation Workspace Service — Application Layer Orchestrator.

Coordinates existing application services to produce UI read models.
Does NOT:
- Access infrastructure repositories directly
- Construct HTML or know about templates
- Duplicate business logic from existing services
- Invent business state
"""

import uuid

from private_legal_navigator.application.case_repository import CaseRepository
from private_legal_navigator.application.deadline_service import DeadlineService
from private_legal_navigator.application.document_repository import DocumentRepository
from private_legal_navigator.application.document_service import DocumentService
from private_legal_navigator.application.reference_event_service import (
    ReferenceEventService,
)
from private_legal_navigator.application.ui_view_models import (
    CandidateCard,
    CaseDetailView,
    CaseListView,
    CaseSummary,
    DeadlineWorkspaceView,
    DocumentSummary,
    ReferenceEventCard,
    WarningDisplay,
)
from private_legal_navigator.domain.deadline import (
    DeadlineCandidateKind,
)
from private_legal_navigator.domain.reference_event import (
    ConfirmationStatus,
)

# ---------------------------------------------------------------------------
# Neutral German labels — must NOT imply legal assessment
# ---------------------------------------------------------------------------

_KIND_LABELS: dict[DeadlineCandidateKind, str] = {
    DeadlineCandidateKind.EXPLICIT_DATE: "explizite Zeitangabe",
    DeadlineCandidateKind.RELATIVE_PERIOD: "relative Zeitangabe",
    DeadlineCandidateKind.QUALITATIVE_REFERENCE: "qualitative Angabe",
}

_UNIT_LABELS: dict[str, str] = {
    "day": "Tag",
    "week": "Woche",
}

_EVENT_TYPE_LABELS: dict[str, str] = {
    "delivery": "Zustellung",
    "announcement": "Bekanntgabe",
    "receipt": "Zugang",
    "issue_date": "Erlassdatum",
    "publication": "Veröffentlichung",
    "application": "Antragstellung",
    "user_defined": "Benutzerdefiniert",
    "unknown": "Unbekannt",
}

_SOURCE_LABELS: dict[str, str] = {
    "auto_detected": "Automatisch erkannt",
    "user_manual": "Manuell",
    "user_corrected": "Korrigiert",
}

_STATUS_LABELS: dict[ConfirmationStatus, str] = {
    ConfirmationStatus.UNCONFIRMED: "Unbestätigt",
    ConfirmationStatus.CONFIRMED: "Bestätigt",
    ConfirmationStatus.REJECTED: "Abgelehnt",
    ConfirmationStatus.REVOKED: "Widerrufen",
    ConfirmationStatus.SUPERSEDED: "Überschrieben",
}

_TRUNCATION_LIMIT = 300


class LocalConfirmationWorkspaceService:
    """Application-layer orchestrator for the M6-UI confirmation workspace.

    Aggregates data from existing M1–M6-A services and produces
    template-safe view model dataclasses.
    """

    def __init__(
        self,
        case_repository: CaseRepository,
        document_repository: DocumentRepository,
        document_service: DocumentService,
        deadline_service: DeadlineService,
        reference_event_service: ReferenceEventService,
    ) -> None:
        self._case_repo = case_repository
        self._document_repo = document_repository
        self._document_service = document_service
        self._deadline_service = deadline_service
        self._reference_event_service = reference_event_service

    # ------------------------------------------------------------------ #
    #  Case views
    # ------------------------------------------------------------------ #

    def list_cases(self) -> CaseListView:
        """Produce a case list view model."""
        cases = self._case_repo.list_all()
        summaries: list[CaseSummary] = []
        for c in cases:
            doc_count = len(self._document_repo.list_by_case(c.case_id))
            summaries.append(
                CaseSummary(
                    case_id=str(c.case_id),
                    title=c.title,
                    status=c.status,
                    document_count=doc_count,
                    created_at=c.created_at.isoformat(),
                )
            )
        return CaseListView(
            cases=summaries,
            case_count=len(summaries),
            has_cases=len(summaries) > 0,
        )

    def get_case(self, case_id: uuid.UUID) -> CaseDetailView | None:
        """Produce a case detail view model with document list."""
        case = self._case_repo.get_by_id(case_id)
        if case is None:
            return None

        docs = self._document_service.list_case_documents(case_id)
        doc_summaries: list[DocumentSummary] = []
        for d in docs:
            doc_summaries.append(
                DocumentSummary(
                    document_id=str(d.document_id),
                    filename=d.filename,
                    classification=d.doc_type,
                    size_bytes=d.size_bytes,
                    has_text=bool(d.text_content),
                    uploaded_at=d.created_at.isoformat(),
                )
            )

        return CaseDetailView(
            case_id=str(case.case_id),
            title=case.title,
            status=case.status,
            documents=doc_summaries,
            has_documents=len(doc_summaries) > 0,
        )

    # ------------------------------------------------------------------ #
    #  Document / Workspace views
    # ------------------------------------------------------------------ #

    def get_document_workspace(
        self, case_id: uuid.UUID, document_id: uuid.UUID
    ) -> DeadlineWorkspaceView | None:
        """Produce a read-only workspace view for a document."""
        # Verify case exists
        case = self._case_repo.get_by_id(case_id)
        if case is None:
            return None

        # Verify document exists and belongs to case
        doc = self._document_service.get_document_text(document_id)
        if doc is None:
            return None
        if doc.case_id != case_id:
            return None

        # Extract deadline candidates
        extraction_result = self._deadline_service.extract_candidates(document_id)

        candidates: list[CandidateCard] = []
        has_relative = False
        warnings: list[WarningDisplay] = []

        if extraction_result is not None:
            warnings = [
                WarningDisplay(code=w.code.value, message=w.message)
                for w in extraction_result.warnings
            ]

            for idx, c in enumerate(extraction_result.candidates):
                is_rel = c.kind == DeadlineCandidateKind.RELATIVE_PERIOD
                has_relative = has_relative or is_rel

                display_text = c.raw_text
                if len(display_text) > _TRUNCATION_LIMIT:
                    display_text = display_text[:_TRUNCATION_LIMIT] + "…"

                candidates.append(
                    CandidateCard(
                        index=idx,
                        kind=_KIND_LABELS.get(c.kind, c.kind.value),
                        display_text=display_text,
                        date_value=c.normalized_date.isoformat() if c.normalized_date else None,
                        duration_amount=c.amount,
                        duration_unit=_UNIT_LABELS.get(c.unit, c.unit) if c.unit else None,
                        reference_required=c.reference_required,
                        is_relative=is_rel,
                    )
                )

        # Reference event candidates — may be empty (M6-A placeholder)
        ref_events: list[ReferenceEventCard] | None = None
        any_confirmed = False
        current_status: str | None = None

        return DeadlineWorkspaceView(
            case_id=str(case_id),
            document_id=str(document_id),
            document_filename=doc.filename,
            candidates=candidates,
            has_candidates=len(candidates) > 0,
            has_relative_candidates=has_relative,
            warnings=warnings,
            human_review_required=True,
            reference_events=ref_events,
            any_confirmed=any_confirmed,
            current_status=current_status,
            csrf_token="",  # Not wired in read-only slice
        )
