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
- [x] T012 — Functional Requirements created (30 FRs)
- [x] T013 — Success Criteria created (13 SCs)
- [x] T014 — Invariants created (24 INVs)
- [x] T015 — Clarify decisions documented
- [x] T016 — Data model designed (data-model.md)
- [x] T017 — Persistence variants compared (Variant B selected)
- [x] T018 — API contract designed (contracts/api.md)
- [x] T019 — Warning and error codes defined (20 codes)
- [x] T020 — Test vectors created (57 test vectors)
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

### Phase 1: Domain Layer
- [ ] T101 — Create `EventType`, `ConfirmationStatus`, `ConfirmationMethod`, `SourceType` enums
- [ ] T102 — Create `ReferenceEventCandidate` dataclass
- [ ] T103 — Create `ConfirmedReferenceEvent` dataclass
- [ ] T104 — Create `DurationUnit`, `Duration` value objects
- [ ] T105 — Create `CalculationOperation`, `CalculationStep`, `CalendarCalculationCandidate` dataclasses
- [ ] T106 — Create `CalculationWarningCode` enum
- [ ] T107 — Domain unit tests (30+ tests)

### Phase 2: Application Layer
- [ ] T108 — Create `ReferenceEventRepository` port (ABC)
- [ ] T109 — Create `CalendarArithmetic` port (ABC)
- [ ] T110 — Create `ReferenceEventService` (orchestrator)
- [ ] T111 — Create `CalculationService` (orchestrator)
- [ ] T112 — Application unit tests (15+ tests)

### Phase 3: Infrastructure Layer
- [ ] T113 — Create `SqliteReferenceEventRepository`
- [ ] T114 — Create `DeterministicCalendarArithmetic`
- [ ] T115 — Create database migration for `confirmed_reference_events`
- [ ] T116 — Infrastructure integration tests (10+ tests)

### Phase 4: API Layer
- [ ] T117 — Create `reference_event_schemas.py` (Pydantic models)
- [ ] T118 — Create `reference_event_routes.py` (FastAPI routes)
- [ ] T119 — Wire dependency injection in `app.py`
- [ ] T120 — Implement logging filter for reference date redaction
- [ ] T121 — API integration tests (15+ tests)

### Phase 5: Validation and Gates
- [ ] T122 — Run full test suite
- [ ] T123 — Verify coverage ≥ 95%
- [ ] T124 — Ruff check
- [ ] T125 — Mypy check
- [ ] T126 — pip check
- [ ] T127 — Verify all 57 test vectors pass
- [ ] T128 — Security review
- [ ] T129 — Compliance review
- [ ] T130 — Final report
