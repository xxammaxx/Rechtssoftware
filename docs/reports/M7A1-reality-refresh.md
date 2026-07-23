# M7-A.1 Reality Refresh Report

**Generated:** 2026-07-23
**Agent:** issue-orchestrator
**Risk Tier:** HIGH_HUMAN_GATE

---

## 1. Preflight Discovery

| Property | Value |
|----------|-------|
| OS/Shell | Windows / PowerShell 5.1 |
| Python | 3.14.6 |
| Git | (available) |
| Repo Path | C:\Rechtssoftware |
| Branch | main |
| HEAD | 01ac1cb0b630c8bd7c3f2cb4d1711c2c7d601e56 |
| HEAD Date | 2026-07-23 09:30:26 +0200 |
| HEAD Message | Merge pull request #8 from xxammaxx/feat/m7a-legal-source-foundation-integrated |
| Remote | origin → https://github.com/xxammaxx/Rechtssoftware.git |
| Working Tree | Clean (0 modified tracked files) |
| pip check | No broken requirements found |
| Ruff | All checks passed (68 source files) |
| Mypy | Success: no issues found in 68 source files |
| Tests | 751 collected, 751 passed, 49 test files |
| Coverage | **73% (FAIL: under 90%)** |
| Python target | pyproject.toml declares py311, actual runtime 3.14.6 |

## 2. Version Inconsistency Matrix

| Source | Version |
|--------|---------|
| `pyproject.toml` | `0.1.0` |
| `pip show` | `0.1.0` |
| `app.py` (FastAPI) | `0.2.0` (hardcoded) |
| `CHANGELOG.md` | `v0.2.0-rc (2026-07-23)` |
| `__init__.py` | No `__version__` defined |
| CLI `--version` | Not implemented |

**Root Cause:** `app.py:162` hardcodes `version="0.2.0"` instead of deriving from package metadata. pyproject.toml was never updated from 0.1.0.

## 3. Coverage Gap Analysis

Top uncovered modules (>50% uncovered):

| Module | Coverage | Unc. Lines | Status |
|--------|----------|------------|--------|
| `__main__.py` (CLI) | 0% | 146 | No CLI tests at all |
| `m7a_ui_routes.py` | 27% | 132 | M7A UI routes largely untested |
| `case_timeline_service.py` | 27% | 96 | Event/link operations untested |
| `citation_resolver.py` | 37% | 88 | Resolution logic untested |
| `gii_adapter.py` | 42% | 219 | GII import pipeline untested |
| `safe_source_client.py` | 42% | 74 | Transport policy barely tested |
| `sqlite_case_timeline_repository.py` | 38% | 111 | Timeline persistence untested |
| `legal_source_service.py` | 40% | 46 | Service untested |
| `sqlite_legal_source_repository.py` | 72% | 63 | Repository partially tested |
| `csrf.py` | 67% | 26 | CSRF partially untested |

## 4. Defect Classification by Track

### Track A — Cross-Case Isolation (BLOCKING)

**Severity: HIGH** — Data integrity and authorization bypass.

**Findings:**

1. `case_timeline_service.py` mutation methods accept only entity ID, not case_id:
   - `confirm_event(event_id)` — no case_id validation
   - `reject_event(event_id)` — no case_id validation
   - `correct_event(event_id, ...)` — no case_id validation
   - `revoke_event(event_id)` — no case_id validation
   - `confirm_link(link_id)` — no case_id validation
   - `reject_link(link_id)` — no case_id validation
   - `correct_link(link_id, ...)` — no case_id validation
   - `revoke_link(link_id)` — no case_id validation

2. UI routes (m7a_ui_routes.py) call service methods without passing case_id:
   - `confirm_norm_link` calls `svc["timeline"].confirm_link(link_id)` — no case verification
   - `confirm_legal_event` calls `svc["timeline"].confirm_event(event_id)` — no case verification
   - Same pattern for reject, correct, revoke

3. Additionally, `m7a_ui_routes.py` passes string IDs to methods expecting UUID — works at runtime only because Python doesn't enforce type hints, but is a latent bug.

**Impact:** An event/link belonging to case A can be confirmed/rejected/corrected/revoked through case B's route.

### Track B — True Legal Source Status (BLOCKING)

**Severity: MEDIUM** — Trust integrity violation.

**Findings:**

1. `legal_source_service.get_source_status()` returns only static metadata (source_key, display_name, authority_tier, enabled, base_url) — no runtime statistics.

2. UI route `legal_source_status` uses `hasattr` pattern to check for `list_snapshots_for_source` on repository — fallback pattern that simulates optional functionality.

