# Tasks — M7-B Incremental GII Sync & Corpus Change Management

## Spec Tasks (this run — COMPLETED)

- [x] T001 — Read GitHub Issue #9 (M7-B Specification)
- [x] T002 — Research GII HTTP capabilities (ETag, Last-Modified, catalog structure)
- [x] T003 — Research catalog XML structure and metadata (builddate, stand date)
- [x] T004 — Research delta/changelog interface availability
- [x] T005 — Review existing ADR-007, GiiAdapter, SourceClient code
- [x] T006 — Review existing domain model (legal_source.py) and database schema (database.py)
- [x] T007 — Review existing LegalSourceService for service patterns
- [x] T008 — Constitution check passed (local-only, no background sync, human-gated)
- [x] T009 — User Stories created (7 stories with acceptance criteria)
- [x] T010 — Functional Requirements created (20 FRs)
- [x] T011 — Product Invariants created (18 INVs)
- [x] T012 — Data Integrity Invariants created (10 DI-INVs)
- [x] T013 — State machine designed (SyncItem, SyncRun)
- [x] T014 — Data model designed (SyncRun, SyncItem entities + schema)
- [x] T015 — Plan created (Phase 1 + Phase 2, implementation order)
- [x] T016 — CLI contract designed (sync-cli.md)
- [x] T017 — Sync plan format designed (sync-plan.md)
- [x] T018 — Sync result format designed (sync-result.md)
- [x] T019 — Status codes and exit codes defined (status-codes.md)
- [x] T020 — Security threat model created (security checklist)
- [x] T021 — Data integrity invariants documented (data-integrity checklist)
- [x] T022 — Migration testing checklist created (migration checklist)
- [x] T023 — Accessibility requirements documented (accessibility checklist)
- [x] T024 — Test strategy and coverage requirements defined (testing checklist)
- [x] T025 — Requirements completeness checklist created (requirements checklist)
- [x] T026 — ADR-009 created (docs/architecture/ADR-009-incremental-gii-sync.md)
- [x] T027 — Quickstart guide created (quickstart.md)

---

## Build Tasks (future run)

### Phase 0: Governance (DONE — no code)

### Phase 1: Domain Layer
- [ ] T101 — Create SyncRunStatus enum (PLANNED, IN_PROGRESS, COMPLETED, FAILED, ABORTED)
- [ ] T102 — Create SyncItemStatus enum (PENDING, NEW, CHANGED, UNCHANGED, REMOTE_NOT_MODIFIED, REMOTE_MISSING, SKIPPED, FAILED)
- [ ] T103 — Create SyncRun dataclass with all attributes + invariants
- [ ] T104 — Create SyncItem dataclass with all attributes + invariants
- [ ] T105 — Create SyncPlan value object (frozen dataclass)
- [ ] T106 — Domain unit tests for SyncRun (validation, counters, invariants)
- [ ] T107 — Domain unit tests for SyncItem (state transitions, invariants)
- [ ] T108 — Domain unit tests for SyncPlan (summary, validation)

### Phase 2: Database Migration
- [ ] T201 — Add sync_runs table creation SQL to database.py
- [ ] T202 — Add sync_items table creation SQL to database.py
- [ ] T203 — Add last_catalog_stand_date column migration to legal_sources
- [ ] T204 — Add indexes for sync_runs and sync_items
- [ ] T205 — Integration test: tables created with correct schema
- [ ] T206 — Integration test: FK constraints enforced (CASCADE DELETE)

### Phase 3: Repository Implementation
- [ ] T301 — Create SyncRunRepository ABC (port)
- [ ] T302 — Implement SqliteSyncRunRepository (create_run, update_run, get_run)
- [ ] T303 — Implement SqliteSyncRunRepository (get_last_run, list_runs)
- [ ] T304 — Implement SqliteSyncRunRepository (save_items, get_items_for_run)
- [ ] T305 — Implement SqliteSyncRunRepository (bulk save for items)
- [ ] T306 — Repository integration tests (CRUD, FK, bulk operations)

### Phase 4: SourceClient Enhancement
- [ ] T401 — Create DownloadResult dataclass (content, etag, last_modified, status_code, content_type)
- [ ] T402 — Add `download_with_headers(url) -> DownloadResult` method to SourceClient
- [ ] T403 — Ensure existing `download()` method remains backward-compatible
- [ ] T404 — Update SourceClient tests (include header capture)
- [ ] T405 — Integration test: actual GII download returns ETag and Last-Modified (TEST mode)

