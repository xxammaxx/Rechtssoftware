# View Models Contract — M6-UI

## Purpose

This document defines the data contracts between UI route handlers (or the `LocalConfirmationWorkspaceService`) and Jinja2 templates. Each view model is a dataclass or typed dict passed as template context.

## Core Safety Rule

**All string fields rendered via `{{ }}` are auto-escaped by Jinja2.** The `| safe` filter is **never** used on any data originating from the database, API, document text, or user input.

## View Model Definitions

### case_list.html

```python
@dataclass
class CaseListView:
    cases: list[CaseSummary]
    case_count: int
    has_cases: bool

@dataclass
class CaseSummary:
    case_id: str          # UUID as string, URL-safe
    title: str            # escaped by Jinja2
    status: str           # "Offen" / "Geschlossen"
    document_count: int
    created_at: str       # formatted datetime
```

### case_detail.html

```python
@dataclass
class CaseDetailView:
    case_id: str
    title: str            # escaped
    status: str
    documents: list[DocumentSummary]
    has_documents: bool

@dataclass
class DocumentSummary:
    document_id: str      # UUID as string
    filename: str         # escaped — never innerHTML
    classification: str   # "bescheid", "rechnung", etc.
    size_bytes: int
    has_text: bool
    uploaded_at: str      # formatted datetime
```

### workspace.html

```python
@dataclass
class DeadlineWorkspaceView:
    case_id: str
    document_id: str
    document_filename: str          # escaped
    candidates: list[CandidateCard]
    has_candidates: bool
    has_relative_candidates: bool
    warnings: list[WarningDisplay]
    human_review_required: bool     # always True
    # When a relative candidate is selected:
    selected_candidate_index: int | None
    reference_events: list[ReferenceEventCard] | None
    any_confirmed: bool
    current_status: str | None      # "CONFIRMED" / "REJECTED" / "REVOKED" / None
    csrf_token: str                 # for all forms on this page
    calculation_preview: CalculationPreviewView | None

@dataclass
class CandidateCard:
    index: int                      # 0-based candidate index
    kind: str                       # "explizite Zeitangabe" / "relative Zeitangabe" / "qualitative Angabe"
    display_text: str               # escaped, truncated evidence text
    date_value: str | None          # for EXPLICIT_DATE
    duration_amount: int | None     # for RELATIVE_PERIOD
    duration_unit: str | None       # "Tag" / "Woche" / None
    reference_required: bool
    is_relative: bool               # convenience flag

@dataclass
class ReferenceEventCard:
    candidate_uuid: str             # reference event candidate UUID
    event_type: str                 # German label ("Zustellung", "Bescheiddatum", etc.)
    suggested_date: str | None      # ISO date or None
    source_type: str                # "Automatisch erkannt" / "Manuell"
    evidence_text: str              # escaped, truncated
    confirmation_status: str        # German badge label
    is_active: bool                 # currently the active confirmed event
```

### preview_result.html

```python
@dataclass
class CalculationPreviewView:
    case_id: str
    document_id: str
    candidate_index: int
    reference_date: str             # German formatted date
    reference_source: str           # event_type translated
    reference_method: str           # confirmation_method translated
    duration_display: str           # "14 Kalendertage (2 Wochen)"
    calculated_date: str            # German formatted date
    calculation_steps: list[CalculationStepDisplay]
    adjustments: list[AdjustmentDisplay]
    warnings: list[WarningDisplay]
    has_required_warnings: bool     # True if all mandatory warnings present
    human_review_required: bool     # always True
    legal_validity_assessed: bool   # always False

@dataclass
class CalculationStepDisplay:
    step_number: int
    operation: str                  # "Addition von 14 Kalendertagen"
    input_date: str
    output_date: str
    amount: int

@dataclass
class AdjustmentDisplay:
    label: str                      # "Wochenendverschiebung", etc.
    applied: bool                   # Always False in M6-A
    note: str                       # "Nicht angewendet"
```

### confirmation_history.html

