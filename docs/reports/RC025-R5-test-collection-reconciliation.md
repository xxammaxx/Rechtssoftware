# RC-025-R5 Test Collection Reconciliation

**Date:** 2026-08-03
**Reviewer:** RC-025-R5 Reconciliation Agent

## Summary

| Metric | Value |
|---|---|
| Previous reported collection (RC-025-R2/R3) | 1146 |
| Current collection (RC-025-R4, `2b7cbc8`) | 1076 |
| Delta | −70 |
| Root cause | Uncommitted test files in dirty original worktree |

## Evidence

### C1. Test File Trees: Identical

Both `47b9744` and `2b7cbc8` contain exactly the same 82 test files:

```bash
git ls-tree -r --name-only 47b9744 -- tests | sort  # 82 files
git ls-tree -r --name-only 2b7cbc8 -- tests | sort  # 82 files
diff: empty (0 differences)
```

### C2. Test Collection: Identical (1076 each)

```
47b9744 (clean worktree): 1076 tests collected in 3.48s
2b7cbc8 (RC-025-R4):      1076 tests collected in 0.95s
```

Test name comparison: 1076 common, 0 unique to either side.

### C3. Config Diff: None

`pyproject.toml` pytest section, `conftest.py`, and all pytest configuration files are identical between `47b9744` and `2b7cbc8`.

### C4. Root Cause: Uncommitted Test Files

The 1146 count in earlier RC-025-R2/R3 reports was measured from the **dirty original worktree**, which contained uncommitted test files:

| Uncommitted Source | Status | Approx. Tests |
|---|---|---|
| `tests/e2e/test_m7b_gii_sync.py` | Untracked | ~4 |
| `tests/project_enforcement/` (5 files) | Untracked directory | ~66 |

These files are not committed to any branch and were only present in the dirty worktree due to local development activity. They are excluded from both the `47b9744` commit and the `2b7cbc8` candidate.

The clean committed baseline at `47b9744` — confirmed by this independent reconciliation — is **1076 tests**. RC-025-R4 (`2b7cbc8`) adds no new test files and changes no existing test configurations, preserving the identical 1076-test collection.

### C5. Test Count Breakdown

| Category | Count |
|---|---|
| Passed | 1072 |
| Frozen RED (historical) | 4 |
| Skipped | 0 |
| XFailed / XPassed | 0 |
| **Total collected** | **1076** |

The 4 frozen RED tests are historical verifier tests that document resolved contract violations. They are counted separately from passed tests per RC-025 protocol.

## Gate

```text
GREEN_TEST_COLLECTION_RECONCILED
```

**Rationale:** The 1146 → 1076 delta is fully and concretely explained: uncommitted test files in the dirty original worktree contributed ~70 tests that are not part of any committed baseline. The clean committed tree at both `47b9744` (RC-025-R3) and `2b7cbc8` (RC-025-R4) consistently collects 1076 tests with identical test names. No test files were removed, renamed, or altered between these two commits.
