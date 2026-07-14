# Plan — M6-A Reference Events and Calendar Arithmetic

## Overview

This plan maps the specification to an implementation strategy. No implementation occurs in this run — this is a specification artifact for the future build.

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

## Dependencies Out of Scope

- No `python-dateutil` (no month arithmetic)
- No `holidays` library (no Feiertagsregeln)
- No `workalendar` (no business day support)
- No locale module (hardcoded German month names from M5)
