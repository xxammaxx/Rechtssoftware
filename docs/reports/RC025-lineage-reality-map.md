# RC-025 Lineage Reality Map

**Generated:** 2026-08-02
**Canonical Worktree:** `/media/xxammaxx/projekte/Rechtssoftware`
**Branch:** `feat/product-ux-design-evolution-v1`

## Preflight

| Item | Value |
|------|-------|
| OS | Linux 6.8.0-124-generic (Ubuntu, x86_64) |
| Shell | /bin/bash |
| Git | 2.43.0 |
| Python (system) | 3.12.3 (/usr/bin/python3) |
| Python (venv) | 3.12.3 (.venv/bin/python) |
| Node | v22.22.0 |
| npm | 10.9.4 |
| Remote | `https://github.com/xxammaxx/Rechtssoftware.git` |
| Worktrees | 1 (single: `/media/xxammaxx/projekte/Rechtssoftware`) |
| Running Processes | None (Rechtssoftware) |
| SQLite Files | None (project-specific; only mypy caches) |

## Kanonizitätsprüfung (A2)

| Kriterium | Status | Evidence |
|-----------|--------|----------|
| Remote auf `xxammaxx/Rechtssoftware` | ✓ | `git remote -v` confirms |
| Commit `a6e4c24` vorhanden | ✓ | HEAD = `a6e4c24f8eec0e9df6a4d7e6c1b12f0af70269fc` |
| RC-023-Evidence vorhanden | ✓ | `evidence/rc023-*/` directories present |
| Keine unbekannten uncommitted changes | ✓ | Only AGENTS.md (2-line deletion, known) + webm video |
| Branch-/Worktree-Lineage reproduzierbar | ✓ | Single worktree, clear ancestry |

**Verdict:** `/media/xxammaxx/projekte/Rechtssoftware` is the single canonical worktree.

## Lineage Classification

### Sources Evaluated

| Source | Commit | Class | Rationale |
|--------|--------|-------|-----------|
| Remote-Main | `7797a869450558455b303556191c7ec4474901b1` | `CANONICAL_BASE` | Merged M7B work; ancestor of all candidates |
| PR-Head (#11) | `35742bbfd1732a86dd4360500b268f6ef8089d68` | `STALE_BRANCH` | Single commit atop main; largely superseded by RC branch |
| Lokaler RC-023-Candidate | `a6e4c24f8eec0e9df6a4d7e6c1b12f0af70269fc` | `DESCENDANT_CANDIDATE` | Direct descendant of CANONICAL_BASE; current HEAD |
| Aktueller lokaler HEAD | `a6e4c24f8eec0e9df6a4d7e6c1b12f0af70269fc` | `DESCENDANT_CANDIDATE` | Same as RC-023-Candidate |
| M7B-Arbeitsbranch | `274292e` (feat/m7b-incremental-gii-sync) | `CANONICAL_BASE` | Ancestor of origin/main; absorbed into main and HEAD |

### Ancestry Order

```
3de5d0d (main, release/v0.2.1-local-closure)
├── 97affdb (test: validate installed wheel runtime)
├── 99328c0 (fix: close security and truthful sync runtime)
├── 274292e (feat: implement incremental GII sync foundation, M7B branch)
├── f4519e5 (feat: implement incremental GII sync foundation)
├── 66345a2 (test: add integration and unit tests for sync)
├── 7797a86 (origin/main: complete incremental sync) ← CANONICAL_BASE
│   ├── 35742bb (PR #11: v1.0.0-rc.1 release) ← STALE_BRANCH
│   └── d2ed916 (reconstruct rc branch with selective pr11 port)
│       └── 6acdd7e (harden windows lifecycle)
│           └── 6094655 (release/v1.0.0-rc.1-reconciled)
│               └── 1be64f3 (advance to 1.0.0rc2)
│                   └── ... (rc2 work)
│                       └── 6a62460 (release/v1.0.0-rc.2-reconciled)
│                           └── 9e304a6 (case tab navigation)
│                               └── 4fd0f04 (evidence-first redesign)
│                                   └── e8ca70c (fix css)
│                                       └── a76ba47 (fix a11y)
│                                           └── a6e4c24 (HEAD) ← DESCENDANT_CANDIDATE
```

### Key Observations

1. **HEAD contains all M7B code**: `git merge-base --is-ancestor origin/main HEAD` returns true. The M7B sync infrastructure (GII sync planning, execution, recovery, FTS5) is fully present in HEAD.
2. **Single worktree**: No ambiguity. Only one Rechtssoftware worktree exists on this system.
3. **HEAD is ahead of main**: `origin/main..HEAD` = 0 commits (nothing in main that HEAD doesn't have). `HEAD..origin/main` = 20 commits of UI evolution and release work.
4. **PR #11 is superseded**: Selective port (`d2ed916`) already incorporated relevant PR #11 changes into the RC branch.

## Uncommitted Changes (Non-Blocking)

| File | Status | Risk |
|------|--------|------|
| `.private-review-evidence/rc017-visible-e2e/video/...webm` | Modified (binary) | None — review evidence |
| `AGENTS.md` | Modified (2 lines deleted) | To be repaired in Phase D |

Untracked files include RC-025.md, `.hermes/` (enforcement/plugin data), `evidence/` (existing), and test files — all expected during development.
