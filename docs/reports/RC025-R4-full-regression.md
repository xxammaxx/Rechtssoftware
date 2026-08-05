# RC-025-R4 Phase G — Full Regression and Coverage

## Test Results

| Metric | Value |
|--------|-------|
| Collected | 1076 |
| Passed | 1072 |
| Frozen-RED (historical) | 4 (separate) |
| Skipped | 0 |
| XFailed | 0 |
| XPassed | 0 |
| Warnings | 27 |
| Runtime | 235.32s (3:55) |

### Frozen RED Failures (expected, NOT counted as regressions)

1. `tests/rc025/test_m7b_contract_red.py::test_red4_single_download_per_apply`
2. `tests/rc025/test_m7b_contract_red.py::test_red8_byte_identity_invariant`
3. `tests/rc025-r1/test_verifier_red.py::test_red_r1_byte_identity_violation`
4. `tests/rc025-r1/test_verifier_red.py::test_red_r1_no_download_count_check`

## Coverage

| Scope | Total | Missed | Coverage |
|-------|-------|--------|----------|
| Overall | 6385 | 1365 | **79%** |
| `sqlite_legal_source_repository.py` (sync/repo) | 314 | 59 | **81%** |
| `sync_service.py` (core logic) | (included in total) | — | — |

Critical paths covered:
- ✅ Download → hash → import pipeline
- ✅ SHA-256 dedup
- ✅ FTS search (current + historical)
- ✅ DB transaction rollback
- ✅ Unique-current constraint
- ✅ Fault injection paths (D1-D4)

## Static Analysis

| Tool | Result |
|------|--------|
| Ruff (src) | 0 new violations (67 pre-existing in frozen verifier files) |
| Mypy | 73 source files clean ✅ |
| Build (wheel + sdist) | ✅ `private_legal_navigator-1.0.0rc2` |
| Twine check | ✅ PASSED (wheel + sdist) |
| Pip check | ✅ (project deps OK; hermes-agent host conflicts unrelated) |

## Classification

```text
GREEN_RC025_R4_FULL_REGRESSION_PASSED
```
