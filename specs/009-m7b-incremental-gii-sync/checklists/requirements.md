# Requirements Checklist — M7-B

## Specification Completeness

| # | Item | Status |
|---|------|--------|
| 1 | Research questions answered (RQ-01–RQ-08) | PASS |
| 2 | External primary sources verified (actual HTTP HEAD/GET to GII) | PASS |
| 3 | Catalog structure and metadata documented | PASS |
| 4 | User Stories with acceptance criteria (7) | PASS |
| 5 | Functional Requirements (20) | PASS |
| 6 | Product Invariants (18) | PASS |
| 7 | Data Integrity Invariants (10) | PASS |
| 8 | Data model complete (SyncRun, SyncItem + enums) | PASS |
| 9 | State machine defined (SyncItem, SyncRun) | PASS |
| 10 | CLI contract complete (3 subcommands) | PASS |
| 11 | Sync plan format defined | PASS |
| 12 | Sync result format defined | PASS |
| 13 | Status codes and enums defined | PASS |
| 14 | Security boundaries documented | PASS |
| 15 | Implementation plan with phases | PASS |
| 16 | Tasks broken down (13 phases) | PASS |
| 17 | Quickstart guide with validation scenarios | PASS |
| 18 | ADR-009 created | PENDING |

## Security Gates

| # | Item | Status |
|---|------|--------|
| 1 | No case data during sync (ADR-007 Decision 7) | PASS |
| 2 | HTTPS-only for all external downloads | PASS (inherited) |
| 3 | Host allowlist enforced | PASS (inherited) |
| 4 | No background sync | PASS |
| 5 | Dry-run as default (no accidental changes) | PASS |
| 6 | Per-item error isolation | PASS |
| 7 | Error summary length limits (500 chars) | PASS |
| 8 | Path traversal protection via instrument key validation | PASS |
| 9 | Safe logging (no personal data in sync logs) | PASS |
| 10 | Append-only sync history (no deletion without CASCADE) | PASS |

## Compliance Gates

| # | Item | Status |
|---|------|--------|
| 1 | Sync isolation from case data (Art. 5(1)(c) data minimization) | PASS |
| 2 | Sync history retention (Art. 5(1)(e) storage limitation) | PASS |
| 3 | No personal data in sync tables | PASS |
| 4 | No automated decisions during sync | PASS |
| 5 | User-initiated sync only (no background processing) | PASS |

## Architecture Gates

| # | Item | Status |
|---|------|--------|
| 1 | M7-A pipeline reused (download → hash → snapshot → parse → persist) | PASS |
| 2 | M7-A domain entities unchanged | PASS |
| 3 | SourceClient backward-compatible | PASS |
| 4 | GiiAdapter enhanced, not replaced | PASS |
| 5 | SHA-256 as integrity anchor | PASS |
| 6 | catalog_stand_date as freshness gate | PASS |
| 7 | Append-only sync history | PASS |
| 8 | CLI as primary interface | PASS |
| 9 | Phase 1 / Phase 2 separation clean | PASS |

## Build Readiness

| # | Item | Status |
|---|------|--------|
| 1 | No product code changed | PASS (verified) |
| 2 | No src/ changes | PASS |
| 3 | No test/ changes | PASS |
| 4 | No pyproject.toml changes | PASS |
| 5 | No database schema changes (spec only) | PASS |

## Blockers

- None.
