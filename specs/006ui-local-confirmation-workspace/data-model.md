# Data Model — M6-UI View Models

## Overview

M6-UI introduces no new persistent data. The UI uses the existing M6-A data model unchanged. This document defines the **view models** — the data structures passed from UI routes (or the `LocalConfirmationWorkspaceService`) to Jinja2 templates.

## No New Database Tables

M6-UI is a presentation layer. All data comes from existing tables and API responses. No migrations needed.

## Application Layer Contract

During implementation, a `LocalConfirmationWorkspaceService` (Application Layer) may be introduced to:

1. Coordinate calls to existing services: `ReferenceEventService`, `CalculationService`, `CaseService`, `DocumentService`
2. Map domain objects to view model dataclasses
3. Perform server-side revalidation before any state-changing operation
4. Produce UI-specific read models without exposing domain entities directly

This service MUST NOT:
- Access infrastructure repositories directly
- Construct HTML or know about templates
- Duplicate business logic from existing services

**Existing Application Service Methods (verified on clean baseline):**

```python
# ReferenceEventService (reference_event_service.py)
- get_reference_event_candidates(document_id, deadline_candidate_index) -> list[ReferenceEventCandidate]
- confirm(document_id, deadline_candidate_index, event_type, confirmed_date, source_type, confirmation_method, candidate_id, evidence_note, confirmed_by) -> ConfirmedReferenceEvent
- reject(document_id, deadline_candidate_index, event_type, candidate_id) -> ConfirmedReferenceEvent
- revoke(confirmation_id) -> ConfirmedReferenceEvent | None
- get_history(document_id, deadline_candidate_index) -> list[ConfirmedReferenceEvent]

# CalculationService (calculation_service.py)
- calculate_preview(confirmation_id, amount, unit) -> CalendarCalculationCandidate
- calculate_preview_from_event(event, amount, unit) -> CalendarCalculationCandidate
```

## Canonical Domain Types (reference_event.py)

```python
# Enums
EventType: delivery, announcement, receipt, issue_date, publication, application, user_defined, unknown
ConfirmationStatus: unconfirmed, confirmed, rejected, revoked, superseded
SourceType: auto_detected, user_manual, user_corrected
ConfirmationMethod: auto_suggested, manually_entered, corrected
DurationUnit: day, week
CalculationOperation: ADD_CALENDAR_DAYS, ADD_CALENDAR_WEEKS

# Entities
ReferenceEventCandidate(candidate_id, document_id, deadline_candidate_index, event_type, suggested_date, source_type, source_reference, evidence_text, start_offset, end_offset, confirmation_status)
ConfirmedReferenceEvent(confirmation_id, document_id, event_type, confirmed_at, deadline_candidate_index, confirmed_date, source_type, confirmation_method, candidate_id, confirmed_by, evidence_note, supersedes_confirmation_id)

# Value Objects
Duration(amount, unit)  # frozen=True, amount > 0, amount <= 36500

# Calculation Result
CalendarCalculationCandidate(calculation_id, confirmed_reference_event, duration, calculated_date, calculation_steps, adjustments_applied, legal_validity_assessed, human_review_required, warnings)
CalculationStep(step, operation, input_date, amount, output_date)
```

## View Models (see contracts/view-models.md for full definitions)

The view model dataclasses map domain objects to template-safe representations:

- `CaseListView`, `CaseSummary` — for case_list.html
- `CaseDetailView`, `DocumentSummary` — for case_detail.html
- `DeadlineWorkspaceView`, `CandidateCard`, `ReferenceEventCard` — for workspace.html
- `CalculationPreviewView`, `CalculationStepDisplay`, `AdjustmentDisplay` — for preview_result.html
- `HistoryView`, `HistoryEntryDisplay` — for confirmation_history.html
- `ErrorView` — for error.html
- `WarningDisplay` — used across multiple templates

## Terminology: Neutral Language

The UI MUST distinguish between document content and system assessment:

| Dokumentinhalt (Original) | UI-Label (System) |
|--------------------------|-------------------|
| "Frist" (im Dokumenttext) | "Erkannter Datums- oder Zeitraumhinweis" |
| "Fristende" | Nicht als Systemlabel verwendet. Stattdessen: "Berechnetes Datum (unverbindlich)" |
| "Fristberechnung" | "Rechenvorschau" |
| "gueltige Frist" | Nicht als Systemlabel verwendet |
| "Fristkandidaten" | "Datums- und Zeitraumhinweise" |

Die Original-Begriffe duerfen im Dokumenttext (evidence_text, display_text) erscheinen — das sind Dokumentinhalte, keine Systembewertungen. Aber alle Systemlabels, Ueberschriften, Button-Texte und Statusmeldungen muessen neutrale Begriffe verwenden.

Empty-State-Texte:
- Keine Faelle: "Keine Faelle vorhanden."
- Keine Dokumente: "Keine Dokumente im Fall."
- Keine Kandidaten: "Keine Datums- oder Zeitraumhinweise erkannt."
- Keine Bezugsereignisse: "Keine Bezugsereignisse gefunden."

## Template Context Safety

All view model fields containing user-provided or document-extracted text are rendered via Jinja2's `{{ variable }}` syntax, which auto-escapes HTML. The `| safe` filter is **never** used for these fields.

**Permanently visible disclaimers (on every results/workspace page):**
- "Rechtliche Gueltigkeit nicht bewertet."
- "Menschliche Pruefung erforderlich."
