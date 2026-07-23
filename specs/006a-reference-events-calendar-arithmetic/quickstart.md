# Quickstart — M6-A Reference Events and Calendar Arithmetic

## Overview

This guide provides runnable validation scenarios for the M6-A feature (confirmed reference events + pure calendar arithmetic). Use these to verify end-to-end behavior once the build phase begins.

**This is a spec-phase artifact.** No implementation code exists yet. All references to API endpoints and domain entities are forward-looking against the [API contract](contracts/api.md) and [data model](data-model.md).

---

## Prerequisites

- Python 3.11+
- PrivateLegalNavigator installed and running (`pip install -e ".[dev]"`, then `python -m private_legal_navigator`)
- A case with at least one PDF document and an M5 deadline candidate of kind `RELATIVE_PERIOD`
- pytest installed (dev dependency)

---

## Setup

### 1. Start the application

```bash
python -m private_legal_navigator
```

Expected: Server starts on `http://127.0.0.1:8000`

### 2. Create a test case with a PDF containing a relative deadline

```bash
# Create case
curl -s -X POST http://127.0.0.1:8000/api/v1/cases \
  -H "Content-Type: application/json" \
  -d '{"title": "SYNTHETISCH – M6-A Testfall", "description": "Testfall für Kalenderarithmetik"}'

# Upload PDF with text containing a relative deadline
# (Use a synthetic PDF generated for testing)
curl -s -X POST "http://127.0.0.1:8000/api/v1/cases/{case_id}/documents" \
  -F "file=@test_synthetic_deadline.pdf"
```

### 3. Run M5 extraction

```bash
curl -s -X POST "http://127.0.0.1:8000/api/v1/cases/{case_id}/documents/{doc_id}/deadline-candidates"
```

Expected: Response includes at least one candidate with `kind=RELATIVE_PERIOD`

---

## Validation Scenarios

### Scenario 1: Reference Event Detection

**Command:**
```bash
curl -s "http://127.0.0.1:8000/api/v1/cases/{case_id}/documents/{doc_id}/deadline-candidates/0/reference-events"
```

**Expected outcome:**
- HTTP 200
- `reference_events` array with ≥ 1 entries
- Each entry has `confirmation_status: "unconfirmed"`
- Each entry has `candidate_id` (UUID), `event_type`, `suggested_date` (or null), `evidence_text`, `start_offset`, `end_offset`
- `warnings` contains `REFERENCE_EVENT_NOT_CONFIRMED`
- `human_review_required: true`

**Covers:** US1, FR-M6A-001, FR-M6A-002, TV-058

---

### Scenario 2: Confirm Reference Event

**Command:**
```bash
curl -s -X POST "http://127.0.0.1:8000/api/v1/cases/{case_id}/documents/{doc_id}/deadline-candidates/0/reference-events/confirm" \
  -H "Content-Type: application/json" \
  -d '{"action": "confirm", "candidate_id": "<uuid-from-scenario-1>", "event_type": "issue_date", "confirmed_date": "2026-07-15", "source_type": "auto_detected"}'
```

**Expected outcome:**
- HTTP 200
- `confirmation_id` populated (UUID)
- `confirmation_status: "confirmed"`
- `confirmation_method: "auto_suggested"`
- `confirmed_at` is ISO datetime with timezone
- `supersedes_confirmation_id: null`
- `warnings` contains `HUMAN_REVIEW_REQUIRED`

**Covers:** US2, FR-M6A-003–006, TV-002, TV-003, TV-060, TV-062

---

### Scenario 3: Manual Date Entry (No Pre-existing Candidate)

**Command:**
```bash
curl -s -X POST "http://127.0.0.1:8000/api/v1/cases/{case_id}/documents/{doc_id}/deadline-candidates/0/reference-events/confirm" \
  -H "Content-Type: application/json" \
  -d '{"action": "confirm", "event_type": "delivery", "confirmed_date": "2026-07-15", "source_type": "user_manual"}'
```

**Expected outcome:**
- HTTP 200
- `candidate_id: null`
- `confirmation_method: "manually_entered"`
- `source_type: "user_manual"`

**Covers:** US2, FR-M6A-008, TV-051, TV-061, TV-063

---

### Scenario 4: Calculation Preview

