# RC-025-R4 Baseline Report

## Worktree Isolation

| Property | Value |
|---|---|
| Original dirty worktree | `/media/xxammaxx/projekte/Rechtssoftware` |
| Isolated RC-025-R4 worktree | `/media/xxammaxx/projekte/Rechtssoftware-rc025-r4` |
| Unrelated file | `.private-review-evidence/rc017-visible-e2e/video/a75183ac69526fed9f7cfbff5a174ef2.webm` (708 MB, SHA256 `ac165f70...`) |
| Handling | Left untouched in original worktree |
| RC-025-R4 base commit | `47b9744` |

## Commit Lineage

```
47b9744 docs(rc025-r3): mutation report, evolution health, final report
40d816c feat(rc025-r3): implement ADR-010 Variant B — FTS current/historical visibility
103d365 docs(rc025-r3): baseline, FTS reality analysis, and ADR-010 proposal
11e75e1 fix(rc025-r2): close M7-B atomicity and verification contracts
b48fbbc fix(test): use force=True in idempotency test to bypass catalog gate
```

## Git State

| Check | Result |
|---|---|
| HEAD | `47b9744da5616f58cc1514b0143cd50371d2808e` |
| Branch | `verify/rc025-r4-release-readiness` |
| Working tree | clean ✅ |
| Diff check | clean ✅ |

## Frozen Verifier Files (SHA256)

```
3e51d37b4937ffaf325e718a0e30dcca8cdb1a48b21186087853798592af77d7  tests/rc025/__init__.py
e59cd13e56ae4bf14dac0aa7e6b4a0f6849798d38b8d1763d43d4129167b3ffb  tests/rc025/test_m7b_contract_red.py
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  tests/rc025-r1/__init__.py
1ad2456e2ff708d9a6301382bcd95a6a8a1efd4383b0643f98c1375ed4cd12cf  tests/rc025-r1/test_verifier_red.py
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  tests/rc025_r2_verifier/__init__.py
03ad61a172909e4a897853d60aa6ef30067fe05a33876600206a90bbc17a398d  tests/rc025_r2_verifier/test_post_fix_verifier.py
```

## Test Results

| Metric | Value |
|---|---|
| Collected | 1076 |
| Passed | 1072 |
| Failed | 4 (frozen RED verifier tests) |
| Skipped | 0 |
| XFailed | 0 |
| XPassed | 0 |
| Warnings | 27 |
| Runtime | 146.99s |

### Frozen RED Test Failures (historical, separate from passed count)

1. `tests/rc025/test_m7b_contract_red.py::test_red4_single_download_per_apply`
2. `tests/rc025/test_m7b_contract_red.py::test_red8_byte_identity_invariant`
3. `tests/rc025-r1/test_verifier_red.py::test_red_r1_byte_identity_violation`
4. `tests/rc025-r1/test_verifier_red.py::test_red_r1_no_download_count_check`

## Test Count Discrepancy vs RC-025-R3 Baseline

RC-025-R3 reported 1146 collected / 1142 passed. The difference (70 tests) is due to uncommitted test files present in the original dirty worktree but absent from the clean commit `47b9744`:

- `tests/e2e/test_m7b_gii_sync.py` (untracked)
- `tests/project_enforcement/` (untracked directory)

The clean committed baseline at `47b9744` is **1076 collected / 1072 passed / 4 frozen RED**. This is the authoritative baseline for RC-025-R4.

## Static Analysis

| Tool | Result |
|---|---|
| Mypy | ✅ Success: no issues found in 73 source files |
| Ruff (src) | ✅ No violations in src/ |
| Ruff (tests, verifier only) | 67 pre-existing violations in frozen verifier files (baseline, not to be fixed) |

## Classification

```text
GREEN_RC025_R4_CLEAN_ISOLATED_WORKTREE_READY
```