3. No `LegalSourceStatusDTO` with snapshot_count, instrument_count, provision_count, integrity_status, etc.

4. `enabled=True` is conflated with "Integrity OK" — no `NOT_VERIFIED` distinction.

### Track C — Snapshot Storage and Integrity (BLOCKING)

**Severity: HIGH** — Data integrity and documentation truth violation.

**Findings:**

1. `_atomic_write` in `safe_source_client.py` uses UUID-based file names (`f"{uuid.uuid4().hex}.snap"`), NOT content-addressable SHA-256 paths as documented in README.

2. Duplicate detection happens post-write: `legal_source_service.sync_gii_instrument()` checks for duplicate hash AFTER the file has been written to disk, meaning duplicate content creates a wasted file.

3. `verify_snapshot()` returns only `bool` — no rich result object with hash comparison, file existence, size checks.

4. No `verify_all_snapshots()` method exists.

5. No public integrity operation that the CLI can call without layer violations.

6. `TransportPolicy.PRODUCTION` mode is not enforced — the `mode` parameter defaults to `PRODUCTION` in the policy but the policy object can be constructed with `TEST` mode by the GII adapter through the `SourceClient` constructor. Production bypass paths exist.

7. No TLS verification enforcement check.

### Track D — CLI Verification (BLOCKING)

**Severity: HIGH** — Fake verification output.

**Findings:**

1. `__main__.py:_handle_legal_source` `verify` action (lines 156-171):
   - Accesses `svc._repo._db_path` — violation of privacy (underscore-prefixed attribute)
   - Violates layer boundary (CLI accessing repository internals)
   - Does NOT actually verify any snapshots — just increments `ok += 1` for each source
   - No file hash comparison
   - No actual integrity check

2. No `--json` output flag support.

3. No `--snapshot-id` flag support.

4. Exit codes documented but not implemented correctly: exit 0 is always returned regardless of actual state.

### Track E — Norm-Link Workflow

**Severity: MEDIUM** — Usability barrier.

**Findings:**

1. UI template likely requires manual UUID copying for norm linking — needs template inspection to confirm.

2. No inline confirmation workflow from norm detail page.

3. FTS snippets may use unsafe `|safe` filter on untrusted text — needs template audit.

### Track F — Evidence Pack Truth (BLOCKING)

**Severity: MEDIUM** — Documentation truth violation.

**Findings:**

1. `build_evidence_pack()` sets `confirmed_facts=[]` and `legal_issues=[]` as hardcoded empties — no indication they are `NOT_TRACKED_IN_THIS_RELEASE`.

2. `integrity.snapshot_hashes` lists hashes but no verification status (VERIFIED/FAILED/MISSING/NOT_VERIFIED).

3. No actual integrity check runs — it just records hashes from database.

4. No `legal_issues` are populated (the table exists but no service loads them).

### Track G — Version and Truth Mirror (BLOCKING)

**Severity: MEDIUM** — Documentation truth violation.

**Findings:**

1. Three different version values in three different sources.
2. README claims "content-addressable raw snapshots" — code uses UUID paths.
3. README claims "keine externen Laufzeitrequests" — GII adapter makes external HTTPS requests.

## 5. Working Tree Status

```
Untracked files present (from prior runs):
  .hermes.md, .hermes/, .opencode/, .playwright-mcp/
  CONTRIBUTING.md, SECURITY.md
  coverage.json, coverage.xml
  docs/reports/ (prior reports)
  e2e-screenshots/, evidence/, node_modules/
  opencode.jsonc, package.json, package-lock.json
  server-*.log, test-results/
```

No modified tracked files. Safe to proceed.

## 6. Test Baseline

- **751 tests pass** (all green)
- **Coverage: 73%** (FAIL: threshold is 90%)
- **Ruff:** All checks passed
- **Mypy:** Success
- **pip check:** No broken requirements

## 7. Observation Summary

The M7-A codebase has a solid architectural foundation but 7 blocking defects across 6 tracks must be resolved before M7-A can be declared closed. The most critical are:

1. **Cross-case mutation authorization bypass** (Track A) — data integrity risk
2. **Fake CLI verify command** (Track D) — trust violation
3. **UUID-based snapshot paths** (Track C) — diverges from documented content-addressable storage
4. **Version inconsistency** (Track G) — 3 different versions in 3 different sources

## 8. Next Step

Proceed to Context Manifest and delegate implementation tracks to subagents following the HIGH_HUMAN_GATE workflow per `WORKING-METHOD.md`.
