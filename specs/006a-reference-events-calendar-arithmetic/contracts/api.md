# API Contract — M6-A Reference Events and Calendar Arithmetic

## Overview

M6-A extends the existing M5 API with three new endpoints:
1. List reference event candidates for a deadline candidate
2. Confirm/reject/revoke a reference event
3. Request a calculation preview

All endpoints follow the existing FastAPI conventions and error envelope pattern.

---

## Base Path

```
/api/v1/cases/{case_id}/documents/{document_id}/deadline-candidates/{candidate_id}
```

> **⚠️ Note on `candidate_id` naming:** The path parameter `{candidate_id}` is an **int** (0-based index identifying the M5 DeadlineCandidate within the document). This is distinct from the `candidate_id` field in the request/response bodies, which is a **UUID** identifying a specific `ReferenceEventCandidate`. These are different identifiers at different levels — the path selects which M5 candidate to act on, the body field selects which detected reference event within that candidate.

---

## Endpoints

### 1. List Reference Event Candidates

```http
GET /api/v1/cases/{case_id}/documents/{document_id}/deadline-candidates/{candidate_id}/reference-events
```

**Description:** Returns all possible reference events for a given deadline candidate. Each candidate is UNCONFIRMED initially.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| case_id | UUID | yes | Case identifier |
| document_id | UUID | yes | Document identifier |
| candidate_id | int | yes | Index of the M5 DeadlineCandidate (0-based) |

**Response 200:**
```json
{
  "candidate_id": 0,
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "reference_events": [
    {
      "candidate_id": "550e8400-e29b-41d4-a716-446655440001",
      "event_type": "issue_date",
      "suggested_date": "2026-07-15",
      "source_type": "auto_detected",
      "evidence_text": "Bescheid vom 15.07.2026",
      "start_offset": 120,
      "end_offset": 142,
      "confirmation_status": "unconfirmed"
    },
    {
      "candidate_id": "550e8400-e29b-41d4-a716-446655440002",
      "event_type": "delivery",
      "suggested_date": null,
      "source_type": "auto_detected",
      "evidence_text": "innerhalb von zwei Wochen nach Zustellung",
      "start_offset": 200,
      "end_offset": 239,
      "confirmation_status": "unconfirmed"
    }
  ],
  "warnings": [
    {
      "code": "MULTIPLE_REFERENCE_EVENTS",
      "message": "Mehrere mögliche Bezugsereignisse gefunden. Bitte wählen Sie das zutreffende Ereignis aus."
    },
    {
      "code": "REFERENCE_EVENT_NOT_CONFIRMED",
      "message": "Kein Bezugsereignis wurde bestätigt. Eine Berechnung ist erst nach Bestätigung möglich."
    }
  ],
  "human_review_required": true
}
```

**Response 200 (Empty — no reference events detected):**
```json
{
  "candidate_id": 0,
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "reference_events": [],
  "warnings": [],
  "human_review_required": true
}
```

