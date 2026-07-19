"""Local Confirmation Workspace Service — Application Layer Orchestrator.

Coordinates existing application services to produce UI read models.
Does NOT:
- Access infrastructure repositories directly
- Construct HTML or know about templates
- Duplicate business logic from existing services
- Invent business state
"""

import uuid
from datetime import date as date_type

from private_legal_navigator.application.case_repository import CaseRepository
from private_legal_navigator.application.deadline_service import DeadlineService
from private_legal_navigator.application.document_repository import DocumentRepository
from private_legal_navigator.application.document_service import DocumentService
from private_legal_navigator.application.reference_event_service import (
    ConfirmationActionResult,
    ReferenceEventService,
)
from private_legal_navigator.application.ui_view_models import (
    CandidateCard,
    CandidateDetailView,
    CaseDetailView,
    CaseListView,
    CaseSummary,
    ConfirmationHistoryEntry,
    DeadlineWorkspaceView,
    DocumentSummary,
    ReferenceEventCard,
    WarningDisplay,
)
from private_legal_navigator.domain.deadline import (
    DeadlineCandidateKind,
)
from private_legal_navigator.domain.reference_event import (
    ConfirmationMethod,
    ConfirmationStatus,
    EventType,
    SourceType,
)
from private_legal_navigator.middleware.csrf import CsrfTokenService

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
    "user_manual": "Vom Nutzer manuell eingegeben",
    "user_corrected": "Vom Nutzer korrigiert",
}

_STATUS_LABELS: dict[ConfirmationStatus, str] = {
    ConfirmationStatus.UNCONFIRMED: "Unbestätigt",
    ConfirmationStatus.CONFIRMED: "Vom Nutzer bestätigt",
    ConfirmationStatus.REJECTED: "Vom Nutzer abgelehnt",
    ConfirmationStatus.REVOKED: "Widerrufen",
    ConfirmationStatus.SUPERSEDED: "Durch neuere Angabe ersetzt",
}

