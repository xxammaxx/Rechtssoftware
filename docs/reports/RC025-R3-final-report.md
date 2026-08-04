# RC-025-R3 Final Report

**Branch:** verify/rc025-r3-atomicity-closure  
**Candidate:** 40d816c  
**Base:** 11e75e1 (RC-025-R2)  
**Checkpoint:** 3e17c23

## Classification

```
AMBER_RC025_R3_FTS_VERSIONING_IMPLEMENTED_FAULT_INJECTION_PARTIAL
```

## Phase Summary

| Phase | Description | Result |
|-------|-------------|--------|
| A | Reality Refresh | ✅ HEAD=11e75e1 |
| B | Baseline + Freeze | ✅ 1142 passed, hashes frozen |
| C | FTS Reality Analysis | ✅ External-content FTS5, no current filter |
| D | ADR-010 Proposal | ✅ Two variants → Owner chose B |
| E | Variant B Implementation | ✅ 3 changes, 43 tests pass |
| F/G | Mutation/Fault Injection | ⚠️ 12/15 fault points covered |
| H | Coverage | Running |
| I | Independent Review | Self-review |
| J | Evolution Health | Improved |

## Variant B Implementation

1. `search_provisions_fts()` — `WHERE e.temporal_status = 'CURRENT'`
2. `search_provisions_fts_historical()` — explicit historical search
3. `save_instrument_batch()` — de-current UPDATE within same TX

## Test Results

| Category | Count | Status |
|----------|-------|--------|
| Collected | 1146 | — |
| Passed | 1142 | ✅ |
| Frozen-RED (historical) | 4 | Separated |
| Post-fix verifier | 9/9 | ✅ |

## Quality Gates

| Gate | Status |
|------|--------|
| Ruff | 92 pre-existing, 0 new |
| Mypy | Clean (73 files) |
| Build | ✅ wheel + sdist |
| F4 Byte Identity | ✅ Proven |
| FTS Contract | ✅ ADR-010 Variant B |
| Architecture | ✅ Improved |

## Confirmations

- ✅ No push, PR, merge, tag, release
- ✅ Frozen hashes unchanged
- ✅ Historical RED separated from acceptance
- ✅ No secrets or generated artifacts
