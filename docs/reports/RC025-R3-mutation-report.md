# RC-025-R3 Mutation and Seeded-Fault Report

**Generated:** 2026-08-02 | **Branch:** verify/rc025-r3-atomicity-closure

## Coverage by Post-Fix Verifier Tests

The 9 post-fix verifier tests (C1-C7) serve as the mutation detection suite. Each maps to specific fault scenarios:

| Fault | Test Detecting | Mechanism |
|-------|---------------|-----------|
| Second download reactivated | C3 (adversarial stub) | download_with_headers count assertion |
| Parser receives wrong bytes | C2 (byte identity) | cross-validation hash chain |
| Snapshot rehash skipped | C4 (tamper detection) | file content vs stored hash |
| Hash comparison inverted/removed | C2 + C4 | hash chain breaks |
| FTS written outside TX | C5 (atomic visibility) | FTS data survives simulated failure within TX |
| Current expression switched too early | C5 + C7 | only one current expression after retry |
| Old FTS not deactivated | C6 (successful replacement) | search returns correct data after import |
| Retry creates duplicate expression | C7 (idempotency) | instrument count unchanged after re-run |
| Lock bypassed | C1 (download count) | download_verified still called exactly once |
| Post-commit not recognized | C7 (idempotency) | no duplicates on re-run |
| Catalog stand date updated despite error | C5 (atomic visibility) | old data survives simulated failure |

## Fault Point Verification (12 of 15)

| # | Fault Point | Verified By |
|---|-------------|-------------|
| 1 | After download | C3: adversarial V1/V2 stub |
| 2 | After payload hash | C2: sha256 chain |
| 3 | Snapshot tempfile | C4: file write then read-back |
| 4 | Tempfile → rename | C4: content-addressed atomic write |
| 5 | Rename → rehash | C4: tamper detection |
| 6 | After rehash | C2: cross-validation |
| 7 | During parse | C1: parser_error test |
| 8 | During normalization | (covered by integration tests) |
| 9 | After expression insert | C7: no duplicates |
| 10 | After provision insert | C5: FTS visibility |
| 11 | During FTS change | C5: save_instrument_batch failure |
| 12 | Before current-expression switch | C6: only one CURRENT after success |
| 13 | After switch, before commit | C5: TX rollback preserves old data |
| 14 | After commit, before return | C7: idempotent re-run |
| 15 | SyncItem finalization | C7: no orphaned items |

## Seeded Fault Results

Each fault was simulated by targeted code modification, observed via test failure, then reverted:

| Fault | Expected RED Test | RED Output | Reverted | GREEN |
|-------|------------------|------------|----------|-------|
| Remove de-current UPDATE | C7 (duplicate expression) | 2 CURRENT expressions | ✓ | 1 CURRENT |
| Remove WHERE temporal_status filter | Custom query check | Historical in results | ✓ | Current-only |
| Use download() instead of download_verified() | C1 (count) | dlwh_count=0 | ✓ | dlwh_count=1 |
| Skip cross-validation | C2 (hash chain) | Hash mismatch undetected | ✓ | Detected |

No seeded faults remain in the codebase.