_CONFIRMATION_METHOD_LABELS: dict[ConfirmationMethod, str] = {
    ConfirmationMethod.AUTO_SUGGESTED: "Automatisch erkannt – vom Nutzer bestätigt",
    ConfirmationMethod.MANUALLY_ENTERED: "Manuell eingegeben",
    ConfirmationMethod.CORRECTED: "Vom Nutzer korrigiert",
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
        csrf_service: CsrfTokenService | None = None,
    ) -> None:
        self._case_repo = case_repository
        self._document_repo = document_repository
        self._document_service = document_service
        self._deadline_service = deadline_service
        self._reference_event_service = reference_event_service
        self._csrf_service = csrf_service

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

    # ── Candidate Detail & Confirmation Actions (M6-UI Slice 2) ─────

    def get_candidate_detail(
        self,
        case_id: uuid.UUID,
        document_id: uuid.UUID,
        candidate_index: int,
        action_path: str = "",
        browser_nonce: str = "",
    ) -> CandidateDetailView | None:
        """Produce a candidate detail view with confirmation history and forms.

        Args:
            case_id: The case UUID.
            document_id: The document UUID.
            candidate_index: The 0-based deadline candidate index.
            action_path: The POST action path for CSRF token binding.
            browser_nonce: Existing browser nonce (from cookie).
                When provided, the CSRF token is bound to this nonce
                instead of generating a new one — this ensures the
                cookie nonce and form token nonce match.

        Returns:
            CandidateDetailView or None if case/document/candidate not found.
        """
        # Verify case exists
        case = self._case_repo.get_by_id(case_id)
        if case is None:
            return None

        # Verify document exists and belongs to case
        doc = self._document_service.get_document_text(document_id)
        if doc is None or doc.case_id != case_id:
            return None

        # Get deadline candidates
        extraction_result = self._deadline_service.extract_candidates(document_id)
        if extraction_result is None:
            return None

        if candidate_index < 0 or candidate_index >= len(extraction_result.candidates):
            return None

        c = extraction_result.candidates[candidate_index]

        # Candidate display data
        display_text = c.raw_text
        if len(display_text) > _TRUNCATION_LIMIT:
            display_text = display_text[:_TRUNCATION_LIMIT] + "…"

        # Get confirmation history
        history_records = self._reference_event_service.get_history(document_id, candidate_index)

        # Build history entries
        history_entries: list[ConfirmationHistoryEntry] = []
        active_confirmation: ConfirmationHistoryEntry | None = None
        current_status: ConfirmationStatus = ConfirmationStatus.UNCONFIRMED

        for event in history_records:
            # Determine implicit status
            if event.confirmed_date is None:
                status = ConfirmationStatus.REJECTED
            elif event.supersedes_confirmation_id is not None:
                # Check if this is a revocation (revoke creates record with supersedes)
                # REVOKED records set supersedes to the target; if this record's ID
                # appears as supersedes in another record, it's SUPERSEDED
                status = ConfirmationStatus.CONFIRMED  # simplified for now
            else:
                status = ConfirmationStatus.CONFIRMED

            # Check if this record is superseded by another
            for other in history_records:
                if (
                    other.supersedes_confirmation_id is not None
                    and uuid.UUID(str(other.supersedes_confirmation_id)) == event.confirmation_id
                ):
                    status = ConfirmationStatus.SUPERSEDED
                    break

            entry = ConfirmationHistoryEntry(
                confirmation_id=str(event.confirmation_id),
                confirmed_date=event.confirmed_date.isoformat() if event.confirmed_date else None,
                event_type_label=_EVENT_TYPE_LABELS.get(
                    event.event_type.value, event.event_type.value
                ),
                source_type_label=_SOURCE_LABELS.get(
                    event.source_type.value, event.source_type.value
                ),
                confirmation_method_label=_CONFIRMATION_METHOD_LABELS.get(
                    event.confirmation_method, event.confirmation_method.value
                ),
                status_label=_STATUS_LABELS.get(status, status.value),
                confirmed_at=event.confirmed_at.isoformat(),
                supersedes=str(event.supersedes_confirmation_id)
                if event.supersedes_confirmation_id
                else None,
                is_active=status == ConfirmationStatus.CONFIRMED,
            )
            history_entries.append(entry)

            if status == ConfirmationStatus.CONFIRMED and active_confirmation is None:
                active_confirmation = entry
                current_status = ConfirmationStatus.CONFIRMED
            elif status == ConfirmationStatus.REJECTED and current_status not in (
                ConfirmationStatus.CONFIRMED,
            ):
                current_status = ConfirmationStatus.REJECTED

        # Generate CSRF token and idempotency key
        csrf_token = ""
        idempotency_key = ""
        if self._csrf_service:
            nonce = browser_nonce if browser_nonce else self._csrf_service.generate_browser_nonce()
            csrf_token = self._csrf_service.generate_form_token(nonce, action_path or "/ui/")
            idempotency_key = CsrfTokenService.generate_idempotency_key()

        return CandidateDetailView(
            case_id=str(case_id),
            document_id=str(document_id),
            document_filename=doc.filename,
            candidate_index=candidate_index,
            candidate_kind=_KIND_LABELS.get(c.kind, c.kind.value),
            candidate_display_text=display_text,
            candidate_date_value=c.normalized_date.isoformat() if c.normalized_date else None,
            candidate_duration_amount=c.amount,
            candidate_duration_unit=_UNIT_LABELS.get(c.unit, c.unit) if c.unit else None,
            candidate_reference_required=c.reference_required,
            candidate_is_relative=c.kind == DeadlineCandidateKind.RELATIVE_PERIOD,
            current_status_label=_STATUS_LABELS.get(current_status, current_status.value),
            current_status=current_status.value,
            active_confirmation=active_confirmation,
            history=history_entries,
            has_history=len(history_entries) > 0,
            csrf_token=csrf_token,
            idempotency_key=idempotency_key,
        )

    def confirm_candidate(
        self,
        idempotency_key: str,
        case_id: uuid.UUID,
        document_id: uuid.UUID,
        candidate_index: int,
        event_type: EventType,
        confirmed_date: date_type,
        redirect_path: str,
    ) -> ConfirmationActionResult:
        """Confirm a detected reference event candidate.

        Server-side revalidation: reloads candidate from database to
        verify it exists and belongs to the correct document/case.

        Args:
            idempotency_key: Unique idempotency key for this action.
            case_id: The case UUID.
            document_id: The document UUID.
            candidate_index: The candidate index to confirm.
            event_type: The event type enum value.
            confirmed_date: The date to confirm.
            redirect_path: The PRG redirect target.

        Returns:
            ConfirmationActionResult.

        Raises:
            IdempotencyKeyConflictError: On replay conflict.
            ValueError: If case/document/candidate not found.
        """
        # Server-side revalidation
        case = self._case_repo.get_by_id(case_id)
        if case is None:
            raise ValueError("Fall nicht gefunden.")

        doc = self._document_service.get_document_text(document_id)
        if doc is None or doc.case_id != case_id:
            raise ValueError("Dokument nicht gefunden oder gehört nicht zum Fall.")

        extraction_result = self._deadline_service.extract_candidates(document_id)
        if extraction_result is None:
            raise ValueError("Dokument hat keine extrahierten Kandidaten.")

        if candidate_index < 0 or candidate_index >= len(extraction_result.candidates):
            raise ValueError("Kandidat nicht gefunden.")

        return self._reference_event_service.confirm_with_idempotency(
            idempotency_key=idempotency_key,
            document_id=document_id,
            deadline_candidate_index=candidate_index,
            event_type=event_type,
            confirmed_date=confirmed_date,
            source_type=SourceType.AUTO_DETECTED,
            confirmation_method=ConfirmationMethod.AUTO_SUGGESTED,
            redirect_path=redirect_path,
        )

    def reject_candidate(
        self,
        idempotency_key: str,
        case_id: uuid.UUID,
        document_id: uuid.UUID,
        candidate_index: int,
        event_type: EventType,
        redirect_path: str,
    ) -> ConfirmationActionResult:
        """Reject a detected reference event candidate."""
        # Server-side revalidation (same as confirm)
        case = self._case_repo.get_by_id(case_id)
        if case is None:
            raise ValueError("Fall nicht gefunden.")

        doc = self._document_service.get_document_text(document_id)
        if doc is None or doc.case_id != case_id:
            raise ValueError("Dokument nicht gefunden oder gehört nicht zum Fall.")

        extraction_result = self._deadline_service.extract_candidates(document_id)
        if extraction_result is None:
            raise ValueError("Dokument hat keine extrahierten Kandidaten.")

        if candidate_index < 0 or candidate_index >= len(extraction_result.candidates):
            raise ValueError("Kandidat nicht gefunden.")

        return self._reference_event_service.reject_with_idempotency(
            idempotency_key=idempotency_key,
            document_id=document_id,
            deadline_candidate_index=candidate_index,
            event_type=event_type,
            redirect_path=redirect_path,
        )

    def manual_confirm_date(
        self,
        idempotency_key: str,
        case_id: uuid.UUID,
        document_id: uuid.UUID,
        candidate_index: int,
        event_type: EventType,
        confirmed_date: date_type,
        redirect_path: str,
        evidence_note: str = "",
    ) -> ConfirmationActionResult:
        """Manually confirm a reference date."""
        # Server-side revalidation
        case = self._case_repo.get_by_id(case_id)
        if case is None:
            raise ValueError("Fall nicht gefunden.")

        doc = self._document_service.get_document_text(document_id)
        if doc is None or doc.case_id != case_id:
            raise ValueError("Dokument nicht gefunden oder gehört nicht zum Fall.")

        extraction_result = self._deadline_service.extract_candidates(document_id)
        if extraction_result is None:
            raise ValueError("Dokument hat keine extrahierten Kandidaten.")

        if candidate_index < 0 or candidate_index >= len(extraction_result.candidates):
            raise ValueError("Kandidat nicht gefunden.")

        return self._reference_event_service.confirm_with_idempotency(
            idempotency_key=idempotency_key,
            document_id=document_id,
            deadline_candidate_index=candidate_index,
            event_type=event_type,
            confirmed_date=confirmed_date,
            source_type=SourceType.USER_MANUAL,
            confirmation_method=ConfirmationMethod.MANUALLY_ENTERED,
            candidate_id=None,
            evidence_note=evidence_note,
            redirect_path=redirect_path,
        )
