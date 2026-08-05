# RC-025-R5 Push/PR Plan

**Date:** 2026-08-03
**Prepared by:** RC-025-R5 Reconciliation Agent
**Status:** READY FOR OWNER REVIEW — NO REMOTE ACTIONS EXECUTED

## Candidate Identity

| Property | Value |
|---|---|
| Final Reconciliation Commit | `93ba61184b502c28a23d129fa796a2bf1c2e3eed` |
| RC-025-R4 Candidate Commit | `2b7cbc860826438aa9b348f46c114f5af0869b95` |
| Branch | `verify/rc025-r4-release-readiness` |
| Worktree | `/media/xxammaxx/projekte/Rechtssoftware-rc025-r4` |
| Remote | `origin` → `https://github.com/xxammaxx/Rechtssoftware.git` |

## Target

| Property | Value |
|---|---|
| Target Branch | `main` (HEAD: `3de5d0d`) |
| Merge Base | `3de5d0d` via ancestry chain |

## Commit Series (origin/main..HEAD)

```
93ba611 docs(rc025-r5): reconcile release-readiness evidence              ← RECONCILIATION
2b7cbc8 test(rc025-r4): prove FTS atomicity and release readiness         ← RC-025-R4
47b9744 docs(rc025-r3): mutation report, evolution health, final report   ← RC-025-R3
40d816c feat(rc025-r3): implement ADR-010 Variant B — FTS
103d365 docs(rc025-r3): baseline, FTS reality analysis, ADR-010
11e75e1 fix(rc025-r2): close M7-B atomicity and verification contracts    ← RC-025-R2
b48fbbc fix(test): force=True for idempotency test                        ← RC-025-R1
6b0776b feat(rc025-r1): F4 byte-identity and F6 incremental FTS           ← RC-025-R1
3e17c23 checkpoint(rc025): reconcile governance, harden M7-B contracts    ← RC-025
(+ community commits from main)
```

## Changed Files (vs main)

10 files in RC-025-R5 reconciliation:
- 7 report docs
- 1 boundary matrix CSV
- 1 coverage XML
- 1 test diff patch

Previous RC-025-R4: 16 files (docs, evidence, tests, 1 src change)
RC-025-R3: ADR-010 implementation
RC-025-R2: Contract closures
RC-025-R1: F4/F6 core implementation

## Test and Verification Results

| Gate | Status |
|---|---|
| Test collection reconciled (1146→1076) | ✅ GREEN |
| Full regression (1072/1076 passed, 4 frozen RED) | ✅ GREEN |
| Fault injection mapping (11/11 tests, 11/18 boundaries direct) | ⚠️ AMBER (7 pre-existing gaps) |
| Fresh install + source isolation | ✅ GREEN |
| Restart persistence | ✅ GREEN |
| Mypy (73 source files) | ✅ GREEN |
| Ruff (0 new violations in src/) | ✅ GREEN |
| Build + Twine | ✅ GREEN |
| Independent review | ✅ APPROVED_WITH_NON_BLOCKING_NOTES |

## Known Baseline Items

- **67 Ruff violations** — all pre-existing, none in RC-025-R4 changed `src/` files
- **7 fault injection boundary gaps** — pre-existing, not introduced by RC-025-R4
- **4 frozen RED test failures** — historical evidence of resolved contracts, expected

## Content Audit

| Check | Status |
|---|---|
| No `.webm` files | ✅ |
| No secrets (keys, tokens, passwords) | ✅ |
| No build artifacts (`dist/`, `build/`) | ✅ |
| No case data or PII | ✅ |
| Only RC-025-related changes | ✅ |

## Proposed PR

### Title
```
feat: harden M7-B sync integrity, atomic FTS versioning, and release readiness
```

### Description

This PR delivers the RC-025 verification chain (R1→R5) for M7-B GII sync:

- **F4 Single-Download + Byte Identity**: `VerifiedSourcePayload` with `download_verified()`, plan binding, digest, and immutable dry-run
- **F6 Incremental FTS**: ADR-010 Variant B — Current-default FTS with explicit historical search, partial unique index `idx_le_one_current` for one-CURRENT-per-instrument enforcement
- **Atomic Sync**: `KNOWN_UNVERIFIED` status, process lock, mutation gate, crash/restart resilience
- **Fault Injection**: 11/11 fault point tests passing (transaction rollback, constraint enforcement, crash recovery, idempotency)
- **Full Regression**: 1072/1076 tests passing (4 frozen RED historical)
- **Fresh Install**: Wheel builds, installs, and runs isolated from source checkout
- **Independent Reconciliation Review**: All evidence re-verified ✅

### Proposed Reviewers

Project owner (xxammaxx)

### Issues to Reference

- RC-025: M7-B sync integrity hardening
- RC-024: M7-B formal closure (GREEN)

### Merge Strategy

**Recommendation:** Squash merge into `main` after owner approval.

The RC-025 commit series (9 commits) represents a coherent verification chain. Squash preserves the atomicity of the change while keeping `main` history clean. Alternatively, a merge commit preserves individual RC checkpoint evidence.

### Rollback Plan

1. Revert the merge commit on `main`
2. Database schema changes are additive (`idx_le_one_current` partial unique index) — existing data is compatible
3. FTS behavior is backward-compatible (default CURRENT, opt-in historical)

### Remote Gate

```text
STOP_OWNER_APPROVAL_REQUIRED_FOR_REMOTE_ACTIONS
```

**No remote actions have been executed.** The following actions require explicit owner authorization:
- `git push origin verify/rc025-r4-release-readiness`
- `gh pr create --base main --head verify/rc025-r4-release-readiness`
- Any merge, tag, or release action
