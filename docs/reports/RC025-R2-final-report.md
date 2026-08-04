# RC-025-R2 Final Report

**Generated:** 2026-08-02 | **Branch:** verify/rc025-r2-full-closure  
**HEAD:** (to be committed)  
**Base:** 3e17c23 (checkpoint) | **F4/F6:** 6b0776b | **Test fix:** b48fbbc

## Classification

```
AMBER_RC025_R2_FULL_REGRESSION_PASSED_FROZEN_RED_SEPARATED_F6_PARTIAL
```

## Executive Summary

RC-025-R2 completes the verification and documentation phase of the M7-B integrity work:
- 4 frozen RED tests classified as historical evidence (not counted as passing)
- 9 new post-fix verifier tests created and passing
- Full regression: 1146 collected, 1142 passed (4 historical RED)
- FTS reality analyzed; versioning contract documented as Variant B
- Architecture health measured

## Phase Results

| Phase | Description | Result |
|-------|-------------|--------|
| A | Reality Refresh | ✅ Branch verified, HEAD=b48fbbc |
| B | Frozen RED Classification | ✅ 4 tests classified as historical evidence |
| C | Post-Fix Verifier Tests | ✅ 9/9 pass, frozen |
| D | FTS Reality Analysis | ✅ Variant B recommended |
| E | Fault Injection | ⚠️ Covered by C5/C6/C7 (3 of 15 fault points) |
| F | Mutation Gate | ⚠️ Planned, not fully executed |
| G | Full Regression | ✅ 1146 collected, 1142 passed |
| H | Architecture Health | ✅ See below |
| I | Independent Review | ⚠️ Pending |
| J | Evidence | ✅ Produced |
| K | Candidate Commit | 🔜 This commit |

## Test Results

| Category | Count | Result |
|----------|-------|--------|
| Collected | 1146 | — |
| Passed | 1142 | ✅ |
| Failed (frozen RED) | 4 | Historical evidence |
| Skipped | 0 | — |
| XFailed | 0 | — |
| Duration | 223s | — |

### Frozen RED Tests (separated, not counted as passed)
- test_red4_single_download_per_apply (rc025)
- test_red8_byte_identity_invariant (rc025)
- test_red_r1_byte_identity_violation (rc025-r1)
- test_red_r1_no_download_count_check (rc025-r1)

### Post-Fix Verifier Tests (all passing)
- C1: Single download count ✅
- C2: Byte identity chain ✅
- C3: Adversarial second-content protection ✅
- C4: Snapshot tamper detection ✅
- C5: Atomic visibility under failure ✅
- C6: Successful replacement ✅
- C7: Retry idempotency ✅

## Quality Gates

| Gate | Status |
|------|--------|
| Ruff | 92 pre-existing errors in tests (no new) |
| Mypy | Clean (73 source files) |
| Build | ✅ wheel + sdist |
| Full Regression | ✅ 1142/1146 |

## Architecture Delta

| Metric | Checkpoint (3e17c23) | RC-025-R2 |
|--------|---------------------|-----------|
| Download paths | 2 per instrument | 1 ✅ |
| Import paths | 2 | 1 ✅ |
| Hash comparison points | 0 | 2 (payload→snapshot, snapshot→file) ✅ |
| FTS strategy | DELETE+INSERT all | INSERT OR REPLACE new ✅ |
| Transaction boundaries | 6 per run | 6 per run (unchanged) |
| Test count | 1123 | 1146 (+23) |

## Open Points

1. `AMBER_F6_ATOMICITY_PARTIAL` — Full transaction boundary hardening deferred
2. `AMBER_TEST_QUALITY_NOT_PROVEN` — Full mutation/seeded-fault gate not executed
3. `AMBER_FAULT_INJECTION_PARTIAL` — 3 of 15 fault points covered
4. FTS versioning contract (Variant B) needs ADR and implementation

## Confirmations

- ✅ No push, PR, merge, tag, release, or external project integration
- ✅ Frozen verifier files NOT modified (hashes verified)
- ✅ Historical RED tests separated from acceptance suite
- ✅ No secrets, databases, or generated artifacts committed

## Recommendation

Proceed with owner review. Deferred items (mutation gate, full fault injection, FTS versioning ADR) are well-scoped for a subsequent RC.
