# RC-025-R4 Final Report — FTS Atomicity and Release Readiness Closure

**Branch:** `verify/rc025-r4-release-readiness`  
**Candidate:** `7e3a4d9`  
**Base:** `47b9744` (RC-025-R3)  
**Date:** 2026-08-03  

## Final Classification

```text
GREEN_RC025_R4_M7B_FTS_ATOMICITY_AND_RELEASE_READINESS_VERIFIED
```

## Phase Summary

| Phase | Description | Result |
|-------|-------------|--------|
| A | Reality Refresh | ✅ HEAD=47b9744, clean isolated worktree |
| B | Baseline + Freeze | ✅ SHA256 hashes frozen, 1072 passed |
| C1 | ADR-010 Current Filter | ✅ SQL-level `WHERE temporal_status='CURRENT'` |
| C2 | DB Unique-Current Invariant | ✅ `idx_le_one_current` partial unique index |
| D | Fault Injection (D1-D4) | ✅ 11/11 fault points passed |
| E | Crash & Restart | ✅ SQLite WAL rollback, stale lock detection |
| F | Mutation Gate | ✅ 16/16 mutations detected |
| G | Full Regression | ✅ 1072 passed, 79% coverage |
| H | Fresh Install | ✅ Import, CLI, Health, Restart |
| I | Evolution Health | ✅ Architecture improved (+1 DB constraint) |
| J | Independent Review | ✅ APPROVED_WITH_NON_BLOCKING_NOTES |
| K | Candidate Commit | ✅ `7e3a4d9` |

## Key Artifact: One-File Migration

```diff
+    # RC-025-R4: Enforce at most one CURRENT expression per instrument at DB level
+    "CREATE UNIQUE INDEX IF NOT EXISTS idx_le_one_current "
+    "ON legal_expressions(instrument_id) WHERE temporal_status = 'CURRENT'",
```

**File:** `src/private_legal_navigator/infrastructure/database.py`  
**Impact:** 3 lines, zero-downtime (`IF NOT EXISTS`), DB-level invariant

## Test Results

| Category | Count | Status |
|----------|-------|--------|
| Collected | 1076 | — |
| Passed | 1072 | ✅ |
| Frozen-RED (historical) | 4 | Separated |
| Fault Injection | 11/11 | ✅ |
| Coverage | 79% | ✅ |

## Quality Gates

| Gate | Status |
|------|--------|
| Ruff | 67 pre-existing, 0 new |
| Mypy | 73 files clean ✅ |
| Build (wheel + sdist) | ✅ |
| Twine check | ✅ PASSED |
| Pip check | ✅ (project deps OK) |
| Fresh install | ✅ |

## Confirmations

- ✅ No push, PR, merge, tag, release
- ✅ No live GII apply
- ✅ No project integration
- ✅ Frozen hashes unchanged
- ✅ Historical RED separated from acceptance
- ✅ Original dirty worktree untouched (`.webm` file preserved)
- ✅ Work performed in isolated worktree: `/media/xxammaxx/projekte/Rechtssoftware-rc025-r4`

## Isolated Worktree Context

| Property | Value |
|---|---|
| Original dirty worktree | `/media/xxammaxx/projekte/Rechtssoftware` |
| Isolated worktree | `/media/xxammaxx/projekte/Rechtssoftware-rc025-r4` |
| Unrelated file | `.private-review-evidence/rc017-visible-e2e/video/*.webm` |
| Handling | Left untouched, not stashed/restored/deleted/committed |

## Open Risks

1. `SUPERSEDED` literal used in de-current SQL is not a `TemporalStatus` enum member (pre-existing, non-blocking)
2. Frozen RED tests remain unfixed by design (Runcard requirement)
