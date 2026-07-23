# UI Routes Contract — M6-UI

## Route Design Principle

New `/ui/` routes render HTML templates using Application Services. The `/api/v1/` JSON API is **unchanged**. UI routes are additive.

## Route Prefix

```
/ui
```

## Mandatory Security for All POST Routes

Every POST route requires:
1. Valid CSRF token (hidden form field)
2. Valid Origin header (or Referer as fallback)
3. Valid Host header (matching configured allowlist)
4. Idempotency key (hidden form field, for state-changing operations)

## Routes

### Case Navigation

#### GET /ui/
Redirect to case list.

#### GET /ui/cases
List all cases.

**Template:** `case_list.html`
**Uses:** `CaseService.list_cases()` (via app.state)
**Security Headers:** Full set (see security-headers contract)
**Cache:** `Cache-Control: no-store`

#### GET /ui/cases/{case_id}
View case detail with document list.

**Template:** `case_detail.html`
**Uses:** `CaseService`, `DocumentService`
**Errors:** 404 → `error.html` with "Fall nicht gefunden"
**Security Headers:** Full set
**Cache:** `Cache-Control: no-store`

### Document View

#### GET /ui/cases/{case_id}/documents/{document_id}
View document details and text preview.

**Template:** Extends `case_detail.html` with document panel
**Uses:** `DocumentService.get_document_text()`
**Errors:** 404 → document not found
**Security Headers:** Full set
**Cache:** `Cache-Control: no-store`

### Workspace

#### GET /ui/cases/{case_id}/documents/{document_id}/workspace
View deadline candidate analysis workspace.

**Template:** `workspace.html`
**Uses:** Deadline-related application services, `ReferenceEventService.get_reference_event_candidates()`
**Security Headers:** Full set
**Cache:** `Cache-Control: no-store`

### Confirmation Actions

All POST routes to `/ui/cases/{case_id}/documents/{document_id}/workspace`:

#### POST /ui/.../workspace/confirm
Confirm a reference event candidate.

**Form fields:**
- `csrf_token`: CSRF protection token
- `idempotency_key`: Unique per-action key
- `candidate_id`: UUID of the reference event candidate
- `event_type`: Event type string (from domain enum)
- `confirmed_date`: Date string YYYY-MM-DD
- `source_type`: "auto_detected" | "user_manual" | "user_corrected"
- `evidence_note`: Optional note (max 2000 chars)

**Server-side revalidation:**
1. Verify case exists and document belongs to case
2. Verify candidate belongs to document
3. Load confirmation, check current status
4. Reload candidate from canonical source
5. Validate date range (1900–2099)
6. Execute `ReferenceEventService.confirm()`

**Redirect:** GET workspace on success (303 See Other)
**Errors:** Re-render workspace with error
**CSRF:** Required (valid token + Origin)
**Idempotency:** Required

#### POST /ui/.../workspace/reject
Reject a reference event candidate.

**Form fields:**
- `csrf_token`
- `idempotency_key`
- `candidate_id`: UUID
- `event_type`: Event type string

**Server-side:** `ReferenceEventService.reject()`
**Redirect:** GET workspace (303)
**CSRF:** Required
**Idempotency:** Required

#### POST /ui/.../workspace/manual
Manually enter a reference date (no candidate).

**Form fields:**
- `csrf_token`
- `idempotency_key`
- `event_type`: Domain enum value
- `confirmed_date`: YYYY-MM-DD
- `evidence_note`: Recommended (warning if absent)

**Server-side:** `ReferenceEventService.confirm()` with `source_type=USER_MANUAL`, `confirmation_method=MANUALLY_ENTERED`
**Mapping:** This UI interaction maps to `source_type=user_manual`, NOT a non-existent action type.

#### POST /ui/.../workspace/correct
Correct a previously confirmed reference event.

**Form fields:**
- `csrf_token`
- `idempotency_key`
- `confirmation_id`: UUID of the confirmation to supersede
- `confirmed_date`: Corrected date
- `evidence_note`: Required for corrections

**Server-side:** `ReferenceEventService.confirm()` with `source_type=USER_CORRECTED`, `supersedes_confirmation_id`
**Result:** New CONFIRMED event; old → SUPERSEDED

### Calculation Preview

#### GET /ui/cases/{case_id}/documents/{document_id}/workspace/preview
View calculation preview page. Only available with active CONFIRMED confirmation.

**Server-side flow:**
1. Load confirmation by ID
2. Verify document/case membership (cross-resource check)
3. Verify confirmation status is CONFIRMED
4. Load candidate from canonical source to get duration
5. Execute `CalculationService.calculate_preview()`

**Template:** `preview_result.html`
**Prerequisite:** Active CONFIRMED confirmation
**Error:** If unconfirmed/revoked, return error page

#### POST /ui/.../workspace/preview
Request calculation preview.

**Form fields:**
- `csrf_token`
- `idempotency_key` (preview is idempotent — same inputs produce same output)
- `confirmation_id`: UUID of the active confirmation

**Server-side:** Same revalidation flow as GET preview
**Redirect:** GET preview on success (303)

### History

#### GET /ui/cases/{case_id}/documents/{document_id}/workspace/history
View confirmation history.

**Template:** `confirmation_history.html`
**Uses:** `ReferenceEventService.get_history()`
**Security Headers:** Full set
**Cache:** `Cache-Control: no-store`

### Revoke

#### POST /ui/.../workspace/revoke
Revoke a confirmation.

**Form fields:**
- `csrf_token`
- `idempotency_key`
- `confirmation_id`: UUID of the confirmation to revoke

**Server-side:** `ReferenceEventService.revoke()`
**Redirect:** GET workspace (303)
**CSRF:** Required
**Idempotency:** Required

## Error Codes and HTTP Status

| Condition | HTTP Status |
|-----------|------------|
| Invalid form data (missing fields, bad format) | 400 |
| CSRF token missing/invalid | 403 |
| Origin/Referer mismatch | 403 |
| Host header mismatch | 400 |
| Resource not found (case, doc, candidate, confirmation) | 404 |
| Idempotency replay / status conflict | 409 |
| Framework-level validation (if not remapped) | 422 |
| Internal error | 500 (sanitized, no stack trace) |

All error responses render `error.html` with:
- User-friendly German message
- Stable error code (internal, not displayed prominently)
- Back link to previous context
- No sensitive IDs, no stack traces, no internal path disclosure

## Privacy in URLs

URLs use only opaque UUIDs. No document titles, case names, dates, or other sensitive values appear in query strings, fragments, or URL paths that could leak via Referer. The `Referrer-Policy: no-referrer` header provides defense-in-depth.

## Security Headers

Every UI route response includes full security headers per `contracts/security-headers.md`.

## Host Validation

Every request's `Host` header is validated against a configurable allowlist derived from `Settings`. See `contracts/security-headers.md` for details.
