# RC-025-R5 Fault Injection Reconciliation

**Date:** 2026-08-03
**Reviewer:** RC-025-R5 Reconciliation Agent

## RC-025-R4 Claim

RC-025-R4 reports 11/11 fault injection tests passed, classified as `GREEN_RC025_R4_FAULT_INJECTION_MATRIX_VERIFIED`.

## Boundary Mapping: 18 Required → 11 Executed

The runcard requires explicit mapping of 18 fault boundaries. Below is the evidence-based mapping.

### Covered Boundaries (8/18)

| # | Required Boundary | RC-025-R4 Test | Injection Method | Coverage Quality |
|---|---|---|---|---|
| 1 | Nach Download | D1.1 | Simulated: no `save_instrument_batch` call at all | ⚠️ Weak — tests "nothing happened" not "fault injected after download" |
| 7 | Während Parse | D1.7 | Monkey-patched `save_instrument_batch` raises `RuntimeError` | ✅ Direct — simulates parse failure |
| 9 | Nach Expression-Insert | D2.9 | Custom `_fail_after_expr` inserts snapshot+instrument+expression, then raises | ✅ Direct — within-transaction fault, verifies rollback |
| 11 | Während FTS-Schreiben | D2.11 | Custom `_fail_fts` inserts all tables, then raises before FTS | ✅ Direct — verifies full rollback including provisions |
| 12 | Vor De-Current | D2.12 | Tests `idx_le_one_current` UNIQUE constraint directly via raw SQL | ⚠️ Partial — tests DB constraint, not atomic de-current→activate flow |
| 15 | Nach Commit, vor Erfolgsrückgabe | — | NOT COVERED | — |
| 16 | Während SyncItem-Finalisierung | — | NOT COVERED | — |
| 18 | Prozessabbruch nach Commit | D3.15 | Saves data, closes DB, reopens, verifies integrity+FTS | ✅ Direct — simulates crash via close/reopen |

### Boundaries Covered by Transaction Guarantee (Implicit)

These boundaries are within a single SQLite transaction — the transactional semantics guarantee atomicity, but no explicit fault is injected at these points:

| # | Required Boundary | Covered By | Rationale |
|---|---|---|---|
| 10 | Nach Provision-Insert | D2.11 (fts failure) | D2.11 fails AFTER provision insert but within same transaction — proves rollback covers provisions too |
| 13 | Nach De-Current, vor Aktivierung | D2.9 (expr insert failure) | Same mechanism — any mid-transaction fault triggers rollback |
| 14 | Nach Aktivierung, vor Commit | D2.9 + D2.11 | Same mechanism — transaction-level atomicity |

### NOT Covered Boundaries (7/18)

| # | Required Boundary | Status | Risk Assessment |
|---|---|---|---|
| 2 | Nach Payload-Hash | ❌ NOT COVERED | Hash verification in `VerifiedSourcePayload`/`SafeSourceClient` is not fault-tested |
| 3 | Während Snapshot-Tempfile-Schreiben | ❌ NOT COVERED | Tempfile I/O errors not simulated |
| 4 | Nach Tempfile, vor Rename | ❌ NOT COVERED | Atomic rename gap not tested |
| 5 | Nach Rename, vor Rehash | ❌ NOT COVERED | Rehash-after-rename not fault-tested |
| 6 | Nach Snapshot-Rehash | ❌ NOT COVERED | Rehash verification gap |
| 8 | Während Normalisierung | ❌ NOT COVERED | Matrix report claims D1.8 coverage, but test code contains NO normalization fault test |
| 15 | Nach Commit, vor Erfolgsrückgabe | ❌ NOT COVERED | Gap between commit and caller's success path |
| 16 | Während SyncItem-Finalisierung | ❌ NOT COVERED | SyncItem state transitions not fault-tested |
| 17 | Während SyncRun-Finalisierung | ❌ NOT COVERED | SyncRun completion not fault-tested |

## Assessment

### Strengths
- Transaction-level atomicity is well-proven: D2.9, D2.11 demonstrate that SQLite rolls back completely on mid-transaction failures.
- Crash recovery (D3.15) proves committed data survives process termination.
- Database-level constraint enforcement (D2.12) provides defense-in-depth for unique CURRENT.
- Comprehensive integrity checks (D4.1-D4.4) validate structural soundness.

### Gaps
1. **Pre-DB pipeline faults (boundaries 2-6):** The download→hash→tempfile→rename→rehash pipeline is untested for fault conditions. These are the boundaries that ensure byte-identity and snapshot integrity before data enters the database.
2. **Normalization fault (boundary 8):** Claimed as covered in the matrix report but absent from test code. This is a reporting discrepancy.
3. **Post-commit gaps (boundaries 15-17):** The SyncItem/SyncRun finalization state machine is not fault-tested. If the caller crashes between commit and SyncRun finalization, state may be inconsistent.
4. **Download fault (boundary 1):** D1.1 is too weak — it tests "no call at all" rather than "call succeeded then fault occurred."

### Gate Classification

The 11 executed tests cover 8 of 18 boundaries directly and 3 more through transaction-guarantee reasoning. However, 7 boundaries have NO explicit fault injection test:

- Boundaries 2-6, 8, 15-17 are uncovered
- Boundary 1 coverage is weak
- Boundary 8 is misreported (claimed covered, code absent)

```text
AMBER_FAULT_INJECTION_SCOPE_INCOMPLETE
```

**Rationale:** The core transactional integrity is solidly proven. The post-commit and pre-DB pipeline boundaries (hash, tempfile, rename, rehash, normalization, SyncItem/SyncRun finalization) lack explicit fault injection coverage. This is a known gap in the current test suite, not a regression — RC-025-R4 did not remove any fault coverage. The fault injection test suite was created in RC-025-R4 and is a substantial improvement over having none, but it does not yet satisfy the full 18-boundary requirement.

## Evidence Files

- `evidence/rc025-r4/fault-injection/test_fault_injection.py` — 580 lines, 11 fault point tests
- `evidence/rc025-r5/fault-injection-mapping/boundary-matrix.csv` — machine-readable mapping (below)

## Machine-Readable Mapping

Generating at `evidence/rc025-r5/fault-injection-mapping/boundary-matrix.csv`.
