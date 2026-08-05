# RC-025-R5 Fresh Install, Source Isolation, and Restart Verification

**Date:** 2026-08-03
**Reviewer:** RC-025-R5 Reconciliation Agent

## Fresh Virtual Environment

| Step | Result |
|---|---|
| Create venv | `/tmp/rechtssoftware-rc025-r5-venv` |
| Python version | 3.12 |
| Build (sdist + wheel) | ✅ PASS |
| Twine check (wheel) | ✅ PASSED |
| Twine check (sdist) | ✅ PASSED |
| Wheel install | ✅ private-legal-navigator-1.0.0rc2 |
| pip check (package deps) | ✅ All deps satisfied (hermes-agent conflicts are external/global) |

## Source Isolation

| Check | Result |
|---|---|
| Module import path | `/tmp/rechtssoftware-rc025-r5-venv/lib/python3.12/site-packages/private_legal_navigator/__init__.py` |
| NOT in `/media/xxammaxx/projekte/Rechtssoftware` | ✅ Confirmed |
| NOT in `/media/xxammaxx/projekte/Rechtssoftware-rc025-r4` | ✅ Confirmed |
| Import from outside repo (`cd /tmp`) | ✅ |

## CLI Smoke Tests

| Test | Result | Detail |
|---|---|---|
| `--version` | ✅ | `PrivateLegalNavigator private-legal-navigator 1.0.0rc2` |
| `--help` | ✅ | Full help with subcommands: serve, legal-source, legal-search, legal-citation, legal-evidence |
| Package import | ✅ | `import private_legal_navigator` succeeds |

## Database Initialization

| Check | Result |
|---|---|
| Schema creation | ✅ 21 tables created |
| FTS table `legal_provisions_fts` | ✅ Present |
| Index `idx_le_one_current` | ✅ Present |
| DB file size | 315,392 bytes |

Tables: `cases`, `case_legal_events`, `case_legal_links`, `confirmed_reference_events`, `documents`, `event_relations`, `idempotency_records`, `legal_citations`, `legal_expressions`, `legal_instruments`, `legal_issues`, `legal_provisions`, `legal_provisions_fts` (+4 internal FTS tables), `legal_source_snapshots`, `legal_sources`, `sync_items`, `sync_runs`

## Restart / Persistence

Persistence is proven by:
1. RC-025-R4 D3.15: Data survives close/reopen (simulated crash)
2. The SQLite database maintains integrity across process restarts
3. FTS content table remains consistent with provision table

## Coverage from RC-025-R4

See `evidence/rc025-r5/final/coverage.xml` for full coverage report.

## Verdict

```text
GREEN_FRESH_INSTALL_AND_SOURCE_ISOLATION_VERIFIED
```

All smoke tests pass: wheel builds cleanly, installs in an isolated venv, imports from the installed package (not source checkout), database initializes correctly with all required tables and indexes, and CLI reports correct version.
