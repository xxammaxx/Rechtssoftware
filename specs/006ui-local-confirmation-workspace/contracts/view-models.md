# View Models Contract — M6-UI

## Purpose

This document defines the data contracts between UI route handlers and Jinja2 templates. Each view model is a dataclass or typed dict passed as template context.

## Core Safety Rule

**All string fields rendered via `{{ }}` are auto-escaped by Jinja2.** The `| safe` filter is **never** used on any data originating from the database, API, document text, or user input.

## View Model Definitions

See `data-model.md` for full type definitions. This contract enumerates the required fields for each template.

### case_list.html

```python
{
    "cases": [
        {
            "case_id": str,       # UUID, URL-safe
            "title": str,         # escaped by Jinja2
            "status": str,        # "Offen" / "Geschlossen"
            "document_count": int,
            "created_at": str,    # formatted datetime
        }
    ],
    "case_count": int,
    "has_cases": bool,            # convenience
}
```

### case_detail.html

```python
{
    "case_id": str,
    "title": str,                 # escaped
    "status": str,
    "documents": [
        {
            "document_id": str,   # UUID
            "filename": str,      # escaped
            "classification": str,
            "size_bytes": int,
            "has_text": bool,
            "uploaded_at": str,
        }
    ],
    "has_documents": bool,
}
```

### deadline_workspace.html

```python
{
    "case_id": str,
    "document_id": str,
    "document_filename": str,     # escaped
    "candidates": [
        {
            "index": int,         # 0-based
            "kind": str,          # "Festes Datum" / "Relative Frist" / "Unbestimmter Zeitraum"
            "display_text": str,  # escaped, truncated evidence text
            "date_value": str | None,
            "duration_amount": int | None,
            "duration_unit": str | None,
            "reference_required": bool,
            "is_relative": bool,
        }
    ],
    "has_candidates": bool,
    "has_relative_candidates": bool,
    "warnings": [{"code": str, "message": str, "severity": str}],
    "human_review_required": bool,   # always True
    # When a relative candidate is selected:
    "selected_candidate": int | None,  # index
    "reference_events": [...],         # see below
    "any_confirmed": bool,
    "current_status": str | None,
    "calculation_preview": {...} | None,  # see calculation_result
    "history_entries": [...] | None,      # see confirmation_history
}
```

### Reference events (within deadline_workspace.html)

```python
"reference_events": [
    {
        "candidate_uuid": str,    # reference event UUID
        "event_type": str,        # German label
        "suggested_date": str | None,
        "source_type": str,       # German label
        "evidence_text": str,     # escaped, truncated to 500 chars for display
        "confirmation_status": str,  # German label + badge class
        "is_active": bool,        # currently the active confirmed event
    }
],
```

### calculation_result.html

```python
{
    "case_id": str,
    "document_id": str,
    "candidate_index": int,
    "reference_date": str,       # "15.07.2026"
    "reference_source": str,     # "Bescheiddatum"
    "reference_method": str,     # "Automatisch erkannt"
    "duration_display": str,     # "14 Kalendertage (2 Wochen)"
    "calculated_date": str,      # "29.07.2026"
    "calculation_steps": [
        {
            "step_number": int,
            "operation": str,    # "Addition von 14 Kalendertagen"
            "input_date": str,
            "output_date": str,
            "amount": int,
        }
    ],
    "adjustments": [
        {
            "label": str,        # "Wochenendverschiebung"
            "applied": bool,     # always False in M6-A
            "note": str,         # "Nicht angewendet"
        }
    ],
    "warnings": [{"code": str, "message": str, "severity": str}],
    "has_required_warnings": bool,   # True if CALCULATION_PREVIEW_ONLY + HUMAN_REVIEW_REQUIRED present
    "human_review_required": bool,   # always True
    "legal_validity_assessed": bool, # always False
}
```

### confirmation_history.html

```python
{
    "case_id": str,
    "document_id": str,
    "candidate_index": int,
    "entries": [
        {
            "confirmation_id": str,
            "confirmed_date": str | None,
            "event_type": str,       # German label
            "confirmation_method": str,  # German label
            "confirmation_status": str,  # German label
            "confirmed_at": str,     # formatted datetime
            "supersedes": str | None,
            "is_current": bool,
        }
    ],
    "current_status": str,           # German label
    "has_active_confirmation": bool,
}
```

### error.html

```python
{
    "error_code": str,           # stable code, NOT displayed prominently
    "message": str,              # user-friendly German message
    "details": str | None,       # additional context, NO sensitive data
    "back_url": str | None,      # link to return
    "back_label": str,           # "Zurück zur Fallübersicht"
}
```

## Data Flow

```
Application Service (returns domain objects)
  → UI Route Handler (maps to view model)
  → Jinja2 Template (renders {{ variables }} with autoescaping)
  → Browser (displays safe HTML)
```

No view model field bypasses autoescaping. No DOM manipulation with innerHTML. No raw HTML from API responses.
