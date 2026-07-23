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
from datetime import datetime

from private_legal_navigator.application.calendar_arithmetic import CalendarArithmetic
from private_legal_navigator.application.case_repository import CaseRepository
from private_legal_navigator.application.deadline_service import DeadlineService
from private_legal_navigator.application.document_repository import DocumentRepository
from private_legal_navigator.application.document_service import DocumentService
from private_legal_navigator.application.reference_event_service import (
    ConfirmationActionResult,
    ReferenceEventService,
)
from private_legal_navigator.application.ui_view_models import (
    CalculationPreviewResultDTO,
    CalculationPreviewView,
    CalculationTraceStepDTO,
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
    CalculationOperation,
    CalculationStep,
    ConfirmationMethod,
    ConfirmationStatus,
    ConfirmedReferenceEvent,
    Duration,
    DurationUnit,
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


# ---------------------------------------------------------------------------
# Display helpers — pure formatting, no domain logic
# ---------------------------------------------------------------------------


def _format_date_iso(iso_str: str | None) -> str:
    """Convert ISO date (YYYY-MM-DD) to German display format (DD.MM.YYYY)."""
    if not iso_str:
        return ""
    try:
        d = date_type.fromisoformat(iso_str)
        return d.strftime("%d.%m.%Y")
    except (ValueError, TypeError):
        return iso_str


def _format_datetime_display(iso_str: str | None) -> str:
    """Convert ISO datetime to German display format (DD.MM.YYYY, HH:MM)."""
    if not iso_str:
        return ""
    try:
        # Handle both date-only and datetime ISO strings
        s = iso_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        # Convert to local time equivalent (display as-is, just format)
        return dt.strftime("%d.%m.%Y, %H:%M")
    except (ValueError, TypeError):
        return iso_str


_STATUS_CSS_MAP: dict[str, str] = {
    "unconfirmed": "unconfirmed",
    "confirmed": "confirmed",
    "rejected": "rejected",
    "revoked": "revoked",
    "superseded": "superseded",
}


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
        calendar_arithmetic: CalendarArithmetic | None = None,
    ) -> None:
        self._case_repo = case_repository
        self._document_repo = document_repository
        self._document_service = document_service
        self._deadline_service = deadline_service
        self._reference_event_service = reference_event_service
        self._csrf_service = csrf_service
        self._calendar_arithmetic = calendar_arithmetic

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
                    created_at_display=_format_datetime_display(c.created_at.isoformat()),
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
                    uploaded_at_display=_format_datetime_display(d.created_at.isoformat()),
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
        hint_corrected: bool = False,
        hint_revoked: bool = False,
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
            # Determine implicit status from database-level flags and structure
            if event.is_revoke:
                # Database-level revocation flag
                status = ConfirmationStatus.REVOKED
            elif event.confirmed_date is None:
                status = ConfirmationStatus.REJECTED
            elif event.supersedes_confirmation_id is not None:
                # Has supersedes but not revoked — check if superseded by another
                status = ConfirmationStatus.CONFIRMED  # Default for records with date + supersedes
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
                confirmed_at_display=_format_datetime_display(event.confirmed_at.isoformat()),
                confirmed_date_display=_format_date_iso(
                    event.confirmed_date.isoformat() if event.confirmed_date else None
                ),
                status_css=_STATUS_CSS_MAP.get(status.value, "unconfirmed"),
            )
            history_entries.append(entry)

            if status == ConfirmationStatus.CONFIRMED and active_confirmation is None:
                active_confirmation = entry
                current_status = ConfirmationStatus.CONFIRMED
            elif status == ConfirmationStatus.REJECTED and current_status not in (
                ConfirmationStatus.CONFIRMED,
            ):
                current_status = ConfirmationStatus.REJECTED
            elif status == ConfirmationStatus.REVOKED and current_status not in (
                ConfirmationStatus.CONFIRMED,
            ):
                current_status = ConfirmationStatus.REVOKED

        # Generate CSRF token and idempotency key
        csrf_token = ""
        idempotency_key = ""
        if self._csrf_service:
            nonce = browser_nonce if browser_nonce else self._csrf_service.generate_browser_nonce()
            csrf_token = self._csrf_service.generate_form_token(nonce, action_path or "/ui/")
            idempotency_key = CsrfTokenService.generate_idempotency_key()

        # Compute display-oriented derived fields
        detected_date_iso = c.normalized_date.isoformat() if c.normalized_date else None
        confirmed_date_iso = active_confirmation.confirmed_date if active_confirmation else None

        display_detected = _format_date_iso(detected_date_iso)
        display_confirmed = _format_date_iso(confirmed_date_iso) if confirmed_date_iso else ""

        # Determine if dates differ (only when both exist)
        dates_differ = bool(
            detected_date_iso and confirmed_date_iso and detected_date_iso != confirmed_date_iso
        )
        dates_match = bool(
            detected_date_iso and confirmed_date_iso and detected_date_iso == confirmed_date_iso
        )

        # Show actions when not yet acted upon (rejected handles its own rules)
        show_actions = current_status not in (
            ConfirmationStatus.CONFIRMED,
            ConfirmationStatus.REVOKED,
        )
        # Correct/revoke are available when CONFIRMED (not for UNCONFIRMED/REJECTED/REVOKED)
        show_correct_revoke = current_status == ConfirmationStatus.CONFIRMED
        is_completed = current_status in (
            ConfirmationStatus.CONFIRMED,
            ConfirmationStatus.REJECTED,
            ConfirmationStatus.REVOKED,
        )

        # Active confirmation ID for expected-state binding
        active_confirmation_id = active_confirmation.confirmation_id if active_confirmation else ""

        # --- Success flash message (guarded by server state verification) ---
        success_message = ""
        if (
            hint_corrected
            and current_status == ConfirmationStatus.CONFIRMED
            and (active_confirmation is not None)
        ):
            # Verify the active confirmation has a correction source
            for event in history_records:
                if str(event.confirmation_id) == active_confirmation.confirmation_id:
                    is_correction = (
                        event.source_type == SourceType.USER_CORRECTED
                        or event.confirmation_method == ConfirmationMethod.CORRECTED
                    )
                    if is_correction:
                        success_message = "corrected"
                    break
        if hint_revoked and not success_message and current_status == ConfirmationStatus.REVOKED:
            success_message = "revoked"

        return CandidateDetailView(
            case_id=str(case_id),
            document_id=str(document_id),
            document_filename=doc.filename,
            candidate_index=candidate_index,
            candidate_kind=_KIND_LABELS.get(c.kind, c.kind.value),
            candidate_display_text=display_text,
            candidate_date_value=detected_date_iso,
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
            case_label=case.title,
            display_detected_date=display_detected,
            display_confirmed_date=display_confirmed,
            dates_differ=dates_differ,
            dates_match=dates_match,
            status_css=_STATUS_CSS_MAP.get(current_status.value, "unconfirmed"),
            show_actions=show_actions,
            show_correct_revoke=show_correct_revoke,
            active_confirmation_id=active_confirmation_id,
            is_completed=is_completed,
            success_message=success_message,
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

    # ── Correct & Revoke (M6-UI Slice 3) ──────────────────────────

    def correct_candidate(
        self,
        idempotency_key: str,
        case_id: uuid.UUID,
        document_id: uuid.UUID,
        candidate_index: int,
        event_type: EventType,
        confirmed_date: date_type,
        expected_active_confirmation_id: str,
        redirect_path: str,
        evidence_note: str = "",
    ) -> ConfirmationActionResult:
        """Correct (supersede) an existing active confirmation.

        Server-side revalidation verifies case/document/candidate exist.
        Expected-state binding ensures the form was generated for the
        current active confirmation.
        """
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

        return self._reference_event_service.correct_with_idempotency(
            idempotency_key=idempotency_key,
            document_id=document_id,
            deadline_candidate_index=candidate_index,
            event_type=event_type,
            confirmed_date=confirmed_date,
            expected_active_confirmation_id=expected_active_confirmation_id,
            evidence_note=evidence_note,
            redirect_path=redirect_path,
        )

    def revoke_candidate(
        self,
        idempotency_key: str,
        case_id: uuid.UUID,
        document_id: uuid.UUID,
        candidate_index: int,
        event_type: EventType,
        expected_active_confirmation_id: str,
        redirect_path: str,
    ) -> ConfirmationActionResult:
        """Revoke (widerrufen) an existing active confirmation.

        Creates a REVOKED record. The previous active confirmation
        becomes SUPERSEDED. No data is deleted.
        """
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

        return self._reference_event_service.revoke_with_idempotency(
            idempotency_key=idempotency_key,
            document_id=document_id,
            deadline_candidate_index=candidate_index,
            event_type=event_type,
            expected_active_confirmation_id=expected_active_confirmation_id,
            redirect_path=redirect_path,
        )

    # ── Calculation Preview (M6-UI Slice 4) ─────────────────────────

    def _get_active_confirmation_for_preview(
        self,
        document_id: uuid.UUID,
        candidate_index: int,
        expected_active_confirmation_id: str,
    ) -> tuple[ConfirmedReferenceEvent, list[ConfirmedReferenceEvent]]:
        """Lookup active CONFIRMED event and verify expected-state.

        Returns (active_event, history_records) tuple.

        Raises:
            ValueError: If no active confirmation exists or expected-state mismatches.
                Contains "geändert" for stale-state (→ 409 in route handler).
        """
        history_records = self._reference_event_service.get_history(document_id, candidate_index)

        active_event = None
        for event in history_records:
            if event.is_revoke:
                continue
            if event.confirmed_date is None:
                continue
            is_superseded = any(
                other.supersedes_confirmation_id == event.confirmation_id
                for other in history_records
            )
            if not is_superseded:
                active_event = event
                break

        if active_event is None:
            # No active confirmation — if the caller provided an expected ID,
            # the state changed (revocation). Otherwise, no confirmation exists.
            if expected_active_confirmation_id and expected_active_confirmation_id.strip():
                raise ValueError("Der Stand wurde inzwischen geändert.")
            raise ValueError(
                "Für eine Rechenvorschau ist zunächst ein aktuell "
                "bestätigtes Bezugsdatum erforderlich."
            )

        if str(active_event.confirmation_id) != expected_active_confirmation_id:
            raise ValueError("Der Stand wurde inzwischen geändert.")

        return active_event, history_records

    def get_preview_view(
        self,
        case_id: uuid.UUID,
        document_id: uuid.UUID,
        candidate_index: int,
        browser_nonce: str = "",
        action_path: str = "",
    ) -> CalculationPreviewView:
        """Produce a calculation preview view model (GET, read-only).

        Loads active confirmation. If one exists, loads the M5 candidate
        data for display. Does NOT perform calculation (POST does that).
        """
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

        c = extraction_result.candidates[candidate_index]

        # Lookup active confirmation
        history_records = self._reference_event_service.get_history(document_id, candidate_index)
        active_event = None
        for event in history_records:
            if event.is_revoke:
                continue
            if event.confirmed_date is None:
                continue
            is_superseded = any(
                other.supersedes_confirmation_id == event.confirmation_id
                for other in history_records
            )
            if not is_superseded:
                active_event = event
                break

        has_active = active_event is not None
        active_id = str(active_event.confirmation_id) if active_event else ""
        active_date_display = (
            _format_date_iso(active_event.confirmed_date.isoformat())
            if active_event and active_event.confirmed_date
            else ""
        )

        # CSRF token for POST form
        csrf_token = ""
        if self._csrf_service:
            nonce = browser_nonce if browser_nonce else self._csrf_service.generate_browser_nonce()
            csrf_token = self._csrf_service.generate_form_token(nonce, action_path or "/ui/")

        display_text = c.raw_text
        if len(display_text) > _TRUNCATION_LIMIT:
            display_text = display_text[:_TRUNCATION_LIMIT] + "…"

        return CalculationPreviewView(
            case_id=str(case_id),
            document_id=str(document_id),
            candidate_index=candidate_index,
            document_filename=doc.filename,
            case_label=case.title,
            active_confirmation_id=active_id,
            active_confirmation_date_display=active_date_display,
            active_confirmation_status="confirmed" if has_active else "",
            candidate_kind=_KIND_LABELS.get(c.kind, c.kind.value),
            candidate_display_text=display_text,
            csrf_token=csrf_token,
            has_active_confirmation=has_active,
            has_calculation_error=not has_active,
            calculation_error_message=(
                ""
                if has_active
                else (
                    "Für eine Rechenvorschau ist zunächst ein aktuell "
                    "bestätigtes Bezugsdatum erforderlich."
                )
            ),
        )

    def calculate_preview(
        self,
        case_id: uuid.UUID,
        document_id: uuid.UUID,
        candidate_index: int,
        expected_active_confirmation_id: str,
    ) -> CalculationPreviewView:
        """Perform calculation preview with expected-state binding (POST).

        Server-side revalidation:
        1. Cross-resource: case, document, candidate existence
        2. Active confirmation lookup
        3. Expected-state check
        4. Calendar arithmetic via existing port
        5. DTO transformation for UI

        Returns:
            CalculationPreviewView with preview_result populated.

        Raises:
            ValueError: On stale state, missing confirmation, missing arithmetic.
        """
        if self._calendar_arithmetic is None:
            raise ValueError("Rechenvorschau ist nicht verfügbar.")

        # Step 1: Cross-resource validation
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

        c = extraction_result.candidates[candidate_index]

        # Step 2: Active confirmation lookup + expected-state
        active_event, _ = self._get_active_confirmation_for_preview(
            document_id, candidate_index, expected_active_confirmation_id
        )

        # Step 3: Build Duration from M5 candidate
        if not c.amount or not c.unit:
            raise ValueError("Der Kandidat enthält keine verwendbare Dauer.")
        duration = self._validate_preview_duration(c.amount, c.unit)

        # Step 4: Calendar arithmetic via existing port
        calc_candidate = self._calendar_arithmetic.calculate(
            reference_event=active_event,
            duration=duration,
        )

        # Step 5: Transform to DTOs
        trace_steps = [_build_trace_step_dto(step) for step in calc_candidate.calculation_steps]

        warning_labels = _WARNING_LABELS_PREVIEW
        warnings = [warning_labels.get(w, w) for w in calc_candidate.warnings]

        preview = CalculationPreviewResultDTO(
            calculated_date_iso=(
                calc_candidate.calculated_date.isoformat() if calc_candidate.calculated_date else ""
            ),
            calculated_date_display=(
                _format_date_iso(calc_candidate.calculated_date.isoformat())
                if calc_candidate.calculated_date
                else ""
            ),
            reference_date_iso=(
                active_event.confirmed_date.isoformat() if active_event.confirmed_date else ""
            ),
            reference_date_display=(
                _format_date_iso(active_event.confirmed_date.isoformat())
                if active_event.confirmed_date
                else ""
            ),
            duration_amount=duration.amount,
            duration_unit=_UNIT_LABELS.get(duration.unit.value, duration.unit.value),
            duration_calendar_days=duration.calendar_days,
            trace_steps=trace_steps,
            warnings=warnings,
        )

        display_text = c.raw_text
        if len(display_text) > _TRUNCATION_LIMIT:
            display_text = display_text[:_TRUNCATION_LIMIT] + "…"

        return CalculationPreviewView(
            case_id=str(case_id),
            document_id=str(document_id),
            candidate_index=candidate_index,
            document_filename=doc.filename,
            case_label=case.title,
            active_confirmation_id=str(active_event.confirmation_id),
            active_confirmation_date_display=(
                _format_date_iso(active_event.confirmed_date.isoformat())
                if active_event.confirmed_date
                else ""
            ),
            active_confirmation_status="confirmed",
            preview_result=preview,
            candidate_kind=_KIND_LABELS.get(c.kind, c.kind.value),
            candidate_display_text=display_text,
            has_active_confirmation=True,
        )

    @staticmethod
    def _validate_preview_duration(amount: int, unit: str) -> Duration:
        """Validate duration for preview calculation.

        Only DAY and WEEK units supported. Amount must be positive and within bounds.
        """
        unit_map: dict[str, DurationUnit] = {
            "day": DurationUnit.DAY,
            "Tag": DurationUnit.DAY,
            "Tage": DurationUnit.DAY,
            "week": DurationUnit.WEEK,
            "Woche": DurationUnit.WEEK,
            "Wochen": DurationUnit.WEEK,
        }

        if unit not in unit_map:
            raise ValueError(f"Nicht unterstützte Zeiteinheit: '{unit}'. Erlaubt sind: Tag, Woche.")
        if not isinstance(amount, int) or amount <= 0:
            raise ValueError("Die Dauer muss eine positive ganze Zahl sein.")
        if amount > 36500:
            raise ValueError("Die Dauer überschreitet das technische Maximum von 36500 Tagen.")

        return Duration(amount=amount, unit=unit_map[unit])


# ── Slice 4 helpers (module-level) ──────────────────────────────────

_OPERATION_LABELS: dict[CalculationOperation, str] = {
    CalculationOperation.ADD_CALENDAR_DAYS: "Addition von Kalendertagen",
    CalculationOperation.ADD_CALENDAR_WEEKS: "Addition von Kalenderwochen",
}

_WARNING_LABELS_PREVIEW: dict[str, str] = {
    "LEGAL_CALCULATION_NOT_PERFORMED": "Keine rechtliche Fristberechnung durchgeführt.",
    "CALCULATION_PREVIEW_ONLY": "Nur Berechnungsvorschau – nicht rechtsverbindlich.",
    "NO_WEEKEND_OR_HOLIDAY_ADJUSTMENT": "Keine Wochenend- oder Feiertagsbereinigung.",
    "NO_DELIVERY_OR_ANNOUNCEMENT_RULE_APPLIED": (
        "Keine Zustell- oder Bekanntgabefiktion angewendet."
    ),
    "HUMAN_REVIEW_REQUIRED": "Menschliche Prüfung erforderlich.",
}


def _build_trace_step_dto(step: CalculationStep) -> CalculationTraceStepDTO:
    """Transform a domain CalculationStep to a UI-safe Trace DTO."""
    return CalculationTraceStepDTO(
        step_number=step.step,
        operation_label=_OPERATION_LABELS.get(step.operation, step.operation.value),
        input_date_iso=step.input_date.isoformat(),
        input_date_display=_format_date_iso(step.input_date.isoformat()),
        amount=step.amount,
        output_date_iso=step.output_date.isoformat(),
        output_date_display=_format_date_iso(step.output_date.isoformat()),
    )
