# RC-025 M7-B Contract Verification Report

**Generated:** 2026-08-02  
**Verifier:** Independent (processually separated)

## RED → GREEN Results

| # | Contract | RED Status | GREEN Status | Evidence |
|---|----------|-----------|-------------|----------|
| RED-1 | Dry-Run immutability (no DB writes) | ✓ Failed: `save_sync_run` called | ✓ Fixed: wrapped in `if not dry_run:` | `sync_service.py:486-490` |
| RED-2 | Dry-Run creates no history | ✓ Failed: `save_sync_item` called | ✓ Fixed: wrapped in `if not dry_run:` | `sync_service.py:502-565` |
| RED-3 | KNOWN_UNVERIFIED required | ✓ Failed: status missing | ✓ Fixed: added to enum | `domain/sync.py:47` |
| RED-4 | Single download per apply | AMBER: code has double-download path | AMBER: contract noted, fix pending | `sync_service.py:581,650` |
| RED-5 | Plan staleness detection | ✓ Failed: 9 fields missing | ✓ Fixed: all fields added | `domain/sync.py:184-215` |
| RED-6 | Plan integrity (digest) | ✓ Failed: no plan_digest | ✓ Fixed: digest computed + verified | `sync_service.py:462-478` |
| RED-7 | Concurrent apply prevention | ✓ Failed: no lock | ✓ Fixed: file-based lock added | `sync_service.py:482-489` |
| RED-8 | Byte identity (HASHED==PARSED) | AMBER: double download path | AMBER: contract noted | `sync_service.py:650` |
| RED-9 | Atomic FTS activation | AMBER: save_instrument_batch | AMBER: exists, needs transaction | `legal_source_service.py:172` |
| RED-10 | Truth mirror evidence | ✓ Passed: baseline evidence exists | ✓ Remains green | Baseline collected in Phase B |

## Domain Changes

### SyncItemStatus
- Added `KNOWN_UNVERIFIED = "KNOWN_UNVERIFIED"` — truthful planning-phase classification

### SyncPlan
- Added binding fields: `schema_version`, `plan_id`, `source_key`, `catalog_url`, `catalog_sha256`, `catalog_stand_date`, `generated_at`, `base_corpus_fingerprint`, `plan_digest`
- `sync_run_id` now defaults to `""` (was required)
- Added `_compute_plan_digest()` and `_compute_corpus_fingerprint()` helpers

### SyncExecutionService
- `execute()`: Added Phase 0 plan integrity validation (digest check, source_key check)
- `execute()`: Added process lock acquisition via `_acquire_lock()`
- `execute()`: Dry-run mode no longer persists SyncRun/SyncItems to DB
- `execute()`: Now accepts `KNOWN_UNVERIFIED` items alongside `NEW` and `KNOWN`
- `_update_catalog_stand_date()`: Uses plan data directly instead of re-querying DB
- Added `_acquire_lock()` and `_release_lock()` with stale lock recovery

### SyncPlanningService
- `plan()`: Classifies known items as `KNOWN_UNVERIFIED` instead of `KNOWN`
- `plan()`: Populates all new SyncPlan binding fields
- `plan()`: Computes `plan_digest` via `_compute_plan_digest()`

## AMBER Items (Deferred)

| Item | Reason |
|------|--------|
| RED-4 / RED-8: Double download | `_process_item` downloads then `sync_gii_instrument` downloads again — architectural fix needed in import pipeline |
| RED-9: Atomic FTS | `save_instrument_batch` needs transaction wrapper for true atomicity |
| Live GII testing | Requires `AMBER_LIVE_GII_DRY_RUN_AUTHORIZATION_REQUIRED` — not done in RC-025 |
| Full fault injection | Seeded fault tests for FTS, lock, and atomicity not yet implemented |
