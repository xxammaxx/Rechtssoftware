# API Requirements Checklist — M6-A Reference Events and Calendar Arithmetic

**Purpose:** Validate the quality, clarity, completeness, and testability of API requirements for the M6-A feature.
**Created:** 2026-07-18
**Target Audience:** QA / Test Designer
**Depth:** Standard (20–25 items)

---

## Requirement Completeness

- [x] CHK001 — Are error response schemas (HTTP status code + error envelope structure) defined for every 4xx error across all 4 endpoints? [Completeness, Contract api.md §Error Cases tables]
- [x] CHK002 — Are request body validation requirements (required fields, field types, format constraints) specified for the confirm endpoint (3 action types) and calculation-preview endpoint? [Completeness, Contract api.md §Request Schema]
- [x] CHK003 — Are path parameter format constraints (UUID format for case_id/document_id, int range for candidate_id) documented as explicit API requirements? [Completeness, Gap]
- [x] CHK004 — Are the preconditions for the calculation-preview endpoint (must have a ConfirmedReferenceEvent with status=confirmed, M5 candidate must be RELATIVE_PERIOD) captured as formal requirements? [Completeness, Contract api.md §3 Prerequisites]
- [x] CHK005 — Is the GET confirmation history endpoint response schema fully defined, including the `current_status` aggregation field? [Completeness, Contract api.md §4 Response 200]

---

## Requirement Clarity

- [x] CHK006 — Is the dual use of `candidate_id` (as int path parameter indexing M5 candidates vs. UUID request body field identifying ReferenceEventCandidates) unambiguously documented with clear naming distinction? [Clarity, Contract api.md §Base Path, §Path Parameters vs. Request Schema]
- [x] CHK007 — Is the `source_type` → `confirmation_method` mapping rule explicitly stated as an API requirement (not just an implementation note)? [Clarity, Contract api.md §source_type→confirmation_method mapping]
- [x] CHK008 — Is the `evidence_note` transient lifecycle ("returned in response, NOT persisted, NOT logged") documented as a clear, testable API requirement? [Clarity, Contract api.md §evidence_note lifecycle, Spec §INV-M6A-20]
- [x] CHK009 — Is the distinction between "200 OK with warning codes" vs. "4xx error" unambiguous for all conditions? (e.g., why is MULTIPLE_REFERENCE_EVENTS a 200 warning while UNSUPPORTED_DURATION_UNIT is a 400 error?) [Clarity, Contract api.md §Warnings vs Errors]
- [x] CHK010 — Are the response fields for the reject and revoke actions clearly defined (which fields are present, which are null)? [Clarity, Contract api.md §Response 200 (Rejected), §Response 200 (Revoked)]

---

## Requirement Consistency

- [x] CHK011 — Do the field names in the API contract JSON examples match the data model dataclass attributes and the warning code table consistently (e.g., `confirmation_status` across all artifacts)? [Consistency, Contract api.md vs. data-model.md vs. Spec §Warncodes]
- [x] CHK012 — Are the required safety response fields (`human_review_required`, `legal_validity_assessed`) included in every endpoint response consistently? [Consistency, Spec §INV-M6A-11/12 vs. Contract api.md all 4 endpoints]
- [x] CHK013 — Does the `adjustments_applied` dict in the calculation-preview response match the fields listed in the spec's success criteria? [Consistency, Contract api.md §3 Response 200 vs. Spec §US5 ACs]
- [x] CHK014 — Are the error code strings in the API contract's error tables consistent with the warning/error code table in the spec? (e.g., `INVALID_CANDIDATE_INDEX` vs. spec listing) [Consistency, Contract api.md §Error Cases vs. Spec §Warncodes]

---

## Acceptance Criteria Quality

- [x] CHK015 — Can every user story acceptance criterion for API-observable behavior (US1–US6) be verified through endpoint responses alone? [Measurability, Spec §US1–US6 ACs]
- [x] CHK016 — Are the acceptance criteria for the confirmation state machine transitions (confirm → CONFIRMED, reject → REJECTED, revoke → REVOKED, supersede → SUPERSEDED) specified as testable API-level outcomes? [Measurability, Spec §US2/US6 ACs, Contract api.md §2]
- [x] CHK017 — Are the deterministic output requirements for the calculation-preview endpoint specified with measurable criteria (same inputs → same outputs on repeated calls)? [Measurability, Spec §FR-M6A-027, TV-048]

---

## Scenario Coverage

- [x] CHK018 — Are API requirements defined for the "no reference events found" scenario (empty `reference_events` array, appropriate warnings)? [Coverage, Contract api.md §1 Response 200 (Empty)]
- [x] CHK019 — Are API requirements defined for attempting calculation-preview with a revoked confirmation? [Coverage, Spec §US6 ACs, TV-005, Contract api.md §3]
- [x] CHK020 — Are requirements defined for the "candidate_id (int) out of range" error path for all endpoints using the M5 candidate index? [Coverage, Contract api.md §1/2/3 Error Cases: INVALID_CANDIDATE_INDEX]

---

## Edge Case Coverage

- [x] CHK021 — Are API requirements defined for invalid UUID format in path parameters (case_id, document_id)? [Edge Case, Contract api.md §Validation & Error Behavior]
- [x] CHK022 — Are API requirements defined for attempting actions on a confirmation that belongs to a different document than the path's document_id? [Edge Case, Contract api.md §Validation & Error Behavior — documented as intentional non-requirement: single-user context, cross-document validation not enforced]
- [x] CHK023 — Are requirements specified for the confirm endpoint receiving a `candidate_id` (UUID body field) that does not correspond to any known ReferenceEventCandidate? [Edge Case, Spec §FR-M6A-031]
- [x] CHK024 — Are requirements defined for concurrent or rapid sequential requests (e.g., confirm → calculate → revoke → calculate)? [Edge Case, Contract api.md §Validation & Error Behavior — documented as intentional non-requirement: single-user context, no concurrent-access safeguards]

---

## Non-Functional Requirements

- [x] CHK025 — Are network isolation requirements for the API layer documented (no external requests triggered during any endpoint handling)? [NFR, Spec §INV-M6A-15, FR-M6A-029]
- [x] CHK026 — Is the determinism of the calculation-preview endpoint captured as a non-functional API requirement? [NFR, Spec §FR-M6A-027]
- [x] CHK027 — Are response size/documentation limits implied by the field size constraints (e.g., evidence_note max 2000 chars) reflected in the API contract? [NFR, Contract api.md §Validation & Error Behavior — Field Size Constraints table]

---

## Dependencies & Assumptions

- [x] CHK028 — Is the assumption that M5 deadline candidates exist and are computed before M6-A endpoints are called documented as an API precondition? [Assumption, Contract api.md §Base Path, §3 Prerequisites]
- [x] CHK029 — Is the single-user / no-concurrent-access assumption explicitly stated for the API layer (no optimistic locking, no conflict resolution)? [Assumption, Contract api.md §Validation & Error Behavior — Single-User Context]
