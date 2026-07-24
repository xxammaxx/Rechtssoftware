# Test Strategy and Coverage Requirements — M7-B

## Overview

M7-B introduces new domain entities, services, CLI entry points, and database tables. This checklist defines the test strategy, coverage requirements, and specific test scenarios.

---

## Coverage Requirements

| Module | Minimum Coverage | Notes |
|--------|-----------------|-------|
| Domain (SyncRun, SyncItem, SyncPlan) | 95% | Pure logic, no I/O |
| Application (SyncPlanningService) | 90% | Mocked repository + adapter |
| Application (SyncExecutionService) | 90% | Mocked adapter + repository |
| Infrastructure (SqliteSyncRunRepository) | 90% | Temp SQLite database |
| Infrastructure (SourceClient enhancement) | 95% | Existing tests + new header capture tests |
| Infrastructure (GiiAdapter enhancement) | 90% | Mocked client |
| CLI (sync commands) | 85% | Mocked services |
| **Overall project** | **75% (no decrease)** | Existing baseline must not drop |

---

## Test Pyramid

```
         ╱╲
        ╱ E2E ╲           (3-5 tests — real GII in TEST mode)
       ╱────────╲
      ╱Integration╲       (10-15 tests — temp DB, mocked network)
     ╱──────────────╲
    ╱   Unit Tests    ╲   (30-40 tests — pure logic + mocked ports)
   ╱────────────────────╲
```

---

## Domain Unit Tests

### SyncRun Tests
| # | Test | Expected |
|---|------|----------|
| UT-01 | SyncRun with valid data | Fields set correctly |
| UT-02 | SyncRun without run_id | UUID auto-generated |
| UT-03 | SyncRun with empty source_key | ValueError |
| UT-04 | SyncRun.item_counts returns correct dict | All counters present |
| UT-05 | SyncRun.duration_seconds for completed run | Positive float |
| UT-06 | SyncRun.duration_seconds for running run | None |
| UT-07 | SyncRun counter invariant: all counts sum to total | Assertion passes |
| UT-08 | SyncRun dry_run flag | Default True |

### SyncItem Tests
| # | Test | Expected |
|---|------|----------|
| UT-10 | SyncItem with valid data | Fields set correctly |
| UT-11 | SyncItem without item_id | UUID auto-generated |
| UT-12 | SyncItem with empty source_identifier | ValueError |
| UT-13 | SyncItem with http_status < 0 | ValueError |
| UT-14 | SyncItem with byte_size < 0 | ValueError |
| UT-15 | SyncItem status transitions valid | No error |
| UT-16 | SyncItem NEW has no previous_sha256 | Empty string |
| UT-17 | SyncItem UNCHANGED has no new_sha256 | Empty string |

### SyncPlan Tests
| # | Test | Expected |
|---|------|----------|
| UT-20 | SyncPlan summary counts correct | Match classified items |
| UT-21 | SyncPlan with empty items list | total=0, all counts 0 |
| UT-22 | SyncPlan.is_fresh flag | True when catalog newer |

---

## Application Service Tests (Mocked)

### SyncPlanningService
| # | Test | Expected |
|---|------|----------|
| AS-01 | Plan: catalog fetch succeeds, items classified | SyncPlan returned with all items |
| AS-02 | Plan: catalog fetch fails | FatalError raised |
| AS-03 | Plan: no previous sync (first run) | All items = NEW |
| AS-04 | Plan: catalog_stand_date matches | Items compared by SHA-256 |
| AS-05 | Plan: catalog_stand_date differs | Full re-classification |
| AS-06 | Plan: instrument filter | Only requested item in plan |
| AS-07 | Plan: force mode | Stand-date gate bypassed |
| AS-08 | Plan: SHA-256 comparison detects change | Item classified as CHANGED |
| AS-09 | Plan: remote_missing detection | Item classified as REMOTE_MISSING |
| AS-10 | Plan: 6100 items (large catalog) | Processed within 5 seconds |

### SyncExecutionService
| # | Test | Expected |
|---|------|----------|
| AS-20 | Execute: only NEW/CHANGED items downloaded | UNCHANGED/SKIPPED skipped |
| AS-21 | Execute: download succeeds, snapshot saved | Snapshot in DB, SyncItem updated |
| AS-22 | Execute: download fails (network) | Item → FAILED, error_summary set |
| AS-23 | Execute: import fails (XML parse) | Item → FAILED, snapshot preserved |
| AS-24 | Execute: SHA-256 dedup prevents re-download | Existing snapshot reused |
| AS-25 | Execute: SyncRun persisted with correct status | Run status = COMPLETED |
| AS-26 | Execute: partial failure (some items fail) | Run status = FAILED, failed_count > 0 |
| AS-27 | Execute: dry-run with --apply flag error | Error: --dry-run and --apply mutually exclusive |
| AS-28 | Execute: summary report generated | Includes all counters and timing |

---

## Repository Tests (SQLite)

