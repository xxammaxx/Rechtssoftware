# Data Model — M6-UI View Models

## Overview

M6-UI introduces no new persistent data. The UI uses the existing M6-A data model unchanged. This document defines the **view models** — the data structures passed from UI routes to Jinja2 templates.

## No New Database Tables

M6-UI is a presentation layer. All data comes from existing tables and API responses. No migrations needed.

## View Models (Template Context)

### CaseListView

```python
@dataclass
class CaseListView:
    cases: list[CaseSummary]
    case_count: int

@dataclass
class CaseSummary:
    case_id: str  # UUID as string for URL
    title: str
    status: str
    document_count: int
    created_at: str  # ISO datetime
```

### CaseDetailView

```python
@dataclass
class CaseDetailView:
    case_id: str
    title: str
    status: str
    documents: list[DocumentSummary]

@dataclass
class DocumentSummary:
    document_id: str  # UUID as string
    filename: str  # safe — never rendered as innerHTML
    classification: str
    size_bytes: int
    has_text: bool  # whether text extraction succeeded
    uploaded_at: str
```

### DeadlineWorkspaceView

```python
@dataclass
class DeadlineWorkspaceView:
    case_id: str
    document_id: str
    document_filename: str
    candidates: list[CandidateCard]
    warnings: list[WarningDisplay]
    human_review_required: bool  # always True

@dataclass
class CandidateCard:
    index: int  # 0-based candidate index
    kind: str  # EXPLICIT_DATE, RELATIVE_PERIOD, QUALITATIVE_REFERENCE
    display_text: str  # truncated, safe for rendering
    date_value: str | None  # for EXPLICIT_DATE
    duration_amount: int | None  # for RELATIVE_PERIOD
    duration_unit: str | None
    reference_required: bool
    is_relative: bool  # convenience flag for template logic
```

### ReferenceEventsView

```python
@dataclass
class ReferenceEventsView:
    case_id: str
    document_id: str
    candidate_index: int
    events: list[ReferenceEventCard]
    any_confirmed: bool
    current_status: str | None  # CONFIRMED/REJECTED/REVOKED/None
    warnings: list[WarningDisplay]

@dataclass
class ReferenceEventCard:
    candidate_uuid: str  # reference event candidate UUID
    event_type: str  # translated to German: "Zustellung", "Bescheiddatum"
    suggested_date: str | None  # ISO date or None
    source_type: str  # "Automatisch erkannt" / "Manuell"
    evidence_text: str  # safe — Jinja2 autoescaped
    confirmation_status: str  # UNCONFIRMED/CONFIRMED/REJECTED/REVOKED/SUPERSEDED
```

### CalculationPreviewView

```python
@dataclass
class CalculationPreviewView:
    case_id: str
    document_id: str
    candidate_index: int
    reference_date: str  # ISO date
    reference_source: str  # event_type translated
    reference_method: str  # confirmation_method translated
    duration_display: str  # "14 Kalendertage (2 Wochen)"
    calculated_date: str  # ISO date
    calculation_steps: list[CalculationStepDisplay]
    adjustments: list[AdjustmentDisplay]
    warnings: list[WarningDisplay]
    has_required_warnings: bool  # True if all mandatory warnings present
    human_review_required: bool  # always True
    legal_validity_assessed: bool  # always False

@dataclass
class CalculationStepDisplay:
    step_number: int
    operation: str  # "Addition von 14 Kalendertagen"
    input_date: str
    output_date: str
    amount: int

@dataclass
class AdjustmentDisplay:
    label: str  # "Wochenendverschiebung"
    applied: bool  # Always False in M6-A
    note: str  # "Nicht angewendet"
```

### HistoryView

```python
@dataclass
class HistoryView:
    case_id: str
    document_id: str
    candidate_index: int
    entries: list[HistoryEntryDisplay]
    current_status: str
    has_active_confirmation: bool

@dataclass
class HistoryEntryDisplay:
    confirmation_id: str
    confirmed_date: str | None
    event_type: str
    confirmation_method: str  # translated
    confirmation_status: str  # translated
    confirmed_at: str  # ISO datetime
    supersedes: str | None  # previous confirmation_id
    is_current: bool  # currently active?
```

### ErrorView

