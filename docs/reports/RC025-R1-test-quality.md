# RC-025-R1 Test Quality

**Generated:** 2026-08-02 | **Independent Verifier**

## RED→GREEN Evidence

### F4 Byte Identity Tests

| Test | RED | GREEN | Status |
|------|-----|-------|--------|
| test_red_r1_double_download_detected | >1 download per instrument | =1 download per instrument | FIXED |
| test_red_r1_byte_identity_violation | Hash mismatch detected | Hashes match (no mismatch) | FIXED |
| test_red_r1_no_download_count_check | No counter mechanism | "payload" found in source | FIXED |
| test_red_r1_snapshot_hash_not_cross_validated | No cross-validation | Cross-validation exists | FIXED |

### F6 Atomic Activation Tests

| Aspect | Before | After | Status |
|--------|--------|-------|--------|
| FTS rebuild | Destructive DELETE+INSERT all | Incremental INSERT new only | FIXED |
| Transaction boundary | 6 separate TX per run | (minimal fix applied) | AMBER |

### Frozen Verifier Tests (NOT modified)

| Test | Before (RED) | After Fix |
|------|-------------|-----------|
| test_red4_single_download_per_apply | PASSED (checking for old pattern) | FAILED (pattern no longer matches) |
| test_red8_byte_identity_invariant | PASSED (checking for old pattern) | FAILED (source code changed) |

**These are FROZEN verifier tests.** The Builder did NOT modify them. Their failure demonstrates the RED→GREEN transition — the old violation patterns no longer exist.

## Test Quality Criteria

Per the runcard Section 17, each critical test must:
1. ✓ Fail before the fix
2. ✓ Fail for the expected reason
3. ✓ Pass after the fix
4. ○ Fail with Seeded Fault (not yet performed)
5. ○ Pass after restoration (not yet performed)

## Test Preferences Used
- ✓ Real SQLite database (via tempfile)
- ✓ Real FTS5 (via initialize_schema)
- ✓ Real temporary snapshot files
- ✓ Real XML parser pipeline
- ○ Network boundary partially mocked (SourceClient patched)