| # | Test | Expected |
|---|------|----------|
| RT-01 | Create sync_run | Row inserted, all fields match |
| RT-02 | Update sync_run status | Row updated |
| RT-03 | Get sync_run by ID | Correct run returned |
| RT-04 | Get last sync_run for source | Most recent run by started_at |
| RT-05 | List sync_runs with limit | Correct number returned, ordered by started_at DESC |
| RT-06 | Save sync_items in bulk | All items inserted with correct run_id |
| RT-07 | Get items for run | All items returned |
| RT-08 | CASCADE DELETE on run delete | Items deleted |
| RT-09 | SET NULL on snapshot delete | snapshot_id becomes NULL |
| RT-10 | Last catalog stand date read/write | Correct value stored and retrieved |

---

## CLI Tests

| # | Test | Expected |
|---|------|----------|
| CL-01 | `pln sync gii --help` | Shows help with all flags |
| CL-02 | `pln sync gii` (no flags) | Dry-run mode activated |
| CL-03 | `pln sync gii --dry-run` | Dry-run plan output |
| CL-04 | `pln sync gii --apply` | Apply execution (mocked) |
| CL-05 | `pln sync gii --apply --dry-run` | Error: mutually exclusive |
| CL-06 | `pln sync gii --instrument BGB` | Only BGB in plan |
| CL-07 | `pln sync gii --instrument "invalid/path"` | Error: invalid key |
| CL-08 | `pln sync gii --catalog-only` | Catalog info output |
| CL-09 | `pln sync gii --force` | Force mode warning displayed |
| CL-10 | `pln sync status` | Sync history displayed |
| CL-11 | `pln sync status --last 5` | 5 runs displayed |
| CL-12 | `pln sync status --source invalid` | Error: source not found |
| CL-13 | `pln sync verify` | Integrity check results |
| CL-14 | `pln sync verify --source gesetze-im-internet` | Source-specific check |
| CL-15 | Exit code 0 on success | Exit code matches |
| CL-16 | Exit code 2 on fatal error | Exit code matches |

---

## Integration Tests

| # | Test | Expected |
|---|------|----------|
| IT-01 | Full dry-run: plan created without side effects | No snapshots, no DB changes |
| IT-02 | Full apply: instruments downloaded and imported | Snapshots in DB, provisions indexed |
| IT-03 | Idempotent re-run: second apply produces no changes | All items UNCHANGED |
| IT-04 | Abort + restart: partial download recovered | Dedup prevents re-download |
| IT-05 | Instrument-specific sync | Only specified instrument processed |
| IT-06 | Catalog-only mode | No items classified |
| IT-07 | Force mode | Catalog stand-date gate bypassed |
| IT-08 | No internet scenario | Graceful error, no crash |
| IT-09 | Concurrent sync blocked | Second returns CONFLICT |

---

## E2E Tests

| # | Test | Expected |
|---|------|----------|
| E2E-01 | Dry-run against real GII (TEST mode) | Catalog fetched, plan displayed |
| E2E-02 | Apply single instrument from real GII | Instrument downloaded and imported |
| E2E-03 | Verify sync history after apply | History shows completed run |
| E2E-04 | Verify snapshot integrity after sync | All hashes match |

---

## Regression Tests

| # | Test | Expected |
|---|------|----------|
| RG-01 | Baseline tests pass after M7-B changes | All pre-existing tests pass |
| RG-02 | FTS5 search still works | Search returns same results |
| RG-03 | Citation resolution still works | Resolution unchanged |
| RG-04 | Case operations unchanged | CRUD on cases still works |
| RG-05 | Document operations unchanged | Upload/download still works |
| RG-06 | M6-A reference events unchanged | Confirmation workflow unchanged |

---

## Static Analysis

```bash
ruff check src tests         # 0 errors
mypy src                     # 0 errors
pip check                    # All dependencies satisfied
```

---

## Performance Requirements

| Scenario | Limit | Test |
|----------|-------|------|
| Catalog comparison (6,120 items) | < 5 seconds | IT-03 |
| Sync planning (no downloads) | < 10 seconds | IT-01 |
| Single instrument sync (20 MB file) | < 30 seconds | E2E-02 |
| CLI help display | < 1 second | CL-01 |
| Sync status display (last 10 runs) | < 2 seconds | CL-10 |

---

## Edge Cases

| # | Scenario | Expected |
|---|----------|----------|
| EC-01 | Empty catalog (0 items) | Plan: total=0 |
| EC-02 | Catalog with 10,000+ items | Processed within limits |
| EC-03 | SHA-256 mismatch on verified snapshot | Verify detects and reports |
| EC-04 | Instrument deleted from GII between runs | REMOTE_MISSING |
| EC-05 | All items REMOTE_MISSING (source deprecated) | Warning displayed |
| EC-06 | Source not registered | Auto-register on first sync |
| EC-07 | Database locked during sync | Error with retry suggestion |
| EC-08 | Invalid UTF-8 in catalog XML | Parse error → FAILED with error_summary |
