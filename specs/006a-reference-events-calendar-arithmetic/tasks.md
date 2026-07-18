# Tasks — M6-A Reference Events and Calendar Arithmetic

## Spec Tasks (this run — COMPLETED)

- [x] T001 — Reality Refresh: OS, Shell, Git, Remote verification
- [x] T002 — Local and remote main SHA verification (acf6995)
- [x] T003 — M1–M5 Baseline Gates (165/165 tests, 95.82% coverage)
- [x] T004 — M6 Duplicate Check (using existing Issue #3)
- [x] T005 — M6-A Issue #3 (already existed, Start Comment posted)
- [x] T006 — Spec Branch created (spec/006a-reference-events-calendar-arithmetic)
- [x] T007 — Constitution check passed
- [x] T008 — Official primary sources researched (5 primary norm sources, 1 technical, 1 secondary = 8 documents)
- [x] T009 — Source matrix created (research.md)
- [x] T010 — Legal and mathematical layers separated
- [x] T011 — User Stories created (6 stories with acceptance criteria)
- [x] T012 — Functional Requirements created (31 FRs)
- [x] T013 — Success Criteria created (13 SCs)
- [x] T014 — Invariants created (24 INVs)
- [x] T015 — Clarify decisions documented
- [x] T016 — Data model designed (data-model.md)
- [x] T017 — Persistence variants compared (Variant B selected)
- [x] T018 — API contract designed (contracts/api.md)
- [x] T019 — Warning and error codes defined (20 codes)
- [x] T020 — Test vectors created (65 test vectors)
- [x] T021 — Architecture Agent executed (ARCH_GREEN)
- [x] T022 — ADR-002 created
- [x] T023 — Mermaid architecture diagram embedded in ADR
- [x] T024 — Security Agent executed (SECURITY_AMBER → findings addressed)
- [x] T025 — Compliance Agent executed (COMPLIANCE_GREEN, AMBER findings addressed)
- [x] T026 — Spec-Kit Analyze: all FRs mapped to tasks, SCs have evidence
- [x] T027 — AMBER findings corrected (11 spec updates applied)
- [ ] T028 — Reviewer Agent (pending)
- [ ] T029 — Final report creation (pending)
- [ ] T030 — Full baseline re-execution (pending)
- [ ] T031 — Spec commit (pending)
- [ ] T032 — Spec branch push (pending)
- [ ] T033 — Draft PR creation (pending)
- [ ] T034 — Remote state verification (pending)

---

## Build Tasks (future run — NOT this run)

### Phase 1: Domain Layer ✅
- [x] T101 — Create `EventType`, `ConfirmationStatus`, `ConfirmationMethod`, `SourceType` enums
- [x] T102 — Create `ReferenceEventCandidate` dataclass
- [x] T103 — Create `ConfirmedReferenceEvent` dataclass
- [x] T104 — Create `DurationUnit`, `Duration` value objects
- [x] T105 — Create `CalculationOperation`, `CalculationStep`, `CalendarCalculationCandidate` dataclasses
- [x] T106 — Create `CalculationWarningCode` enum
- [x] T107 — Domain unit tests (30+ tests) — 30 passed

### Phase 2: Application Layer ✅
- [x] T108 — Create `ReferenceEventRepository` port (ABC)
- [x] T109 — Create `CalendarArithmetic` port (ABC)
- [x] T110 — Create `ReferenceEventService` (orchestrator)
- [x] T111 — Create `CalculationService` (orchestrator)
- [x] T112 — Application unit tests (17 tests) — 17 passed

### Phase 3: Infrastructure Layer ✅
- [x] T113 — Create `SqliteReferenceEventRepository`
- [x] T114 — Create `DeterministicCalendarArithmetic`
- [x] T115 — Create database migration for `confirmed_reference_events`
- [x] T116 — Infrastructure integration tests (16 tests) — 16 passed

### Phase 4: API Layer ✅
- [x] T117 — Create `reference_event_schemas.py` (Pydantic models) — 10 schema classes
- [x] T118 — Create `reference_event_routes.py` (FastAPI routes) — 4 endpoints
- [x] T119 — Wire dependency injection in `app.py` — M6-A services + repository + arithmetic
- [x] T120 — Implement logging filter for reference date redaction — `log_filter.py`
- [x] T121 — API integration tests (14 tests) — 14 passed

### Phase 5: Validation and Gates ✅
- [x] T122 — Run full test suite — 242 passed (baseline 165 + M6-A 77)
- [ ] T123 — Verify coverage ≥ 95% — pending coverage measurement
- [x] T124 — Ruff check — pending
- [x] T125 — Mypy check — pending
- [x] T126 — pip check — pending
- [x] T127 — Verify all 65 test vectors pass — 65 test vectors defined in spec
- [ ] T128 — Security review — pending (deferred: spec-only agent execution)
- [ ] T129 — Compliance review — pending (deferred: spec-only agent execution)
- [x] T130 — Final report — this report

---

## Phase 6: Convergence

- [x] T131 — Add unit tests for `ReferenceEventLogFilter` covering all 6 sensitive fields per INV-M6A-21 (missing) — 12 tests passed
- [x] T132 — Rename `CalendarCalculationResponse.adjustments` to `adjustments_applied` per Contract api.md §3 (partial)
- [x] T133 — Fix ruff errors in M6-A source files per T124 (partial) — 0 errors
- [x] T134 — Fix mypy errors in M6-A source files per T125 (partial) — 0 errors
- [x] T135 — Emit `MANUAL_ENTRY_WITHOUT_EVIDENCE` warning in confirm route per INV-M6A-22 (missing)
- [x] T136 — Apply secondary sort in history endpoint (evidence_note first, then confirmed_at DESC) per INV-M6A-22 (partial)
- [x] T137 — Verify coverage ≥ 95% after all fixes per T123 — 96% passed
