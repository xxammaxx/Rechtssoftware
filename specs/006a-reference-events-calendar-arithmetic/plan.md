# Plan — M6-A Reference Events and Calendar Arithmetic

## Overview

This plan maps the specification to an implementation strategy. No implementation occurs in this run — this is a specification artifact for the future build.

---

## Technical Context

### Technology Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Language | Python 3.11+ | Inherited from project base |
| Web Framework | FastAPI | Inherited from M1; existing route patterns reused |
| Database | SQLite | Inherited from M1; local-only, no server needed |
| Date/Time Library | stdlib `datetime` only | All arithmetic within stdlib capabilities; no external dependency needed |
| Test Framework | pytest | Inherited from M1; existing test infrastructure |
| Static Analysis | ruff + mypy | Inherited from M1 |
| Schema Migrations | Manual SQL | One new table; no ORM migration framework needed |

### Constraints

| Constraint | Source | Impact |
|------------|--------|--------|
| No external dependencies beyond stdlib for domain/infrastructure | INV-M6A-15 | CalendarArithmetic must use only `datetime.timedelta` |
| No external network requests | INV-M6A-15 | No holiday data APIs, no CVE databases, no remote validation |
| No holiday or weekend logic | INV-M6A-08 | `adjustments.weekend_*` and `holiday_*` always `false` |
| Date range: 1900-01-01 to 2099-12-31 | INV-M6A-23 | Input validation + post-calculation range check |
| Single-user context | INV-M6A-19 | No auth, no session isolation, `confirmed_by` is optional label |
| Only DAY and WEEK duration units | INV-M6A-05 / INV-M6A-07 | MONTH, YEAR, BUSINESS_DAY, WORKING_DAY rejected |
| Evidence by reference, not copy | INV-M6A-DP-01 | No duplication of document text in confirmation records |
| No automatic legal rule application | INV-M6A-10 | All adjustments flags `false`; legal rule layer deferred |
| No "Frist" terminology in results | Usage rule | Term restricted to warnings and disclaimers only |

### Unknowns

**None.** All research questions (RQ-01 through RQ-10) have been answered in `research.md`. No technical unknowns remain for M6-A scope.

### Dependencies

| Dependency | Type | Version | Purpose |
|------------|------|---------|---------|
| `pydantic` | inherited | project | API request/response schemas |
| `pymupdf` | inherited | project | PDF text extraction (existing, not modified) |
| `structlog` | inherited | optional | Logging (confirmation filter extends existing) |

---

## Constitution Check

| # | Principle | Compliance | Verification |
|---|-----------|------------|--------------|
| 1 | **Local-only** | ✅ PASS | SQLite persistence, no external requests (INV-M6A-15) |
| 2 | **Privacy by Design** | ✅ PASS | Evidence by offset reference, no text duplication (INV-M6A-DP-01); logging filter redacts reference dates (INV-M6A-21) |
| 3 | **No automated legal decision** | ✅ PASS | Confirmation gate structurally prevents calculation without user action (INV-M6A-01, INV-M6A-02) |
| 4 | **Human Review** | ✅ PASS | `human_review_required=true` structurally enforced in every response (INV-M6A-11) |
| 5 | **Modular architecture** | ✅ PASS | Domain layer isolates dataclasses/enums; no framework dependency (ADR-002) |
| 6 | **Small vertical slices** | ✅ PASS | M6-A is one self-contained slice: API → Service → Domain → SQLite |
| 7 | **Red tests before implementation** | ✅ PASS | 64 test vectors defined in spec phase; tests precede build code |
| 8 | **Local gates as primary truth** | ✅ PASS | All testing against local SQLite; no remote dependencies |
| 9 | **No remote CI without approval** | ✅ PASS | CI workflows disabled per organizational policy |
| 10 | **Evidence before success claims** | ✅ PASS | All normative claims traceable to primary sources (see `research.md`) |
| 11 | **Documentation as living truth** | ✅ PASS | All artifacts (spec, data-model, API contract, plan, tasks) committed in spec run |
| 12 | **No production/PII test data** | ✅ PASS | Test data uses "SYNTHETISCH –" prefix per policy |

**Post-Design Re-Evaluation:** All 12 principles remain satisfied after Phase 1 design. No regressions introduced. The confirmation gate architecture particularly strengthens principles 3 and 4 compared to baseline.

---

## Architecture Decision

**Variant B: Confirmation Persistent, Calculation On-Demand** (see ADR-002)

- `ConfirmedReferenceEvent` stored in SQLite (new table `confirmed_reference_events`)
- `CalendarCalculationCandidate` computed on demand as pure function
- One new database table, CASCADE DELETE with documents

## Affected Layers

| Layer | Changes | Type |
|-------|---------|------|
| **Domain** | New entities: ReferenceEventCandidate, ConfirmedReferenceEvent, Duration, CalendarCalculationCandidate, CalculationStep + new enums | New files |
| **Application** | New ports: ReferenceEventRepository, CalendarArithmetic + new services | New files |
| **Infrastructure** | SQLite confirmation repository, DeterministicCalendarArithmetic, ReferenceEventDetector | New files |
| **API** | New routes for reference events and calculation preview, new schemas | New files |
| **Persistence** | New migration for confirmed_reference_events table | New migration |

## No Changes To

| Area | Rationale |
|------|-----------|
| M5 DeadlineCandidate | No modification — M6-A reads M5 output |
| M5 DeterministicDeadlineExtractor | No modification |
| Existing Case/Document domain | No modification |
| pyproject.toml | No new dependencies (stdlib only) |
| Existing API routes | No modification — new routes added |