**Command:**
```bash
curl -s -X POST "http://127.0.0.1:8000/api/v1/cases/{case_id}/documents/{doc_id}/deadline-candidates/0/calculation-preview" \
  -H "Content-Type: application/json" \
  -d '{"confirmation_id": "<uuid-from-scenario-2>"}'
```

**Expected outcome:**
- HTTP 200
- `result_type: "calculated_candidate"`
- `calculated_date` is valid ISO date (YYYY-MM-DD)
- `calculation_steps` array with ≥ 1 step, each with `step`, `operation`, `input_date`, `amount`, `output_date`
- `legal_validity_assessed: false`
- `human_review_required: true`
- All `adjustments.*` fields `false`
- `warnings` contains `CALCULATION_PREVIEW_ONLY`, `NO_WEEKEND_OR_HOLIDAY_ADJUSTMENT`, `NO_DELIVERY_OR_ANNOUNCEMENT_RULE_APPLIED`, `HUMAN_REVIEW_REQUIRED`

**Covers:** US3, US4, US5, FR-M6A-012–027, TV-010–022, TV-036–048

---

### Scenario 5: Reject Reference Event

**Command:**
```bash
curl -s -X POST "http://127.0.0.1:8000/api/v1/cases/{case_id}/documents/{doc_id}/deadline-candidates/0/reference-events/confirm" \
  -H "Content-Type: application/json" \
  -d '{"action": "reject", "candidate_id": "<uuid>", "event_type": "delivery"}'
```

**Expected outcome:**
- HTTP 200
- `confirmation_status: "rejected"`
- `confirmed_date: null`
- `warnings` contains `REFERENCE_EVENT_REJECTED`

**Covers:** FR-M6A-007, TV-004

---

### Scenario 6: Revoke Confirmation

**Command:**
```bash
curl -s -X POST "http://127.0.0.1:8000/api/v1/cases/{case_id}/documents/{doc_id}/deadline-candidates/0/reference-events/confirm" \
  -H "Content-Type: application/json" \
  -d '{"action": "revoke", "confirmation_id": "<uuid-from-scenario-2>"}'
```

**Expected outcome:**
- HTTP 200
- `confirmation_status: "revoked"`
- `supersedes_confirmation_id` references the revoked confirmation
- `previous_confirmation` block shows the superseded record
- `warnings` contains `REFERENCE_EVENT_REVOKED`

**Covers:** US6, FR-M6A-010, TV-005

---

### Scenario 7: Confirmation History

**Command:**
```bash
curl -s "http://127.0.0.1:8000/api/v1/cases/{case_id}/documents/{doc_id}/deadline-candidates/0/reference-events/history"
```

**Expected outcome (after confirming, changing, or revoking):**
- HTTP 200
- `confirmations` array with ≥ 1 entries, sorted by `confirmed_at` desc
- Each entry shows `confirmation_id`, `confirmed_date`, `event_type`, `confirmation_status`, `confirmed_at`
- `current_status` reflects the latest state

**Covers:** US6, FR-M6A-009, TV-055, TV-056, TV-057

---

### Scenario 8: Error — Unconfirmed Calculation

**Command:**
```bash
# Using a candidate with NO confirmed reference event
curl -s -X POST "http://127.0.0.1:8000/api/v1/cases/{case_id}/documents/{doc_id}/deadline-candidates/1/calculation-preview" \
  -H "Content-Type: application/json" \
  -d '{"confirmation_id": "<non-existent-or-revoked-id>"}'
```

**Expected outcome:**
- HTTP 400
- Error envelope: `{"detail": {"code": "REFERENCE_EVENT_NOT_CONFIRMED", "message": "..."}}`

**Covers:** INV-M6A-01, FR-M6A-011, TV-001

---

### Scenario 9: Error — Unsupported Duration Unit

**Prerequisite:** An M5 candidate with `unit=MONTH`, `unit=YEAR`, or equivalent.

**Command:**
```bash
curl -s -X POST "http://127.0.0.1:8000/api/v1/cases/{case_id}/documents/{doc_id}/deadline-candidates/0/calculation-preview" \
  -H "Content-Type: application/json" \
  -d '{"confirmation_id": "<valid-id>"}'
```