```python
@dataclass
class HistoryView:
    case_id: str
    document_id: str
    candidate_index: int
    entries: list[HistoryEntryDisplay]
    current_status: str             # German label
    has_active_confirmation: bool

@dataclass
class HistoryEntryDisplay:
    confirmation_id: str
    confirmed_date: str | None
    event_type: str                 # German label
    confirmation_method: str        # German label
    confirmation_status: str        # German label
    confirmed_at: str               # formatted datetime
    supersedes: str | None          # previous confirmation_id
    is_current: bool
```

### error.html

```python
@dataclass
class ErrorView:
    error_code: str                 # stable code, NOT displayed prominently
    message: str                    # user-friendly German message
    details: str | None             # additional context, NO sensitive data
    back_url: str | None
    back_label: str                 # "Zurueck zur Falluebersicht"
```

## Source of Truth Mapping

Every UI field maps to a defined source. No invented states.

| UI-Feld | Domain-/Application-Quelle | Transformation | Fallback |
|---------|--------------------------|----------------|----------|
| `candidate_id` | `ReferenceEventCandidate.candidate_id` | `str(uuid)` | — |
| `event_type` | `EventType` enum | German label from lookup table | "Unbekannt" |
| `suggested_date` | `ReferenceEventCandidate.suggested_date` | German date format | "Kein Datum" |
| `source_type` | `SourceType` enum | German label | "Unbekannt" |
| `confirmation_status` | `ConfirmationStatus` enum | German label + badge class | "Unbekannt" |
| `human_review_required` | Domain constant | Always `True` | — |
| `legal_validity_assessed` | Domain constant | Always `False` | — |
| `calculated_date` | `CalendarCalculationCandidate.calculated_date` | German date format | "Nicht berechnet" |
| `duration.amount` | `Duration.amount` | Integer string | "—" |
| `duration.unit` | `Duration.unit` → `DurationUnit` | German label | "—" |
| `adjustments.*` | `CalendarCalculationCandidate.adjustments_applied` | Boolean → "Angewendet"/"Nicht angewendet" | — |
| `warnings` | `CalendarCalculationCandidate.warnings` | Warning code → German message | — |
| `supersedes` | `ConfirmedReferenceEvent.supersedes_confirmation_id` | `str(uuid)` or None | — |

## Translation Tables

### Event Type Labels
```python
EVENT_TYPE_LABELS: dict[str, str] = {
    "delivery": "Zustellung",
    "announcement": "Bekanntgabe",
    "receipt": "Zugang / Erhalt",
    "issue_date": "Bescheiddatum",
    "publication": "Veroeffentlichung",
    "application": "Antragstellung",
    "user_defined": "Nutzerdefiniert",
    "unknown": "Unbekannt",
}
```

### Confirmation Method Labels
```python
CONFIRMATION_METHOD_LABELS: dict[str, str] = {
    "auto_suggested": "Automatisch erkannt – vom Nutzer bestaetigt",
    "manually_entered": "Manuell eingegeben",
    "corrected": "Vom Nutzer korrigiert",
}
```

### Source Type Labels
```python
SOURCE_TYPE_LABELS: dict[str, str] = {
    "auto_detected": "Automatisch erkannt",
    "user_manual": "Manuell eingegeben",
    "user_corrected": "Vom Nutzer korrigiert",
}
```

### Candidate Kind Labels (M5 DeadlineCandidate types)
```python
CANDIDATE_KIND_LABELS: dict[str, str] = {
    "EXPLICIT_DATE": "Explizite Zeitangabe",
    "RELATIVE_PERIOD": "Relative Zeitangabe",
    "QUALITATIVE_REFERENCE": "Qualitative Angabe",
}
```