**Error Cases:**
| HTTP | Code | Description |
|------|------|-------------|
| 404 | CASE_NOT_FOUND | Case does not exist |
| 404 | DOCUMENT_NOT_FOUND | Document does not exist |
| 400 | INVALID_CANDIDATE_INDEX | candidate_id out of range |
| 400 | NOT_A_RELATIVE_CANDIDATE | The candidate is not RELATIVE_PERIOD (explicit dates don't need reference events) |

---

### 2. Confirm/Reject/Revoke Reference Event

```http
POST /api/v1/cases/{case_id}/documents/{document_id}/deadline-candidates/{candidate_id}/reference-events/confirm
```

**Description:** User confirms, rejects, or revokes a reference event. This is the mandatory gate before any calculation.

**Request Body (Confirm — auto-suggested candidate accepted):**
```json
{
  "action": "confirm",
  "candidate_id": "550e8400-e29b-41d4-a716-446655440001",
  "event_type": "issue_date",
  "confirmed_date": "2026-07-15",
  "source_type": "auto_detected",
  "evidence_note": "Datum aus Bescheid vom 15.07.2026"
}
```

**Request Body (Confirm — manual entry, no pre-existing candidate):**
```json
{
  "action": "confirm",
  "event_type": "delivery",
  "confirmed_date": "2026-07-15",
  "source_type": "user_manual",
  "evidence_note": "Zustellungsdatum laut Zustellungsurkunde"
}
```

**Request Body (Reject):**
```json
{
  "action": "reject",
  "candidate_id": "550e8400-e29b-41d4-a716-446655440002",
  "event_type": "delivery"
}
```

**Request Body (Revoke):**
```json
{
  "action": "revoke",
  "confirmation_id": "550e8400-e29b-41d4-a716-446655440003"
}
```

**Request Schema:**
```json
{
  "action": "string - 'confirm', 'reject', 'revoke' (required)",
  "candidate_id": "UUID | null - identifies which ReferenceEventCandidate is being acted on. Required for confirm/reject on existing candidates. null for manual entries without a pre-existing candidate.",
  "event_type": "string (EventType enum) - required for confirm/reject, optional for revoke",
  "confirmed_date": "string (ISO date YYYY-MM-DD) | null - required for confirm",
  "source_type": "string (SourceType enum) - required for confirm (auto_detected, user_manual, user_corrected), max 100 chars",
  "confirmation_id": "UUID | null - required for revoke",
  "evidence_note": "string - optional, max 2000 chars. TRANSIENT: only returned in API response, NOT persisted to database."
}
```

**source_type → confirmation_method mapping:**
| source_type | confirmation_method |
|-------------|-------------------|
| `auto_detected` | `auto_suggested` |
| `user_manual` | `manually_entered` |
| `user_corrected` | `corrected` |

**evidence_note lifecycle:** This field is transient (session-only). It is returned in the API response for immediate user reference but is NOT stored in the `confirmed_reference_events` database table. It is NOT written to application logs. Its sole purpose is displaying the user's note in the current confirmation response.

**Response 200 (Confirmed):**
```json
{
  "confirmation_id": "550e8400-e29b-41d4-a716-446655440003",
  "candidate_id": "550e8400-e29b-41d4-a716-446655440001",
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "issue_date",
  "confirmed_date": "2026-07-15",
  "source_type": "auto_detected",
  "confirmation_method": "auto_suggested",
  "confirmed_at": "2026-07-14T09:30:00Z",
  "confirmation_status": "confirmed",
  "supersedes_confirmation_id": null,
  "warnings": [
    {
      "code": "HUMAN_REVIEW_REQUIRED",
      "message": "Die Bestätigung ersetzt keine rechtliche Prüfung."
    }
  ],
  "human_review_required": true
}
```

**Response 200 (Rejected):**
```json
{
  "confirmation_id": "550e8400-e29b-41d4-a716-446655440004",
  "candidate_id": "550e8400-e29b-41d4-a716-446655440002",
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "delivery",
  "confirmed_date": null,
  "source_type": "auto_detected",
  "confirmation_status": "rejected",
  "confirmed_at": "2026-07-14T09:31:00Z",
  "warnings": [
    {
      "code": "REFERENCE_EVENT_REJECTED",
      "message": "Bezugsereignis abgelehnt. Eine Berechnung ist nicht möglich."
    }
  ],
  "human_review_required": true
}
```

**Response 200 (Revoked):**
```json
{
  "confirmation_id": "550e8400-e29b-41d4-a716-446655440005",
  "supersedes_confirmation_id": "550e8400-e29b-41d4-a716-446655440003",
  "confirmation_status": "revoked",
  "confirmed_at": "2026-07-14T09:35:00Z",
  "previous_confirmation": {
    "confirmation_id": "550e8400-e29b-41d4-a716-446655440003",
    "confirmed_date": "2026-07-15",
    "confirmation_status": "superseded"
  },
  "warnings": [
    {
      "code": "REFERENCE_EVENT_REVOKED",
      "message": "Bestätigung widerrufen. Eine Berechnung ist nicht mehr möglich."
    }
  ],
  "human_review_required": true
}
```

**Error Cases:**
| HTTP | Code | Description |
|------|------|-------------|
| 404 | CASE_NOT_FOUND | Case does not exist |
| 404 | DOCUMENT_NOT_FOUND | Document does not exist |
| 404 | CONFIRMATION_NOT_FOUND | confirmation_id not found (for revoke) |
| 400 | INVALID_CONFIRMATION_ACTION | Unknown action |
| 400 | INVALID_DATE | confirmed_date is not a valid ISO date |
| 400 | ALREADY_CONFIRMED | Reference event is already confirmed (revoke first) |
| 400 | ALREADY_REVOKED | Reference event is already revoked |
| 400 | INVALID_CANDIDATE_REFERENCE | The provided `candidate_id` (UUID) does not reference any known ReferenceEventCandidate. No silent fallback to manual entry. |
| 422 | VALIDATION_ERROR | Request body validation failed |

---

### 3. Calculation Preview

```http
POST /api/v1/cases/{case_id}/documents/{document_id}/deadline-candidates/{candidate_id}/calculation-preview
```

**Description:** Request a non-binding arithmetic calculation preview based on a confirmed reference date and M5-detected duration.

**Prerequisites:**
- A `ConfirmedReferenceEvent` must exist (status: `confirmed`)
- The M5 `DeadlineCandidate` must be of kind `RELATIVE_PERIOD` with valid amount and unit

**Request Body:**
```json
{
  "confirmation_id": "550e8400-e29b-41d4-a716-446655440003"
}
```

**Response 200:**
```json
{
  "result_type": "calculated_candidate",
  "calculation_id": "550e8400-e29b-41d4-a716-446655440010",
  "reference_event": {
    "confirmation_id": "550e8400-e29b-41d4-a716-446655440003",
    "event_type": "issue_date",
    "confirmed_date": "2026-07-15",
    "confirmation_status": "confirmed",
    "confirmation_method": "auto_suggested",
    "source_type": "user_manual"
  },
  "duration": {
    "amount": 2,
    "unit": "week",
    "calendar_days": 14
  },
  "calculated_date": "2026-07-29",
  "calculation_steps": [
    {
      "step": 1,
      "operation": "ADD_CALENDAR_WEEKS",
      "input_date": "2026-07-15",
      "amount": 14,
      "output_date": "2026-07-29"
    }
  ],
  "adjustments": {
    "weekend_adjustment_applied": false,
    "holiday_adjustment_applied": false,
    "legal_rule_applied": false,
    "delivery_fiction_applied": false,
    "announcement_fiction_applied": false
  },
  "legal_validity_assessed": false,
  "human_review_required": true,
  "warnings": [
    {
      "code": "CALCULATION_PREVIEW_ONLY",
      "message": "Diese Berechnung ist eine unverbindliche Vorschau. Sie stellt KEINE rechtlich verbindliche Frist dar."
    },
    {
      "code": "NO_WEEKEND_OR_HOLIDAY_ADJUSTMENT",
      "message": "Wochenenden und Feiertage wurden nicht berücksichtigt. Die tatsächliche rechtliche Frist kann abweichen."
    },
    {
      "code": "NO_DELIVERY_OR_ANNOUNCEMENT_RULE_APPLIED",
      "message": "Es wurden keine Zustellungs- oder Bekanntgaberegeln angewendet."
    },
    {
      "code": "HUMAN_REVIEW_REQUIRED",
      "message": "Menschliche Prüfung zwingend erforderlich. Nicht zur Fristwahrung geeignet."
    }
  ]
}
```

**Error Cases:**
| HTTP | Code | Description |
|------|------|-------------|
| 404 | CASE_NOT_FOUND | Case does not exist |
| 404 | DOCUMENT_NOT_FOUND | Document does not exist |
| 400 | INVALID_CANDIDATE_INDEX | candidate_id out of range |
| 400 | REFERENCE_EVENT_NOT_CONFIRMED | No confirmed reference event exists |
| 400 | REFERENCE_EVENT_REVOKED | Reference event was revoked |
| 400 | DURATION_NOT_AVAILABLE | M5 candidate has no usable duration |
| 400 | UNSUPPORTED_DURATION_UNIT | Duration unit is MONTH, YEAR, etc. |
| 400 | INVALID_DURATION_AMOUNT | Duration amount is zero or negative |
| 400 | DURATION_LIMIT_EXCEEDED | Duration exceeds maximum |
| 404 | CONFIRMATION_NOT_FOUND | Specified confirmation_id does not exist |
| 422 | VALIDATION_ERROR | Request body validation failed |

---

### 4. Get Confirmation History

```http
GET /api/v1/cases/{case_id}/documents/{document_id}/deadline-candidates/{candidate_id}/reference-events/history
```

**Description:** Returns the full audit trail of all confirmations for this candidate.

**Response 200:**
```json
{
  "candidate_id": 0,
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "confirmations": [
    {
      "confirmation_id": "550e8400-e29b-41d4-a716-446655440005",
      "confirmed_date": null,
      "event_type": "issue_date",
      "confirmation_status": "revoked",
      "confirmed_at": "2026-07-14T09:35:00Z",
      "supersedes_confirmation_id": "550e8400-e29b-41d4-a716-446655440003"
    },
    {
      "confirmation_id": "550e8400-e29b-41d4-a716-446655440003",
      "confirmed_date": "2026-07-15",
      "event_type": "issue_date",
      "confirmation_status": "superseded",
      "confirmed_at": "2026-07-14T09:30:00Z",
      "supersedes_confirmation_id": null
    }
  ],
  "current_status": "revoked",
  "human_review_required": true
}
```

---

## Error Envelope

All error responses follow the existing pattern:

```json
{
  "detail": {
    "code": "UNSUPPORTED_DURATION_UNIT",
    "message": "Die Dauer-Einheit 'month' wird in diesem Build nicht unterstützt. Nur 'day' und 'week' sind verfügbar."
  }
}
```

---

## Validation & Error Behavior

### Invalid UUID Formats

All path parameters typed as `UUID` (`case_id`, `document_id`) are validated by FastAPI's built-in UUID parser. Invalid UUID strings (e.g., `"abc"`, `"not-a-uuid"`) produce an automatic **422 VALIDATION_ERROR** response before the endpoint logic executes. No explicit validation logic is required in the endpoint implementation — this is inherited from the project's FastAPI baseline.

### Field Size Constraints

Request body fields have documented length limits enforced at the API layer:

| Field | Max Length | Error Code | Endpoints |
|-------|-----------|------------|-----------|
| `evidence_note` | 2000 chars | `FIELD_TOO_LONG` | POST confirm |
| `source_reference` | 100 chars | `FIELD_TOO_LONG` | POST confirm |
| `confirmed_by` | 100 chars | `FIELD_TOO_LONG` | POST confirm |

### Single-User Context

The API operates in a **single-user local context** (see INV-M6A-19). This means:
- No authentication or authorization is required
- No optimistic locking or conflict resolution is implemented
- No concurrent-access safeguards exist — rapid sequential requests are processed in order but without transaction isolation
- Cross-document validation (verifying that a `confirmation_id` belongs to the path's `document_id`) is **not enforced** — the user is expected to operate within the correct document context
- The `confirmed_by` field is an optional label for future multi-user extension, not an authenticated identity

---

## Resource Relationships

```
Case
 └── Document
      └── DeadlineCandidate (from M5, index-based)
           ├── ReferenceEventCandidate[] (GET)
           ├── ConfirmedReferenceEvent (POST confirm)
           ├── Confirmation History (GET history)
           └── CalendarCalculationCandidate (POST calculation-preview)
```

---

## Warnings vs Errors

**Warnings** (200 response): Non-blocking informational or safety messages (e.g., `MULTIPLE_REFERENCE_EVENTS`, `CALCULATION_PREVIEW_ONLY`)

**Errors** (4xx response): Blocking conditions that prevent the operation (e.g., `UNSUPPORTED_DURATION_UNIT`, `REFERENCE_EVENT_NOT_CONFIRMED`)
