# RC-025-R3 Baseline

**Generated:** 2026-08-02 | **Branch:** verify/rc025-r3-atomicity-closure  
**HEAD:** 11e75e1

## Verifier Hashes (Frozen)

| File | SHA-256 |
|------|---------|
| tests/rc025/test_m7b_contract_red.py | e59cd13e |
| tests/rc025-r1/test_verifier_red.py | 1ad2456e |
| tests/rc025_r2_verifier/test_post_fix_verifier.py | 03ad61a1 |

## Post-Fix Verifier Tests

```
9 collected, 9 passed, 0 failed, 2 warnings, 2.27s
✅ C1 download_count == 1
✅ C2 byte identity chain
✅ C3 adversarial second-content
✅ C4 snapshot tamper detection
✅ C5 atomic visibility under failure
✅ C6 successful replacement
✅ C7 retry idempotency
```

## Mypy

```
Success: no issues found in 73 source files
Exit code: 0
```

## Ruff

```
92 errors, 52 fixable, exit code 0
```

### Breakdown by Source

| Source | Count | Rules | Introduced In |
|--------|-------|-------|---------------|
| tests/integration/test_sync_*.py (5 files) | 10 | F821, I001 | RC-025-R1 (test mock forward refs) |
| tests/project_enforcement/ (5 files) | 47 | F401, E402, E501, SIM221, I001 | Pre-existing |
| tests/e2e/ | ~15 | Various | Pre-existing |
| Other tests | ~20 | Various | Pre-existing |

### RC-025-R3 Delta

**No new ruff violations introduced.** All 92 errors were present in commit `11e75e1`. The 5 `F821 Undefined name 'VerifiedSourcePayload'` errors in integration test mocks were introduced during RC-025-R1 when `download_verified()` mock functions were added with string forward-reference type annotations.

## Full Regression

(Results from background run — see evidence/rc025-r3/baseline/full-regression.txt)