### Warning Messages (User-Facing German)
```python
WARNING_MESSAGES: dict[str, str] = {
    "LEGAL_CALCULATION_NOT_PERFORMED": (
        "Es wurde keine rechtliche Fristberechnung durchgefuehrt. "
        "Dies ist eine rein mathematische Datumsberechnung."
    ),
    "CALCULATION_PREVIEW_ONLY": (
        "Diese Berechnung ist eine unverbindliche Vorschau. "
        "Sie stellt KEINE rechtlich verbindliche Frist dar. "
        "Rechtliche Gueltigkeit nicht bewertet."
    ),
    "NO_WEEKEND_OR_HOLIDAY_ADJUSTMENT": (
        "Wochenenden und Feiertage wurden nicht beruecksichtigt."
    ),
    "NO_DELIVERY_OR_ANNOUNCEMENT_RULE_APPLIED": (
        "Es wurden keine Zustellungs- oder Bekanntgaberegeln angewendet."
    ),
    "HUMAN_REVIEW_REQUIRED": (
        "Menschliche Pruefung zwingend erforderlich."
    ),
    "MULTIPLE_REFERENCE_EVENTS": (
        "Mehrere moegliche Bezugsereignisse gefunden. "
        "Bitte waehlen Sie das zutreffende Ereignis aus."
    ),
    "REFERENCE_EVENT_NOT_CONFIRMED": (
        "Kein Bezugsereignis wurde bestaetigt. "
        "Eine Berechnung ist erst nach Bestaetigung moeglich."
    ),
    "REFERENCE_EVENT_REJECTED": (
        "Bezugsereignis abgelehnt. Keine Berechnung moeglich."
    ),
    "REFERENCE_EVENT_REVOKED": (
        "Bestaetigung widerrufen. Keine Berechnung mehr moeglich."
    ),
    "CALCULATED_DATE_OUT_OF_RANGE": (
        "Das berechnete Datum liegt ausserhalb des gueltigen Bereichs (1900–2099)."
    ),
}

ERROR_MESSAGES: dict[str, str] = {
    "CASE_NOT_FOUND": "Der angeforderte Fall wurde nicht gefunden.",
    "DOCUMENT_NOT_FOUND": "Das angeforderte Dokument wurde nicht gefunden.",
    "CONFIRMATION_NOT_FOUND": "Die angeforderte Bestaetigung wurde nicht gefunden.",
    "INVALID_CANDIDATE_INDEX": "Die angeforderte Zeitangabe existiert nicht.",
    "NOT_A_RELATIVE_CANDIDATE": "Diese Zeitangabe ist keine relative Zeitangabe.",
    "REFERENCE_EVENT_NOT_CONFIRMED": "Kein Bezugsdatum bestaetigt.",
    "REFERENCE_EVENT_REVOKED": "Die Bestaetigung wurde widerrufen.",
    "UNSUPPORTED_DURATION_UNIT": "Diese Zeiteinheit wird nicht unterstuetzt.",
    "INVALID_DURATION_AMOUNT": "Die Dauer muss groesser als null sein.",
    "INVALID_DATE": "Das eingegebene Datum ist ungueltig.",
    "INTERNAL_PROCESSING_ERROR": "Der Vorgang konnte nicht abgeschlossen werden.",
    "CSRF_VALIDATION_FAILED": "Die Anfrage konnte nicht verarbeitet werden.",
    "IDEMPOTENCY_CONFLICT": "Diese Aktion wurde bereits verarbeitet.",
    "HOST_NOT_ALLOWED": "Die Anfrage konnte nicht verarbeitet werden.",
}
```

## Template Context Safety Rules

The `| safe` filter is **never** used for:
- `CaseSummary.title`
- `DocumentSummary.filename`
- `CandidateCard.display_text`
- `ReferenceEventCard.evidence_text`
- `ErrorView.message`
- `WarningDisplay.message`
- `HistoryEntryDisplay` (any field)
- Any string originating from document text or user input

## Data Flow

```
Domain Objects (from Application Services)
  → LocalConfirmationWorkspaceService (optional, Application Layer)
  → UI Route Handler (maps to view model dataclasses)
  → Jinja2 Template (renders {{ variables }} with autoescaping)
  → Browser (displays safe HTML)
```

No view model field bypasses autoescaping. No DOM manipulation with innerHTML. No raw HTML from API responses.
