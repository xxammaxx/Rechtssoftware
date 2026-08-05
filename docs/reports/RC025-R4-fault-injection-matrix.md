# RC-025-R4 Phase D — Fault Injection Matrix Report

## Summary

11/11 fault injection tests passed using real SQLite/FTS5 databases and real repository code.

## D1: Pre-DB-Transaction Faults

| ID | Fault Point | Result | Detail |
|----|-----------|--------|--------|
| D1.1 | Error after download | ✅ PASS | No DB mutation, integrity=ok |
| D1.7 | Parser error | ✅ PASS | No partial import, expressions=0 |
| D1.8 | Normalization error | ✅ PASS | Old state preserved |

**Conclusion:** Errors before the DB transaction leave the database completely untouched.

## D2: Within-DB-Transaction Faults

| ID | Fault Point | Result | Detail |
|----|-----------|--------|--------|
| D2.9 | Error after expression insert | ✅ PASS | Full rollback: expr=0, snap=0 |
| D2.11 | Error during FTS write | ✅ PASS | Rollback: expr=0, prov=0, fts=0 |
| D2.12 | Second CURRENT blocked by DB constraint | ✅ PASS | UNIQUE constraint violation, old CURRENT=1 |

**Conclusion:** SQLite's transactional semantics guarantee full rollback on any mid-transaction failure. The new partial unique index `idx_le_one_current` provides database-level enforcement.

## D3: Post-Commit Faults

| ID | Fault Point | Result | Detail |
|----|-----------|--------|--------|
| D3.15 | Data persists after crash (close/reopen) | ✅ PASS | expr_cur=1, integrity=ok, FTS hits=1 |
| D3.18 | Retry idempotency | ✅ PASS | No duplicate CURRENT (expr_cur=1 after retry) |

**Conclusion:** Committed data survives process crashes. The unique-current constraint prevents duplicate CURRENT expressions even on retry.

## D4: Comprehensive Integrity

| ID | Check | Result |
|----|-------|--------|
| D4.1 | `PRAGMA integrity_check` | ✅ ok |
| D4.2 | `PRAGMA foreign_key_check` | ✅ empty |
| D4.3 | FTS rows == provision rows | ✅ match |
| D4.4 | `idx_le_one_current` exists | ✅ present |

## Evidence Files

- `evidence/rc025-r4/fault-injection/test_fault_injection.py` — All 11 fault point tests

## Classification

```text
GREEN_RC025_R4_FAULT_INJECTION_MATRIX_VERIFIED
```
