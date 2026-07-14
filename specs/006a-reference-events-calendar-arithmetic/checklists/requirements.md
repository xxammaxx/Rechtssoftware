# Requirements Checklist — M6-A

## Specification Completeness

| # | Item | Status |
|---|------|--------|
| 1 | Research questions answered (RQ-01–RQ-10) | PASS |
| 2 | Primary sources documented (20+ sources) | PASS |
| 3 | Legal and mathematical layers separated | PASS |
| 4 | User Stories with acceptance criteria (6) | PASS |
| 5 | Functional Requirements (30) | PASS |
| 6 | Success Criteria (13) | PASS |
| 7 | Product Invariants (24) | PASS |
| 8 | Data model complete | PASS |
| 9 | API contract complete (4 endpoints) | PASS |
| 10 | Warning codes defined (20) | PASS |
| 11 | Test vectors defined (64) | PASS |
| 12 | ADR-002 created | PASS |
| 13 | Architecture diagram present | PASS |
| 14 | Plan document present | PASS |
| 15 | Tasks broken down | PASS |
| 16 | Clarify decisions documented | PASS |

## Security Gates

| # | Item | Status |
|---|------|--------|
| 1 | No automatic reference event selection | PASS |
| 2 | No automatic legal rule application | PASS |
| 3 | No delivery/announcement fiction | PASS |
| 4 | No weekend/holiday adjustment | PASS |
| 5 | Input validation (date ranges, field lengths) | PASS |
| 6 | Logging filter specified | PASS |
| 7 | No external requests | PASS |
| 8 | Single-user scope documented | PASS |
| 9 | Audit trail limitations documented | PASS |
| 10 | Security Agent executed | PASS (AMBER resolved) |

## Compliance Gates

| # | Item | Status |
|---|------|--------|
| 1 | Art. 22 DSGVO — No automated legal decision | PASS |
| 2 | Art. 5(1)(c) — Data minimization | PASS |
| 3 | Art. 5(1)(e) — Storage limitation (CASCADE DELETE) | PASS |
| 4 | Art. 15 — Right of access (history endpoint) | PASS |
| 5 | Art. 17 — Right to erasure (CASCADE DELETE) | PASS |
| 6 | Art. 25 — Data protection by design (local-only) | PASS |
| 7 | Art. 6 — Legal basis documented | PASS |
| 8 | Mandatory user confirmation gate | PASS |
| 9 | Mandatory human review flag | PASS |
| 10 | Terminology discipline (no "Frist" claims) | PASS |
| 11 | No automatic communication | PASS |
| 12 | Compliance Agent executed | PASS (GREEN) |

## Architecture Gates

| # | Item | Status |
|---|------|--------|
| 1 | M5/M6-A clean separation | PASS |
| 2 | Unconfirmed/Confirmed separation | PASS |
| 3 | Confirmation state machine | PASS |
| 4 | Pure CalendarArithmetic component | PASS |
| 5 | Days/Weeks only | PASS |
| 6 | No month/year | PASS |
| 7 | No framework dependency in domain | PASS |
| 8 | Traceable calculation path | PASS |
| 9 | Persistence decision (Variant B) | PASS |
| 10 | API contract consistency | PASS |
| 11 | Idempotency | PASS |
| 12 | Testability | PASS |
| 13 | Architecture Agent executed | PASS (ARCH_GREEN) |

## Build Readiness

| # | Item | Status |
|---|------|--------|
| 1 | No product code changed | PASS (verified) |
| 2 | No src/ changes | PASS |
| 3 | No test/ changes | PASS |
| 4 | No pyproject.toml changes | PASS |
| 5 | No database schema changes | PASS (spec only) |
| 6 | Baseline tests still green | WAITING (T030) |
| 7 | Spec branch pushed | WAITING (T032) |
| 8 | Draft PR created | WAITING (T033) |

## Blockers

- None.
