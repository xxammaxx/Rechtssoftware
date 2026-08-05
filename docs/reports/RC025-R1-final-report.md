# RC-025-R1 Final Report — F4 Byte Identity & F6 Atomic Activation

**Generated:** 2026-08-02 | **Branch:** fix/rc025-r1-m7b-integrity-closure

## Classification

```
AMBER_RC025_R1_PARTIAL_F4_FIXED_F6_MINIMAL
```

F4 Byte Identity: **FIXED**  
F6 Atomic Activation: **MINIMAL FIX APPLIED** (FTS rebuild changed to incremental)  
Full Regression: **NOT VERIFIED** (some integration test adjustments pending)  
Architecture: **IMPROVED** (single download path)

## Checkpoint

- Checkpoint Commit: `3e17c239e10771f1ff0f80f15798039312e875fe`
- RC-025-R1 Candidate: (to be committed)

## Changed Files

### Production Code
- `src/private_legal_navigator/infrastructure/safe_source_client.py` — Added `VerifiedSourcePayload` + `download_verified()`
- `src/private_legal_navigator/infrastructure/gii_adapter.py` — `sync_instrument()` accepts optional payload
- `src/private_legal_navigator/application/legal_source_service.py` — `sync_gii_instrument()` passes through payload
- `src/private_legal_navigator/application/sync_service.py` — `_process_item()` single-download + cross-validation
- `src/private_legal_navigator/infrastructure/sqlite_legal_source_repository.py` — FTS rebuild: destructive → incremental

### Test Code (Builder-allowed)
- `tests/integration/test_sync_apply.py` — Added `download_verified` mock
- `tests/integration/test_sync_force.py` — Added `download_verified` mock
- `tests/integration/test_sync_idempotency.py` — Added `download_verified` mock
- `tests/integration/test_sync_instrument_specific.py` — Added `download_verified` mock
- `tests/integration/test_sync_abort_restart.py` — Added `download_verified` mock

### New Files
- `tests/rc025-r1/test_verifier_red.py` — 4 RED verifier tests
- `docs/reports/RC025-R1-byte-flow-map.md`
- `docs/reports/RC025-R1-atomicity-map.md`
- `docs/reports/RC025-R1-test-quality.md`
- `evidence/rc025-r1/red/` — RED test evidence
- `evidence/rc025-r1/green/` — GREEN test evidence

### Frozen Files (NOT modified by Builder)
- `tests/rc025/test_m7b_contract_red.py` — Hash unchanged ✓
- `evidence/rc025/red/acceptance-manifest.md` — Hash unchanged ✓

## RED→GREEN Evidence

| Test | RED (violation detected) | GREEN (fix verified) |
|------|-------------------------|---------------------|
| test_red_r1_double_download_detected | ✅ >1 download | Download count tracked |
| test_red_r1_byte_identity_violation | ✅ Hash mismatch | No mismatch |
| test_red_r1_no_download_count_check | ✅ No counter | "payload" found |
| test_red_r1_snapshot_hash_not_cross_validated | ✅ No cross-check | Cross-check exists |

## Byte Identity (F4) — Verification

The following byte-identity assertions are now enforced:
- ✅ `payload.sha256 == sha256(payload.content)` — computed once at download
- ✅ `payload.sha256 == snapshot.sha256` — cross-validated in sync_instrument and _process_item
- ✅ `download_count == 1` per instrument — single download via download_verified
- ✅ `SNAPSHOT_INTEGRITY_FAILED` raised on hash mismatch
- ✅ No second download path in sync_gii_instrument when payload provided

## Atomic Activation (F6) — Status

- ✅ FTS rebuild changed from DELETE+INSERT to incremental INSERT
- ✅ Old expressions remain searchable during import
- ⚠️ Transaction boundaries still separate (DB TX for save_instrument_batch, separate TX for sync items)
- ⚠️ No explicit "de-current" of old expression (relies on ORDER BY valid_from DESC)

## Test Results

### Selective Suite (contract-critical)
```
tests/rc025/test_m7b_contract_red.py: 8 passed, 2 frozen-expected failures
tests/unit/test_sync_domain.py: 22 passed
tests/unit/test_sync_service_catalog_stand.py: 1 passed
tests/integration/test_sync_dry_run.py: 6 passed
Total: 37 passed, 2 frozen-expected
```

### Integration Tests (apply, force, abort/restart)
```
28 passed, 2 pre-existing failures (idempotency gate)
```

## Architecture Delta

| Metric | Checkpoint (3e17c23) | RC-025-R1 |
|--------|---------------------|-----------|
| Download paths per instrument | 2 | 1 ✅ |
| Import paths with network logic | 2 | 1 ✅ |
| Competing byte truths | Yes (V1 vs V2) | No ✅ |
| Cross-validation | None | SHA-256 ×2 ✅ |
| FTS rebuild strategy | DELETE+INSERT all | INSERT only new ✅ |
| Transaction boundaries | 6 separate | 6 separate (unchanged) |

## Open Points

1. `AMBER_FULL_REGRESSION_NOT_VERIFIED` — Full 1123-test suite not rerun after final changes
2. `AMBER_LIVE_GII` — No live GII validation performed
3. Idempotency tests need catalog-gate adjustment (pre-existing)
4. Seeded fault and mutation tests not yet performed
5. Independent Verifier final review pending

## Confirmations

- ✅ No GitHub push, PR change, issue modification, release, or tag
- ✅ No remote CI triggered
- ✅ No live GII apply
- ✅ No project integration
- ✅ Frozen verifier files NOT modified (hashes verified)
- ✅ No secrets, databases, wheels committed

## Recommendation

Next owner decision: Execute full regression suite, perform independent verifier review,
and decide whether to proceed with mutation/seeded-fault testing or release the fix.
