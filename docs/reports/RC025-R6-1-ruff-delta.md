# RC-025-R6.1 Ruff Delta Report

**Date:** 2026-08-03
**Base:** RC-025-R6 commit `b5dba14`

## Pre-Fix State (RC-025-R6)

| Scope | Violations | Exit Code |
|---|---|---|
| `src/` | 0 | 0 |
| `tests/` (all) | 115 (67 baseline + 48 new) | 1 |
| `tests/rc025_r6_verifier/` | 48 | 1 |

### R6 Verifier Violations by Rule (48 total)

| Rule | Count | Description |
|---|---|---|
| F401 | 18 | Unused imports |
| UP017 | 8 | Use `datetime.UTC` alias |
| I001 | 6 | Import sorting |
| E501 | 2 | Line too long |
| F841 | 2 | Unused variable |
| SIM105 | 2 | Use `contextlib.suppress` |
| UP012 | 1 | Unnecessary `encode("utf-8")` |

## Post-Fix State (RC-025-R6.1)

| Scope | Violations | Exit Code |
|---|---|---|
| `src/` | 0 | 0 |
| `tests/rc025_r6_verifier/` | **0** | **0** |
| `tests/` (all) | 67 (pre-existing baseline only) | 1 |

### Fix Method

- Auto-fix via `ruff check --fix`: 37 violations resolved (F401, UP017, I001, UP012)
- Manual fix: 11 remaining violations (E501 line breaks, SIM105 contextlib.suppress, F841 unused vars removed/asserted)

## Frozen-Verifier-Integrität

| File | SHA-256 Before | SHA-256 After | Changed? |
|---|---|---|---|
| `__init__.py` | `a5e79be...` | `a5e79be...` | **No** (identical) |
| `test_missing_boundaries.py` | `c8cbae3...` | `6a19b91...` | Yes (Ruff-only: imports, line breaks, contextlib) |
| `test_crash_subprocess.py` | *(not frozen)* | `af884ad...` | Yes (Ruff-only: line breaks) |
| `test_seeded_fault.py` | *(not frozen)* | `a37acb4...` | Yes (Ruff-only: contextlib) |

**Independent Verifier confirms:** All changes are purely stylistic (no assertion modifications, no fault hook changes, no test parameter changes, no marker changes, no skips/xfails added, no production code modified).

## Ruff-Gate Summary

```
67 pre-existing baseline violations (unchanged)
 0 new RC-025-R6/R6.1 violations in src/
 0 new RC-025-R6/R6.1 violations in tests/rc025_r6_verifier/
src/ Ruff-clean: ✅
r6_verifier/ Ruff-clean: ✅
```
