# UI Routes Contract — M6-UI

## Route Design Principle

New `/ui/` routes render HTML templates using the existing Application Services. The `/api/v1/` JSON API is **unchanged**. UI routes are additive.

## Route Prefix

```
/ui
```

## Routes

### Case Navigation

#### GET /ui/cases
List all cases.

**Template:** `case_list.html`
**Context:** `CaseListView`
**Uses:** `CaseService.list_cases()`

#### GET /ui/cases/{case_id}
View case detail with document list.

**Template:** `case_detail.html`
**Context:** `CaseDetailView`
**Uses:** `CaseService.get_case()`, `DocumentService.get_documents_for_case()`
**Errors:** 404 → `error.html` with "Fall nicht gefunden"

### Document View

#### GET /ui/cases/{case_id}/documents/{document_id}
View document details and text preview.

**Template:** Extends `case_detail.html` with document panel
**Context:** Includes `DocumentSummary` with text preview
**Uses:** `DocumentService.get_document_text()`
**Errors:** 404 → document not found

### Deadline Workspace

#### GET /ui/cases/{case_id}/documents/{document_id}/deadlines
View deadline candidate analysis workspace.

**Template:** `deadline_workspace.html`
**Context:** `DeadlineWorkspaceView`
**Uses:** `DeadlineExtractor.extract()`

#### POST /ui/cases/{case_id}/documents/{document_id}/deadlines
Trigger deadline analysis (same as GET, supports form submission).

**Redirect:** To GET on success
**Errors:** Re-render with error

### Reference Events

#### GET /ui/cases/{case_id}/documents/{document_id}/deadlines/{candidate_id}/events
View reference events for selected candidate.

**Template:** Extends `deadline_workspace.html` with events panel
**Context:** `ReferenceEventsView`
**Uses:** `EventService.get_reference_events()`

### Confirmation Actions

#### POST /ui/cases/{case_id}/documents/{document_id}/deadlines/{candidate_id}/confirm
Confirm, reject, or manually enter a reference date.

**Form fields:**
- `action`: "confirm" | "reject" | "manual"
- `candidate_uuid`: UUID of the reference event candidate (for confirm)
- `event_type`: Event type string
- `confirmed_date`: Date string YYYY-MM-DD (for confirm/manual)
- `source_type`: "auto_detected" | "user_manual" | "user_corrected"
- `evidence_note`: Optional note

**Redirect:** To GET events page on success (303 See Other)
**Errors:** Re-render events page with error message
**Uses:** `EventService.confirm()`, `EventService.reject()`
**Validation:** Server-side; date range 1900–2099; required fields

### Calculation Preview

#### GET /ui/cases/{case_id}/documents/{document_id}/deadlines/{candidate_id}/preview
View calculation preview page (renders only if confirmed).

**Template:** `calculation_result.html`
**Context:** `CalculationPreviewView`
**Uses:** None (display-only)

#### POST /ui/cases/{case_id}/documents/{document_id}/deadlines/{candidate_id}/preview
Request calculation preview.

**Form fields:**
- `confirmation_id`: UUID of the active confirmation

**Redirect:** To GET preview on success
**Errors:** Re-render workspace with error
**Uses:** `EventService.calculate_preview()`

### History

#### GET /ui/cases/{case_id}/documents/{document_id}/deadlines/{candidate_id}/history
View confirmation history.

**Template:** `confirmation_history.html`
**Context:** `HistoryView`
**Uses:** `EventService.get_history()`

### Revoke

#### POST /ui/cases/{case_id}/documents/{document_id}/deadlines/{candidate_id}/revoke
Revoke a confirmation. Requires confirmation_id in form data.

**Form fields:**
- `confirmation_id`: UUID of the confirmation to revoke

**Redirect:** To GET events page on success
**Errors:** Re-render with error
**Uses:** `EventService.revoke()`

## Error Handling

All errors render `error.html` with:
- User-friendly German message
- Stable error code (for debugging, not displayed prominently)
- Back link to return to previous page
- No sensitive IDs in error text
- No stack traces

## Security Headers

All UI routes include:
```
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; font-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: no-referrer
```

Case-related routes also include:
```
Cache-Control: no-store, max-age=0
```

## Host Validation

All requests require `Host` header matching `127.0.0.1:8000` or `localhost:8000`. Mismatched Host returns 400.
