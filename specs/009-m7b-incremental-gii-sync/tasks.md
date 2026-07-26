# Tasks — M7-B Incremental GII Sync & Corpus Change Management

**Status (2026-07-26):** Spec-Phase (T001-T027) vollständig. Build-Phasen 1-10: Code existiert mit Abweichungen. Tests: 37 neue Tests (Domain + Integration). Phase 9: implementiert. Phase 10: Red Tests (teilweise) — siehe Phasen-Details. Phasen 11-13: noch offen (geplant).

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
- [x] T101 — Create SyncRunStatus enum (RUNNING, COMPLETED, ABORTED, FAILED) — existiert (abweichend von Spec PLANNED/IN_PROGRESS)
- [x] T102 — Create SyncItemStatus enum (PENDING, NEW, KNOWN, CHANGED, UNCHANGED, ...) — existiert (+KNOWN)
- [x] T103 — Create SyncRun dataclass — existiert (domain/sync.py)
- [x] T104 — Create SyncItem dataclass — existiert (domain/sync.py)
- [x] T105 — Create SyncPlan value object — existiert (domain/sync.py)
- [x] T106 — Domain unit tests for SyncRun (fields, validation) — existiert (tests/unit/test_sync_domain.py, 22 Tests)
- [x] T107 — Domain unit tests for SyncItem (state transitions) — existiert (tests/unit/test_sync_domain.py)
- [x] T108 — Domain unit tests for SyncPlan (summary, validation) — existiert (tests/unit/test_sync_domain.py)

### Phase 2: Database Migration
- [x] T201 — Add sync_runs table creation SQL to database.py — existiert
- [x] T202 — Add sync_items table creation SQL to database.py — existiert
- [x] T203 — Add last_catalog_stand_date column migration — existiert
- [x] T204 — Add indexes for sync_runs and sync_items — existiert (M7B_INDEXES)
- [x] T205 — Integration test: tables created by initialize_schema() — existiert (test_sync_repository.py)
- [x] T206 — Integration test: FK constraints enforced (CASCADE DELETE) — existiert (test_sync_repository.py)

### Phase 3: Repository Implementation
- [x] T301 — Create SyncRunRepository ABC (port) — existiert (Teil von LegalSourceRepository ABC)
- [x] T302 — Implement create_run, update_run, get_run — existiert (sqlite_legal_source_repository.py)
- [x] T303 — Implement list_runs(limit=N) — hinzugefügt 2026-07-25
- [x] T304 — Implement get_items_for_run() — hinzugefügt 2026-07-25
- [x] T305 — Implement save_sync_items_batch() — existiert (executemany)
- [x] T306 — Repository integration tests — existiert (test_sync_repository.py, 15 Tests)

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
- [x] T901 — Add sync history to legal sources status page
- [x] T902 — Show last sync run summary per source
- [x] T903 — Show last_catalog_stand_date in source detail

### Phase 10: Red Tests Before Implementation
- [x] R001 — Write failing test: SyncRun entity invariants → existiert (test_sync_domain.py, 22 Tests)
- [x] R002 — Write failing test: SyncItem state machine transitions → existiert (test_sync_domain.py)
- [ ] R003 — Write failing test: SyncPlanningService.catalog_diff() — offen (Phase 11)
- [ ] R004 — Write failing test: SourceClient.download_with_headers() — offen (Phase 11)
- [x] R005 — Write failing test: SqliteSyncRunRepository CRUD → existiert (test_sync_repository.py, 15 Tests)
- [ ] R006 — Write failing test: SyncExecutionService.selective_download() — offen (Phase 11)
- [ ] R007 — Write failing test: CLI entry point parsing — offen (Phase 12)

### Phase 11: Integration Tests (geplant)
- [ ] I001 — Integration test: full dry-run plan (no downloads, no DB changes)
- [ ] I002 — Integration test: full apply run (with test catalog)
- [ ] I003 — Integration test: idempotent re-run (second run = all UNCHANGED)
- [ ] I004 — Integration test: abort + restart (SHA-256 dedup handles partial run)
- [ ] I005 — Integration test: instrument-specific sync
- [ ] I006 — Integration test: catalog-only mode
- [ ] I007 — Integration test: force mode

### Phase 12: E2E Tests (geplant)
- [ ] E001 — E2E: dry-run against real GII (TEST mode, localhost redirect)
- [ ] E002 — E2E: apply a single instrument
- [ ] E003 — E2E: verify sync history
- [ ] E004 — E2E: verify snapshot integrity after sync

### Phase 13: Documentation + Build
- [x] D001 — Update README.md with sync CLI documentation — DONE (docs-agent, 2026-07-26)
- [ ] D002 — Run full test suite (baseline + new tests) — siehe COV-001-Trendreport (864 Tests, 71% Coverage)
- [ ] D003 — Verify coverage ≥ 90% for new modules — domain/sync.py (91%) ✓, sync_service.py (0%) ✗
- [x] D004 — Ruff check (0 errors) — DONE (linter clean)
- [x] D005 — Mypy check (0 errors) — DONE (type-check clean)
- [ ] D006 — pip check — offen
- [ ] D007 — Wheel build — offen