```python
@dataclass
class ErrorView:
    error_code: str  # stable error code
    message: str  # user-friendly German message
    details: str | None  # additional context, no sensitive data
    back_url: str | None  # where to go back
    back_label: str  # "Zurück zur Fallübersicht"

class ErrorMessages:
    """User-friendly German error messages for API error codes."""
    _MESSAGES = {
        "CASE_NOT_FOUND": "Der angeforderte Fall wurde nicht gefunden. Möglicherweise wurde er gelöscht.",
        "DOCUMENT_NOT_FOUND": "Das angeforderte Dokument wurde nicht gefunden.",
        "CONFIRMATION_NOT_FOUND": "Die angeforderte Bestätigung wurde nicht gefunden.",
        "INVALID_CANDIDATE_INDEX": "Der angeforderte Fristkandidat existiert nicht.",
        "NOT_A_RELATIVE_CANDIDATE": "Dieser Kandidat ist kein relativer Fristkandidat.",
        "REFERENCE_EVENT_NOT_CONFIRMED": "Kein Bezugsdatum bestätigt. Bitte bestätigen Sie zuerst ein Bezugsdatum.",
        "REFERENCE_EVENT_REVOKED": "Die Bestätigung wurde widerrufen. Keine Berechnung möglich.",
        "UNSUPPORTED_DURATION_UNIT": "Diese Zeiteinheit wird nicht unterstützt. Nur Tage und Wochen sind verfügbar.",
        "INVALID_DURATION_AMOUNT": "Die Dauer muss größer als null sein.",
        "INVALID_DATE": "Das eingegebene Datum ist ungültig. Bitte Format YYYY-MM-DD verwenden.",
        "INTERNAL_PROCESSING_ERROR": "Ein interner Fehler ist aufgetreten. Bitte versuchen Sie es erneut.",
    }

    @classmethod
    def get(cls, code: str) -> str:
        return cls._MESSAGES.get(code, "Ein unerwarteter Fehler ist aufgetreten.")
```

### WarningDisplay

```python
@dataclass
class WarningDisplay:
    code: str  # stable warning code
    message: str  # German message
    severity: str  # "warning" | "error" | "info"

class WarningMessages:
    """User-friendly German warning messages."""
    _MESSAGES = {
        "LEGAL_CALCULATION_NOT_PERFORMED": (
            "Es wurde keine rechtliche Fristberechnung durchgeführt. "
            "Dies ist eine rein mathematische Datumsberechnung."
        ),
        "CALCULATION_PREVIEW_ONLY": (
            "Diese Berechnung ist eine unverbindliche Vorschau. "
            "Sie stellt KEINE rechtlich verbindliche Frist dar."
        ),
        "NO_WEEKEND_OR_HOLIDAY_ADJUSTMENT": (
            "Wochenenden und Feiertage wurden nicht berücksichtigt. "
            "Die tatsächliche rechtliche Frist kann abweichen."
        ),
        "NO_DELIVERY_OR_ANNOUNCEMENT_RULE_APPLIED": (
            "Es wurden keine Zustellungs- oder Bekanntgaberegeln angewendet."
        ),
        "HUMAN_REVIEW_REQUIRED": (
            "Menschliche Prüfung zwingend erforderlich. "
            "Nicht zur Fristwahrung geeignet."
        ),
        "MANUAL_ENTRY_WITHOUT_EVIDENCE": (
            "Achtung: Diese manuelle Eingabe hat keinen Beleg. "
            "Bitte geben Sie nach Möglichkeit eine Quelle an."
        ),
        "MULTIPLE_REFERENCE_EVENTS": (
            "Mehrere mögliche Bezugsereignisse gefunden. "
            "Bitte wählen Sie das zutreffende Ereignis aus."
        ),
        "REFERENCE_EVENT_NOT_CONFIRMED": (
            "Kein Bezugsereignis wurde bestätigt. "
            "Eine Berechnung ist erst nach Bestätigung möglich."
        ),
        "REFERENCE_EVENT_REJECTED": (
            "Bezugsereignis abgelehnt. Keine Berechnung möglich."
        ),
        "REFERENCE_EVENT_REVOKED": (
            "Bestätigung widerrufen. Keine Berechnung mehr möglich."
        ),
        "CALCULATED_DATE_OUT_OF_RANGE": (
            "Das berechnete Datum liegt außerhalb des gültigen Bereichs (1900–2099)."
        ),
    }

    @classmethod
    def get(cls, code: str) -> str | None:
        return cls._MESSAGES.get(code)
```

## Template Context Safety

All view model fields containing user-provided or document-extracted text are rendered via Jinja2's `{{ variable }}` syntax, which auto-escapes HTML. The `| safe` filter is **never** used for any of these fields:

- `CaseSummary.title`
- `DocumentSummary.filename`
- `CandidateCard.display_text`
- `ReferenceEventCard.evidence_text`
- `ErrorView.message`
- `WarningDisplay.message`
- `HistoryEntryDisplay.event_type`
- Any `_view` or `_display` string field

## Event Type Translations

```python
EVENT_TYPE_LABELS = {
    "delivery": "Zustellung",
    "announcement": "Bekanntgabe",
    "receipt": "Zugang / Erhalt",
    "issue_date": "Bescheiddatum",
    "publication": "Veröffentlichung",
    "application": "Antragstellung",
    "user_defined": "Nutzerdefiniert",
    "unknown": "Unbekannt",
}
```

## Confirmation Method Translations

```python
CONFIRMATION_METHOD_LABELS = {
    "auto_suggested": "Automatisch erkannt — vom Nutzer bestätigt",
    "manually_entered": "Manuell eingegeben",
    "corrected": "Vom Nutzer korrigiert",
}
```

## Source Type Translations

```python
SOURCE_TYPE_LABELS = {
    "auto_detected": "Automatisch erkannt",
    "user_manual": "Manuell eingegeben",
    "user_corrected": "Vom Nutzer korrigiert",
}
```