## Dependency Graph

```
M5 DeadlineCandidate (RELATIVE_PERIOD)
    │
    ▼
ReferenceEventCandidate (detected from M5 + document text)
    │
    ▼ User confirms or manually enters
ConfirmedReferenceEvent (persisted)
    │
    ▼ Duration extracted from M5 candidate
CalendarArithmetic.calculate(reference_date, duration)
    │
    ▼
CalendarCalculationCandidate (non-binding preview)
```

## Implementation Order

1. **Domain layer** — New entities, enums, value objects
2. **Application ports** — Interfaces for repository and arithmetic
3. **Infrastructure** — SQLite repository, arithmetic implementation, reference event detector
4. **API layer** — Schemas, routes, dependency injection
5. **Database migration** — confirmed_reference_events table
6. **Tests** — Unit tests (domain), integration tests (repository), API tests

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| User treats preview as binding | Medium | HIGH | Mandatory warnings, terminology discipline |
| Confirmation gate bypassed in code | Low | HIGH | Structural enforcement via invariants and test gates |
| Date overflow | Low | Medium | Input validation (1900-2099 range) + post-calculation check |
| Log leakage of reference dates | Low | Medium | Logging filter spec, test vector TV-050 |
| SQLite audit trail tampering | Medium | Low | Documented limitation (INV-M6A-24) |

---

## Gates Evaluation

### Research Gate ✅ PASS
| Requirement | Status | Evidence |
|-------------|--------|----------|
| RQ-01–RQ-10 answered | ✅ PASS | `research.md` — all 10 research questions resolved |
| Primary sources documented | ✅ PASS | 5 official primary norm sources, 1 technical, 1 secondary = 8 documents |
| Source classification methodology | ✅ PASS | OFFICIAL_PRIMARY_NORM / OFFICIAL_GUIDANCE / SECONDARY_SOURCE / TECHNICAL_PRIMARY_DOCUMENTATION / INTERNAL_PRODUCT_POLICY |

### Security Gate ✅ PASS (AMBER resolved)
| Requirement | Status | Evidence |
|-------------|--------|----------|
| No automatic reference event selection | ✅ PASS | INV-M6A-01, INV-M6A-02; structural confirmation gate |
| No automatic legal rule application | ✅ PASS | INV-M6A-10; all adjustments flags `false` |
| No delivery/announcement fiction | ✅ PASS | INV-M6A-09; explicitly in "Bewusst nicht unterstützt" |
| No weekend/holiday adjustment | ✅ PASS | INV-M6A-08; `adjustments` always `false` |
| Input validation (date ranges, field lengths) | ✅ PASS | INV-M6A-20, INV-M6A-23; errors: FIELD_TOO_LONG, CALCULATED_DATE_OUT_OF_RANGE |
| Logging filter specified | ✅ PASS | INV-M6A-21, INV-M6A-DP-08; confirmed_date, evidence_text, evidence_note, source_text, document_id, confirmation_id redacted |
| Security Agent executed | ✅ PASS | T024; AMBER findings addressed with 11 spec updates |

### Compliance Gate ✅ PASS (GREEN)
| Requirement | Status | Evidence |
|-------------|--------|----------|
| Art. 22 DSGVO — No automated decision | ✅ PASS | Confirmation gate + human_review_required structural enforcement |
| Art. 5(1)(c) — Data minimization | ✅ PASS | Evidence via offset reference, no text duplication |
| Art. 5(1)(e) — Storage limitation | ✅ PASS | CASCADE DELETE on document deletion |
| Art. 15 — Right of access | ✅ PASS | History endpoint for confirmation audit trail |
| Art. 17 — Right to erasure | ✅ PASS | CASCADE DELETE + documented limitations |
| Art. 25 — Data protection by design | ✅ PASS | Local-only, no telemetry, privacy filters |
| Art. 6 — Legal basis documented | ✅ PASS | Context-dependent; no universal legal basis claimed |
| Compliance Agent executed | ✅ PASS | T025; GREEN verdict |

### Architecture Gate ✅ PASS (ARCH_GREEN)
| Requirement | Status | Evidence |
|-------------|--------|----------|
| M5/M6-A clean separation | ✅ PASS | M5 domain unchanged; M6-A consumes M5 output |
| Unconfirmed/Confirmed separation | ✅ PASS | Distinct entity classes with state machine |
| Confirmation state machine | ✅ PASS | 5 states (UNCONFIRMED, CONFIRMED, REJECTED, REVOKED, SUPERSEDED) |
| Pure CalendarArithmetic component | ✅ PASS | No side effects, no external dependencies, stdlib only |
| Days/Weeks only | ✅ PASS | INV-M6A-05, INV-M6A-07; unsupported units rejected |
| No framework dependency in domain | ✅ PASS | Dataclasses + enums; no FastAPI/pydantic in domain layer |
| Persistence decision (Variant B) | ✅ PASS | ADR-002 with rationale |
| API contract consistency | ✅ PASS | 4 endpoints with full req/res schemas |
| Architecture Agent executed | ✅ PASS | T021; ARCH_GREEN verdict |

---

## Dependencies Out of Scope

- No `python-dateutil` (no month arithmetic)
- No `holidays` library (no Feiertagsregeln)
- No `workalendar` (no business day support)
- No locale module (hardcoded German month names from M5)