**Expected outcome (for MONTH/YEAR/BUSINESS_DAY/WORKING_DAY/HOUR):**
- HTTP 400
- Error envelope: `{"detail": {"code": "UNSUPPORTED_DURATION_UNIT", "message": "..."}}`

**Covers:** FR-M6A-014, INV-M6A-07, TV-027–031

---

### Scenario 10: Error — Invalid Duration

**Prerequisite:** An M5 candidate with `amount=0` or `amount<0`.

**Command:**
```bash
curl -s -X POST "http://127.0.0.1:8000/api/v1/cases/{case_id}/documents/{doc_id}/deadline-candidates/0/calculation-preview" \
  -H "Content-Type: application/json" \
  -d '{"confirmation_id": "<valid-id>"}'
```

**Expected outcome:**
- HTTP 400
- Error envelope: `{"detail": {"code": "INVALID_DURATION_AMOUNT", "message": "..."}}`

**Covers:** FR-M6A-015, FR-M6A-016, TV-023, TV-024

---

### Scenario 11: Error — Invalid Candidate Reference

**Command:**
```bash
curl -s -X POST "http://127.0.0.1:8000/api/v1/cases/{case_id}/documents/{doc_id}/deadline-candidates/0/reference-events/confirm" \
  -H "Content-Type: application/json" \
  -d '{"action": "confirm", "candidate_id": "00000000-0000-0000-0000-000000000000", "event_type": "issue_date", "confirmed_date": "2026-07-15", "source_type": "auto_detected"}'
```

**Expected outcome:**
- HTTP 400
- Error envelope: `{"detail": {"code": "INVALID_CANDIDATE_REFERENCE", "message": "..."}}`
- No confirmation is created
- No silent fallback to manual entry

**Covers:** FR-M6A-031, Spec §Clarifications 2026-07-18

---

## Unit Test Validation

Run the existing test suite to confirm no regressions:

```bash
# Full test suite
pytest --cov=src/private_legal_navigator --cov-fail-under=90

# M6-A specific tests (once implemented)
pytest tests/unit/test_calendar_arithmetic.py -v
pytest tests/unit/test_reference_events.py -v
pytest tests/integration/test_confirmed_reference_repo.py -v
pytest tests/api/test_reference_event_routes.py -v
```

Expected: All tests pass, coverage ≥ 95% for new code.

---

## Static Analysis

```bash
ruff check src tests
mypy src
pip check
```

Expected: No errors introduced by M6-A code.

---

## Key References

| Artifact | Path | Purpose |
|----------|------|---------|
| Specification | [spec.md](spec.md) | Functional requirements, invariants, user stories |
| Data Model | [data-model.md](data-model.md) | Domain entities, enums, database schema |
| API Contract | [contracts/api.md](contracts/api.md) | All 4 endpoints with request/response schemas |
| Test Vectors | [test-vectors.md](test-vectors.md) | 64 specification test cases |
| Research | [research.md](research.md) | All 10 research questions answered |
| Plan | [plan.md](plan.md) | Implementation order, risk assessment, gates |
| Tasks | [tasks.md](tasks.md) | Task breakdown for all 5 implementation phases |
| ADR-002 | [docs/architecture/adr-002-confirmed-reference-events.md](../docs/architecture/adr-002-confirmed-reference-events.md) | Architecture decision with rationale |
| Requirements Checklist | [checklists/requirements.md](checklists/requirements.md) | Gate status for all quality criteria |

---

## Test Vectors Coverage

This quickstart covers **10 validation scenarios** mapping to the following test vectors from [test-vectors.md](test-vectors.md):

| Scenario | Covers TVs |
|----------|-----------|
| Reference Event Detection | TV-058, TV-059 |
| Confirm Reference Event | TV-002, TV-003, TV-060, TV-062 |
| Manual Date Entry | TV-051, TV-061, TV-063 |
| Calculation Preview | TV-010–022, TV-036–048 |
| Reject Event | TV-004 |
| Revoke Confirmation | TV-005 |
| Confirmation History | TV-055–057 |
| Unconfirmed Error | TV-001 |
| Unsupported Duration | TV-027–031 |
| Invalid Duration | TV-023–024 |
| Invalid Candidate Reference | FR-M6A-031 |

Full 64-vector validation is defined in the test suite (see `tasks.md` Phase 5, T127).
