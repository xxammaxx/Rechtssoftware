"""View models for M6-UI read-only workspace.

Safe dataclasses for template rendering. All string fields are auto-escaped
by Jinja2. The |safe filter is never used on user-provided or document-extracted data.
"""

from dataclasses import dataclass, field


@dataclass
class CaseSummary:
    """A single case in the case list view."""

    case_id: str
    title: str
    status: str
    document_count: int
    created_at: str
    created_at_display: str = ""


@dataclass
class CaseListView:
    """View model for the case list page."""

    cases: list[CaseSummary]
    case_count: int
    has_cases: bool


@dataclass
class DocumentSummary:
    """A single document in the case detail view.

    Does NOT include document text — only metadata.
    """

    document_id: str
    filename: str
    classification: str
    size_bytes: int
    has_text: bool
    uploaded_at: str
    uploaded_at_display: str = ""


@dataclass
class CaseDetailView:
    """View model for the case detail page."""

    case_id: str
    title: str
    status: str
    documents: list[DocumentSummary]
    has_documents: bool


@dataclass
class CandidateCard:
    """A single deadline candidate for the workspace view."""

    index: int
    kind: str
    display_text: str
    date_value: str | None = None
    duration_amount: int | None = None
    duration_unit: str | None = None
    reference_required: bool = False
    is_relative: bool = False


@dataclass
class ReferenceEventCard:
    """A reference event candidate for the workspace view.

    Since reference event detection is a placeholder in M6-A,
    this will typically be empty during Slice 1.
    """

    candidate_uuid: str
    event_type: str
    suggested_date: str | None
    source_type: str
    evidence_text: str
    confirmation_status: str
    is_active: bool = False


@dataclass
class WarningDisplay:
    """A warning to display in the UI."""

    code: str
    message: str


@dataclass
class DeadlineWorkspaceView:
    """View model for the document workspace page (read-only in Slice 1)."""

    case_id: str
    document_id: str
    document_filename: str
    candidates: list[CandidateCard] = field(default_factory=list)
    has_candidates: bool = False
    has_relative_candidates: bool = False
    warnings: list[WarningDisplay] = field(default_factory=list)
    human_review_required: bool = True
    selected_candidate_index: int | None = None
    reference_events: list[ReferenceEventCard] | None = None
    any_confirmed: bool = False
    current_status: str | None = None
    csrf_token: str = ""


@dataclass
class ErrorView:
    """View model for error pages."""

    status_code: int
    title: str
    message: str
    detail: str = ""


@dataclass
class BaseContext:
    """Base context included in every template render."""

    page_title: str = "PrivateLegalNavigator"
    human_review_required: bool = True
    legal_validity_assessed: bool = False


@dataclass
class ConfirmationHistoryEntry:
    """A single entry in the confirmation history."""

    confirmation_id: str
    confirmed_date: str | None  # ISO date or None for rejected
    event_type_label: str
    source_type_label: str
    confirmation_method_label: str
    status_label: str
    confirmed_at: str  # ISO datetime
    supersedes: str | None
    is_active: bool
    # Display-oriented derived fields
    confirmed_at_display: str = ""
    confirmed_date_display: str = ""
    status_css: str = ""


@dataclass
class CandidateDetailView:
    """View model for the candidate detail / confirmation page."""

    case_id: str
    document_id: str
    document_filename: str
    candidate_index: int
    candidate_kind: str
    candidate_display_text: str
    candidate_date_value: str | None
    candidate_duration_amount: int | None
    candidate_duration_unit: str | None
    candidate_reference_required: bool
    candidate_is_relative: bool
    # Confirmation state
    current_status_label: str  # e.g., "Vom Nutzer bestätigt"
    current_status: str  # raw enum value
    active_confirmation: ConfirmationHistoryEntry | None
    history: list[ConfirmationHistoryEntry]
    has_history: bool
    # CSRF
    csrf_token: str
    idempotency_key: str
    # Safety
    human_review_required: bool = True
    legal_validity_assessed: bool = False
    # Success flash message
    success_message: str = ""
    # Display-oriented derived fields (deterministic, no domain logic)
    case_label: str = ""
    display_detected_date: str = ""
    display_confirmed_date: str = ""
    dates_differ: bool = False
    dates_match: bool = False
    status_css: str = ""
    show_actions: bool = False
    show_correct_revoke: bool = False
    active_confirmation_id: str = ""
    is_completed: bool = False


# ── M6-UI Slice 4: Calculation Preview & Trace ──────────────────────


@dataclass
class CalculationTraceStepDTO:
    """Ein einzelner Schritt im Rechenweg — für die UI formatiert.

    Enthält KEINE internen IDs, keine UUIDs, keine Domain-Objekte.
    """

    step_number: int  # 1-based Sequenznummer
    operation_label: str  # z.B. "Addition von Kalendertagen"
    input_date_iso: str  # ISO-Datum (YYYY-MM-DD)
    input_date_display: str  # Deutsches Format (DD.MM.YYYY)
    amount: int  # Anzahl Kalendertage
    output_date_iso: str  # ISO-Datum (YYYY-MM-DD)
    output_date_display: str  # Deutsches Format (DD.MM.YYYY)


@dataclass
class CalculationPreviewResultDTO:
    """Berechnungsvorschau — bereinigt für die UI.

    Keine internen IDs. Keine Domain-Objekte. Flache Struktur.
    """

    calculated_date_iso: str  # z.B. "2026-06-29"
    calculated_date_display: str  # z.B. "29.06.2026"
    reference_date_iso: str  # Bestätigtes Bezugsdatum (vom Server)
    reference_date_display: str  # Deutsches Format
    duration_amount: int  # z.B. 14
    duration_unit: str  # z.B. "Tag" oder "Woche"
    duration_calendar_days: int  # In Kalendertage umgerechnet
    trace_steps: list[CalculationTraceStepDTO] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    human_review_required: bool = True
    legal_validity_assessed: bool = False
    is_preview_only: bool = True


@dataclass
class CalculationPreviewView:
    """Komplettes View-Model für das Preview-Template.

    Aggregiert das Berechnungsergebnis mit Navigationsdaten
    und dem aktiven Bestätigungsstatus.
    """

    case_id: str
    document_id: str
    candidate_index: int
    document_filename: str
    case_label: str
    active_confirmation_id: str  # Für expected-state im Form
    active_confirmation_date_display: str
    active_confirmation_status: str  # "confirmed"
    preview_result: CalculationPreviewResultDTO | None = None
    candidate_kind: str = ""
    candidate_display_text: str = ""
    csrf_token: str = ""
    has_active_confirmation: bool = False
    has_calculation_error: bool = False
    calculation_error_message: str = ""
    human_review_required: bool = True
    legal_validity_assessed: bool = False