### Phase 5: GiiAdapter Enhancement
- [ ] T501 — Create GiiCatalog dataclass (items, stand_date, builddate, sha256, source_key)
- [ ] T502 — Enhance `fetch_catalog()` to extract and return stand_date + builddate + hash
- [ ] T503 — Add `plan_sync(existing_catalog) -> SyncPlan` method to GiiAdapter
- [ ] T504 — Ensure sync_instrument captures ETag/Last-Modified via download_with_headers
- [ ] T505 — Update GiiAdapter unit tests

### Phase 6: Sync Planning Service
- [ ] T601 — Create SyncPlanningService (orchestrates catalog fetch + diff)
- [ ] T602 — Implement catalog presence diff (set comparison O(n))
- [ ] T603 — Implement SHA-256 comparison for KNOWN items
- [ ] T604 — Implement catalog_stand_date gate logic
- [ ] T605 — Generate SyncPlan from diff results
- [ ] T606 — Unit tests for planning service (mocked catalog + repo)

### Phase 7: Sync Execution Service
- [ ] T701 — Create SyncExecutionService (orchestrates selective download)
- [ ] T702 — Implement download loop: only NEW/CHANGED items
- [ ] T703 — Integrate with existing GiiAdapter.sync_instrument() for download + import
- [ ] T704 — Implement progress reporting during download
- [ ] T705 — Implement error handling (per-item FAILED, continue with next)
- [ ] T706 — Implement SyncRun persistence (create run, save items, update status)
- [ ] T707 — Implement summary report generation
- [ ] T708 — Unit + integration tests

### Phase 8: CLI Entry Points
- [ ] T801 — Create CLI module structure (`private_legal_navigator/cli/`)
- [ ] T802 — Implement `pln sync gii [--dry-run|--apply] [--instrument KEY] [--catalog-only] [--force]`
- [ ] T803 — Implement `pln sync status [--source KEY] [--last N]`
- [ ] T804 — Implement `pln sync verify [--source KEY]`
- [ ] T805 — Add CLI configuration and dependency injection
- [ ] T806 — CLI action tests (mocked services)

### Phase 9: UI Status Page Updates
- [ ] T901 — Add sync history to legal sources status page
- [ ] T902 — Show last sync run summary per source
- [ ] T903 — Show last_catalog_stand_date in source detail

### Phase 10: Red Tests Before Implementation
- [ ] R001 — Write failing test: SyncRun entity invariants
- [ ] R002 — Write failing test: SyncItem state machine transitions
- [ ] R003 — Write failing test: SyncPlanningService.catalog_diff()
- [ ] R004 — Write failing test: SourceClient.download_with_headers()
- [ ] R005 — Write failing test: SqliteSyncRunRepository CRUD
- [ ] R006 — Write failing test: SyncExecutionService.selective_download()
- [ ] R007 — Write failing test: CLI entry point parsing

### Phase 11: Integration Tests
- [ ] I001 — Integration test: full dry-run plan (no downloads, no DB changes)
- [ ] I002 — Integration test: full apply run (with test catalog)
- [ ] I003 — Integration test: idempotent re-run (second run = all UNCHANGED)
- [ ] I004 — Integration test: abort + restart (SHA-256 dedup handles partial run)
- [ ] I005 — Integration test: instrument-specific sync
- [ ] I006 — Integration test: catalog-only mode
- [ ] I007 — Integration test: force mode

### Phase 12: E2E Tests
- [ ] E001 — E2E: dry-run against real GII (TEST mode, localhost redirect)
- [ ] E002 — E2E: apply a single instrument
- [ ] E003 — E2E: verify sync history
- [ ] E004 — E2E: verify snapshot integrity after sync

### Phase 13: Documentation + Build
- [ ] D001 — Update README.md with sync CLI documentation
- [ ] D002 — Run full test suite (baseline + new tests)
- [ ] D003 — Verify coverage ≥ 90% for new modules
- [ ] D004 — Ruff check (0 errors)
- [ ] D005 — Mypy check (0 errors)
- [ ] D006 — pip check
- [ ] D007 — Wheel build
