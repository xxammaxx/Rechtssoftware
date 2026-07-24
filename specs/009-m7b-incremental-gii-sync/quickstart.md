# Quickstart — M7-B Incremental GII Sync & Corpus Change Management

## Overview

This guide provides runnable validation scenarios for the M7-B feature (incremental GII sync). Use these to verify end-to-end behavior once the build phase begins.

**This is a spec-phase artifact.** No implementation code exists yet. All references to CLI commands and domain entities are forward-looking against the [spec](spec.md) and [CLI contract](contracts/sync-cli.md).

---

## Prerequisites

- Python 3.11+
- PrivateLegalNavigator installed (`pip install -e ".[dev]"`)
- M7-A legal source tables initialized (first run does this automatically)
- pytest installed (dev dependency)
- Internet access to `https://www.gesetze-im-internet.de` for GII tests

---

## Setup

### 1. Start the application

```bash
python -m private_legal_navigator
```

Expected: Server starts on `http://127.0.0.1:8000`

### 2. Register GII source (if not already registered)

This happens automatically on first sync, but can be triggered manually:

```bash
# The source is auto-registered on first sync_gii call
```

---

## Validation Scenarios

### Scenario 1: First-Time Sync (Dry-Run)

**Command:**
```bash
python -m private_legal_navigator sync gii --dry-run
```

**Expected outcome:**
- HTTP client connects to `https://www.gesetze-im-internet.de/gii-toc.xml`
- Catalog is parsed: ~5,000–6,100 items found
- All items classified as NEW (no previous state)
- SyncPlan summary shows: total=N, new=N, unchanged=0, changed=0
- **NO** downloads occur
- **NO** database changes
- Exit code: 0

**Covers:** US3, FR-M7B-007, INV-M7B-02

---

### Scenario 2: First-Time Sync (Apply)

**Command:**
```bash
python -m private_legal_navigator sync gii --apply
```

**Expected outcome:**
- Catalog fetched and parsed
- All NEW items downloaded sequentially
- Progress shown per item: "Downloading BGB...", "Downloading StGB..."
- Each download: SHA-256 hashed, snapshot stored, parsed, indexed in SQLite
- Summary: total=6000, new=6000, failed=0
- SyncRun persisted in database
- `legal_sources.last_catalog_stand_date` updated
- Exit code: 0

**Covers:** US2, FR-M7B-001–006, FR-M7B-009–015

---

### Scenario 3: Idempotent Re-Run (All UNCHANGED)

**Command:**
```bash
# Run immediately after Scenario 2
python -m private_legal_navigator sync gii --dry-run
```

**Expected outcome:**
- Catalog fetched
- catalog_stand_date compared — likely matches last run
- All items classified as UNCHANGED (same catalog, same SHA-256)
- Plan shows: total=6000, unchanged=6000, new=0, changed=0
- If catalog_stand_date matches: "Corpus is up to date" message
- Exit code: 0

**Covers:** US1, INV-M7B-03, INV-M7B-04

---

### Scenario 4: Single Instrument Sync

**Command:**
```bash
python -m private_legal_navigator sync gii --apply --instrument BGB
```

**Expected outcome:**
- Catalog fetched
- Only BGB instrument classified
- If unchanged: one item in plan, UNCHANGED status
- If changed: downloaded and imported
- Summary: total=1, unchanged=1 (or changed=1)
- Exit code: 0

**Covers:** US5, FR-M7B-013

---

### Scenario 5: Catalog-Only Mode

**Command:**
```bash
python -m private_legal_navigator sync gii --catalog-only
```

**Expected outcome:**
- Catalog fetched and displayed
- Catalog metadata shown: stand_date, builddate, total items
- **NO** per-item classification
- **NO** downloads
- Exit code: 0

**Covers:** FR-M7B-017

---

### Scenario 6: Force Sync

**Command:**
```bash
python -m private_legal_navigator sync gii --dry-run --force
```

**Expected outcome:**
- Catalog fetched
- catalog_stand_date gate SKIPPED
- All items classified regardless of stand_date comparison
- "Force mode: catalog_stand_date gate bypassed" warning displayed
- Normal plan summary output
- Exit code: 0

**Covers:** INV-M7B-10

---

### Scenario 7: Sync Status

**Command:**
```bash
python -m private_legal_navigator sync status --last 5
```

**Expected outcome (after at least one sync run):**
- Table with last 5 sync runs
- Columns: Run ID (short), Date, Status, Total, New, Changed, Unchanged, Failed, Duration
- Most recent run first
- Exit code: 0

**Covers:** US6, FR-M7B-017

---

### Scenario 8: Sync Verify

**Command:**
```bash
python -m private_legal_navigator sync verify
```

**Expected outcome:**
- All snapshots in legal_source_snapshots checked against on-disk files
- SHA-256 recomputed and compared with stored hash
- Summary: total=N, verified=N, failed=0, missing=0
- Any failed/missing snapshots listed individually
- Exit code: 0 (all verified) or 1 (some failed)

**Covers:** US7, FR-M7B-018

---

### Scenario 9: Error Handling

**Command (simulate network error):**
```bash
# With network disconnected or invalid URL
python -m private_legal_navigator sync gii --apply
```

**Expected outcome:**
- Catalog download fails
- Error message: "Failed to fetch GII catalog: <reason>"
- No partial sync run created
- Exit code: 1

**Covers:** INV-M7B-15

---

### Scenario 10: Abort and Restart

**Procedure:**
1. Start `sync gii --apply` (first time, many instruments)
2. Interrupt with Ctrl+C during download
3. Run `sync gii --apply` again

**Expected outcome (second run):**
- Catalog fetched
- Already-downloaded instruments detected via SHA-256 dedup
- Remaining instruments (not yet downloaded) classified as NEW
- Only remaining NEW instruments downloaded
- Complete sync with no duplicates

**Covers:** US4, INV-M7B-05

---

## Unit Test Validation

```bash
# Run all tests
pytest --cov=src/private_legal_navigator

# M7-B specific tests (once implemented):
pytest tests/unit/test_sync_run.py -v
pytest tests/unit/test_sync_planning.py -v
pytest tests/unit/test_sync_execution.py -v
pytest tests/integration/test_sync_repository.py -v
pytest tests/api/test_sync_cli.py -v
```

Expected: All tests pass, coverage ≥ 90% for new modules.

---

## Static Analysis

```bash
ruff check src tests
mypy src
pip check
```

Expected: No errors introduced by M7-B code.

---

## Key References

| Artifact | Path | Purpose |
|----------|------|---------|
| Specification | [spec.md](spec.md) | Functional requirements, invariants, user stories |
| Data Model | [data-model.md](data-model.md) | Domain entities, enums, database schema |
| Research | [research.md](research.md) | All 8 research questions answered |
| Plan | [plan.md](plan.md) | Implementation order, Phase 1 + Phase 2 |
| Tasks | [tasks.md](tasks.md) | Task breakdown for all 13 implementation phases |
| CLI Contract | [contracts/sync-cli.md](contracts/sync-cli.md) | CLI interface with all flags |
| Sync Plan Format | [contracts/sync-plan.md](contracts/sync-plan.md) | Dry-run plan output format |
| Sync Result Format | [contracts/sync-result.md](contracts/sync-result.md) | Apply result output format |
| Status Codes | [contracts/status-codes.md](contracts/status-codes.md) | Exit codes and status enum |
| ADR-009 | [docs/architecture/ADR-009-incremental-gii-sync.md](../../docs/architecture/ADR-009-incremental-gii-sync.md) | Architecture decision with rationale |
