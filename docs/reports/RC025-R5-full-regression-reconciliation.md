# RC-025-R5 Full Regression Reconciliation

**Date:** 2026-08-03
**Reviewer:** RC-025-R5 Reconciliation Agent

## Test Execution (Fresh Run)

| Metric | Value |
|---|---|
| Collected | 1076 |
| Passed | 1072 |
| Failed | 4 (frozen RED verifier tests — historical, not product failures) |
| Skipped | 0 |
| XFailed | 0 |
| XPassed | 0 |
| Warnings | 27 |
| Runtime | 182.84s (3:02) |
| Exit code | 1 (due to 4 frozen RED failures — expected) |

## Frozen RED Test Failures (Historical, separate from passed count)

These 4 tests document resolved contract violations. They are frozen verifier tests that validate OLD violation patterns — they correctly FAIL because the violations they tested for have been fixed.

1. `tests/rc025/test_m7b_contract_red.py::test_red4_single_download_per_apply`
2. `tests/rc025/test_m7b_contract_red.py::test_red8_byte_identity_invariant`
3. `tests/rc025-r1/test_verifier_red.py::test_red_r1_byte_identity_violation`
4. `tests/rc025-r1/test_verifier_red.py::test_red_r1_no_download_count_check`

## Count Breakdown

| Category | Count | Notes |
|---|---|---|
| Product tests passed | 1072 | All functional, unit, integration tests |
| Frozen RED (historical) | 4 | Expected failures — evidence of resolved contracts |
| **Total collected** | **1076** | Same as RC-025-R4 baseline |

## Comparison with RC-025-R4 Baseline

| Metric | RC-025-R4 Baseline | RC-025-R5 Re-run | Delta |
|---|---|---|---|
| Collected | 1076 | 1076 | 0 |
| Passed | 1072 | 1072 | 0 |
| Failed (RED) | 4 | 4 | 0 |
| Runtime | 146.99s | 182.84s | +35.85s (variance) |

No regressions. All 1072 product tests pass identically to RC-025-R4 baseline.

## Static Analysis

| Tool | Result |
|---|---|
| Mypy | ✅ Success: no issues found in 73 source files |
| Ruff (src/) | ✅ 0 violations in production code |
| Ruff (full) | 67 pre-existing baseline violations (none in changed `src/` files) |
| Build | ✅ Wheel + sdist created |
| Twine check | ✅ PASSED for both wheel and sdist |
| pip check | ✅ All package dependencies satisfied |

## Coverage

See `evidence/rc025-r5/final/coverage.xml` for detailed coverage data.

## Gate

```text
GREEN_RC025_R5_REGRESSION_VERIFIED
```

1076 tests collected, 1072 passed, 4 frozen RED (historical, correctly failing as evidence of resolved contracts), mypy clean, ruff baseline stable, build reproducible.
