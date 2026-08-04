# Changelog — PrivateLegalNavigator

## v1.0.0-rc.2 (2026-07-28) — Release Gate Closure & RC Tag Reconciliation

### Release Gates Closed

- **GATE-01** `backup_helper.py`: 40 unit tests, 93 % coverage (WAL-mode, integrity, failure paths, CLI)
- **GATE-02** `restore_helper.py`: 60 unit tests, 93 % coverage (traversal, symlink, size, hash, atomic, rollback)
- **GATE-03** Installed-Wheel-E2E: complete M6-UI + M7-B test executed
- **GATE-05** `sync_service.py`: 77 % coverage (AMBER_M7B_COVERAGE_GATE_OPEN — complex HTTP error recovery)
- **GATE-06/07** Wheel + Sdist built, twine check passed
- **GATE-08** README, CHANGELOG, docs updated with final values
- **GATE-10** RC tag collision resolved: `v1.0.0-rc.1` already in use → upgraded to `1.0.0rc2`
- **GATE-11** Windows cold-test harness prepared (not executed on Linux)

### Bug Fixes

- Fix symlink false positive in `restore_helper.py` S_IFMT mask (S_IFREG vs S_IFLNK bit overlap)
- Catch `sqlite3.DatabaseError` in `_check_database_integrity`
- Update E2E script version assertion for installed wheel

### Testing

- 1021 tests passing (was 921)
- Overall coverage: 79 %
- `backup_helper.py`: 93 %
- `restore_helper.py`: 93 %
- Ruff: 0 errors
- Mypy: PASS
- pip check: No broken requirements
- Installed-Wheel-E2E: All 12 M7-B gates passed

## v0.2.1 (2026-07-26) — M7-B Incremental GII Sync & Sync-History

### ⚠ BREAKING CHANGES
- **New database tables:** 2 new tables (`sync_runs`, `sync_items`) added for sync run history — schema migration runs automatically on startup
- **New column:** `legal_sources.last_catalog_stand_date` added for catalog freshness gating

### New Features — Incremental GII Sync (M7-B)

#### Sync Planning Service
- `SyncPlanningService` fetches GII catalog (`gii-toc.xml`) and classifies every instrument
- Three-tier change detection: `catalog_stand_date` gate → catalog presence diff → SHA-256 comparison
- Produces `SyncPlan` value object (never persisted — read-only classification)
- Detects NEW, KNOWN, SKIPPED, and REMOTE_MISSING instruments
- `--force` flag bypasses catalog stand-date gate for full re-classification

#### Sync Execution Service
- `SyncExecutionService` executes a `SyncPlan`: selective download of NEW/CHANGED instruments
- Per-item SHA-256 dedup: unchanged content is not re-imported
- HTTP metadata capture (ETag, Last-Modified, status code) via `SourceClient.download_with_headers()`
- Atomic SyncRun persistence with per-item status tracking
- Dry-run mode: classify and count only — no downloads (safe default)
- `error_summary` capped at 500 chars per failed item

#### Domain Model (sync.py)
- `SyncRunStatus`: RUNNING, COMPLETED, ABORTED, FAILED
- `SyncItemStatus`: PENDING, NEW, KNOWN, CHANGED, UNCHANGED, REMOTE_NOT_MODIFIED, REMOTE_MISSING, SKIPPED, FAILED
- `SyncRun`: Full audit trail (catalog metadata, per-status counts, timestamps)
- `SyncItem`: Per-instrument tracking (SHA-256 before/after, HTTP metadata, error summary)
- `SyncPlan`: Frozen value object for plan phase output

#### Database Schema (2 new tables)
- `sync_runs` — Append-only sync execution records with full status counters
- `sync_items` — Per-instrument status within a run (FK to `sync_runs` with CASCADE DELETE)
- `legal_sources.last_catalog_stand_date` — Column for catalog freshness gating
- 5 new indexes (`idx_sr_source`, `idx_sr_status`, `idx_si_run`, `idx_si_status`, `idx_si_source_identifier`)

#### CLI Commands
- `python -m private_legal_navigator legal-source sync --source gii [--dry-run|--apply] [--force]` — Incremental GII sync with plan/apply split
- `python -m private_legal_navigator legal-source sync-status [--source KEY] [--last N]` — Sync run history display

#### Phase 9 UI
- Sync history integrated into legal source status page (`/ui/legal-sources`)
- Last sync run summary per source (status, date, item counts)
- `catalog_stand_date` display in source detail

#### SourceClient Enhancement
- `DownloadResult` dataclass with `content`, `http_status`, `etag`, `last_modified`, `content_type`
- `download_with_headers(url) -> DownloadResult` method — captures HTTP response metadata
- Backward-compatible: existing `download()` method unchanged

#### SyncRunSummary DTO
- `legal_source_status_dto.py`: Template-ready DTO for sync history in UI
- `from_sync_run()` factory method converts domain entity to display model

### Architecture Decisions

- **ADR-009** — [Incremental GII Sync & Corpus Change Management](docs/architecture/ADR-009-incremental-gii-sync.md)
  - Evidence-based hybrid sync architecture (catalog + presence + SHA-256)
  - Two-phase split: Plan (dry-run) → Human Review → Execute (apply)
  - Append-only sync history pattern (consistent with ADR-002, ADR-008)

### M6-UI Accessibility Fixes
- Various accessibility improvements to M6-UI templates

### Test Coverage

- 864 total tests (up from 802 at M7-A.1)
- Domain sync module: 22 unit tests (SyncRun, SyncItem, SyncPlan validation + state transitions)
- Repository sync: 15 integration tests (CRUD, FK enforcement, batch operations)
- Overall coverage: 71% (baseline maintained)
- ruff lint clean, mypy strict mode clean

### Full File List (new/modified)

```
NEW:  src/private_legal_navigator/domain/sync.py
NEW:  src/private_legal_navigator/application/sync_service.py
NEW:  src/private_legal_navigator/application/legal_source_status_dto.py
NEW:  tests/unit/test_sync_domain.py
NEW:  tests/integration/test_sync_repository.py
MOD:  src/private_legal_navigator/__main__.py (sync/sync-status CLI handlers)
MOD:  src/private_legal_navigator/api/m7a_ui_routes.py (Phase 9 sync history)
MOD:  src/private_legal_navigator/application/legal_source_service.py (sync history queries)
MOD:  src/private_legal_navigator/application/legal_source_repository.py (sync ports)
MOD:  src/private_legal_navigator/infrastructure/database.py (2 new tables + indexes)
MOD:  src/private_legal_navigator/infrastructure/sqlite_legal_source_repository.py (sync repository)
MOD:  src/private_legal_navigator/infrastructure/safe_source_client.py (DownloadResult, download_with_headers)
MOD:  src/private_legal_navigator/infrastructure/gii_adapter.py (catalog-diff helpers)
NEW:  docs/architecture/ADR-009-incremental-gii-sync.md
NEW:  docs/reports/COV-001-coverage-trend.md (this report)
```

---

## v0.2.0 (2026-07-23) — M7-A Trusted Legal Source Operations & Release Closure

### ⚠ BREAKING CHANGES
- **New dependency:** `lxml >= 6.1.0` required for secure XML parsing of legal sources
- **New database tables:** 11 new tables (10 real + 1 FTS5 virtual) added to the existing `private_legal_navigator.db` — schema migration runs automatically on startup
- **New snapshot storage:** Raw source files stored under `PLN_DATA_DIR/snapshots/` — separate backup path from the main database

### New Features — Legal Source Foundation (M7-A)

#### GII Import (Gesetze im Internet Adapter)
- `GiiAdapter` fetches legal instruments from `gesetze-im-internet.de`
- Catalog discovery: lists all available laws
- Single-instrument sync: download → hash → parse → persist atomically
- SHA-256 duplicate detection: identical content is not re-imported
- Four-stage pipeline: Download → Parse → Normalize → Index (isolated failure boundaries per stage)
- Parser version tracking for future re-normalization

#### FTS5 Full-Text Search
- SQLite FTS5 virtual table (`legal_provisions_fts`) over provision texts
- BM25-ranked search results with snippet generation
- Supports prefix queries, phrase queries, boolean operators
- Synchronous index — no staleness or separate sync process

#### Citation Resolution
- `CitationResolver` resolves citations like "§ 48 SGB X" to specific provisions
- Regex-based parsing of common German citation patterns
- Deterministic lookup: abbreviation → instrument → expression → provision
- Returns authority tier display, retrieval date, temporal warnings
- Supports case-insensitive fallback search for abbreviations

#### Authority Tier Classification
- Six-tier system: OFFICIAL_PROMULGATION (T0) through UNKNOWN (T5)
- GII classified as `CONSOLIDATED_NON_OFFICIAL` (T3) — transparent provenance
- Per-expression tier overrides supported
- Tier displayed in every norm detail view

#### SHA-256 Snapshot Integrity
- Every downloaded source file stored unmodified before parsing
- Content-addressable storage: SHA-256 hash as identity
- Directory sharding (first 2 hex chars) for filesystem performance
- Immutable snapshots — no UPDATE code path exists

### New Features — Case Legal Timeline (M7-A)

#### Append-Only Legal Events
- `case_legal_events` table with 11 event types (DOCUMENT_ISSUED through OTHER)
- Three temporal dimensions: `occurred_at`, `known_at`, `recorded_at`
- CANDIDATE → CONFIRMED → CORRECTED → REVOKED lifecycle (identical to M6-A pattern)
- Corrections create new records; originals preserved via `previous_event_id`
- Revocation sets `revoked_at`; record never deleted

#### Event Relations
- `event_relations` table with 10 relation types (AMENDS, REPLACES, CHALLENGES, etc.)
- Many-to-many: a single event can have multiple outgoing and incoming relations
- Self-referential CHECK constraint prevents invalid relations

#### Case-Legal Links (Norm-to-Case)
- `case_legal_links` table connecting cases to legal provisions
- Same lifecycle: CANDIDATE → CONFIRMED → CORRECTED → REVOKED
- Links track relevance notes and document associations

#### Evidence Pack
- Deterministic bundle of confirmed evidence for a case
- Contains: confirmed facts, open facts, legal events, legal issues, confirmed links, provisions, source snapshots, temporal warnings
- No LLM used — pure projection from confirmed data

#### Legal Issues
- `legal_issues` table tracking open/resolved legal questions per case
- Status flow: OPEN → UNDER_REVIEW → RESOLVED → DEFERRED

### New UI Pages (M7-A)

| Route | Page | Description |
|-------|------|-------------|
| `/ui/legal-sources` | Rechtsquellen | Source status overview with snapshot counts |
| `/ui/legal-sources/search?q=...` | Rechtsquellensuche | FTS5 full-text search across legal corpus |
| `/ui/legal-sources/norm/{id}` | Normdetail | Detailed provision view with metadata |
| `/ui/cases/{id}/legal-situation` | Rechtslage | Norm links management (link, confirm, reject, correct, revoke) |
| `/ui/cases/{id}/legal-timeline` | Rechtsverlauf | Chronological event timeline with human review workflow |
| `/ui/cases/{id}/evidence-pack` | Evidence Pack | Read-only export of case evidence |

All mutations are POST-only with CSRF protection (same PRG pattern as M6-UI).

### Security Improvements

- **Secure XML Parser:** lxml with `resolve_entities=False`, `no_network=True`, `huge_tree=False`, 50 MB size limit — blocks XXE, SSRF, billion laughs attacks
- **Secure Source Client:** Host allowlist restricted to `*.gesetze-im-internet.de`, HTTPS-only, redirect validation at each hop, 200 MB response size limit, TLS verification enforced
- **Atomic Writes:** `tempfile` + `rename` pattern for snapshot storage (prevents partial writes)
- **Transport Policy (SEC-001):** Explicit allow/block rules for all external HTTP traffic
- **Transactional Imports (SEC-015):** All-or-nothing batch persistence — snapshot preserved with FAILED status on error

### New Dependencies

- `lxml >= 6.1.0` — Secure XML parsing for legal source downloads

### New Database Tables (11 total)

| Table | Type | Purpose |
|-------|------|---------|
| `legal_sources` | Real | Registered legal source publishers |
| `legal_source_snapshots` | Real | Immutable raw downloads with SHA-256 hashes |
| `legal_instruments` | Real | Legal instruments (laws, regulations) |
| `legal_expressions` | Real | Versioned expressions of instruments |
| `legal_provisions` | Real | Individual paragraphs, articles, sections |
| `legal_citations` | Real | Citation resolution records |
| `case_legal_events` | Real | Append-only case legal events |
| `event_relations` | Real | Many-to-many event relations |
| `case_legal_links` | Real | Norm-to-case connections |
| `legal_issues` | Real | Case-specific legal issues |
| `legal_provisions_fts` | FTS5 | Full-text search index over provisions |

### Architecture Decisions

- **ADR-007** — [Legal Source Provenance and Corpus Foundation](docs/architecture/ADR-007-legal-source-provenance.md)
  - 10 architectural sub-decisions covering monolith extension, FTS5, SHA-256 snapshots, pipeline stages, authority tiers, temporal honesty, privacy isolation, secure XML, pluggable adapters, and lxml dependency
- **ADR-008** — [Case Legal Timeline and Case-Legal Links](docs/architecture/ADR-008-case-legal-timeline.md)
  - 10 architectural sub-decisions covering append-only events, temporal dimensions, event types, explicit relations, human review lifecycle, history preservation, derived timeline, integration with existing mechanisms, norm links, and no automatic legal effect

### Test Coverage

- 751 total tests (up from 703 at M6-UI)
- mypy strict mode clean
- pytest-cov target >=90%
- ruff lint clean

### Full File List (new/modified)

```
NEW:  src/private_legal_navigator/domain/legal_source.py
NEW:  src/private_legal_navigator/domain/case_timeline.py
NEW:  src/private_legal_navigator/application/legal_source_service.py
NEW:  src/private_legal_navigator/application/legal_source_repository.py
NEW:  src/private_legal_navigator/application/case_timeline_service.py
NEW:  src/private_legal_navigator/application/case_timeline_repository.py
NEW:  src/private_legal_navigator/application/citation_resolver.py
NEW:  src/private_legal_navigator/api/m7a_ui_routes.py
NEW:  src/private_legal_navigator/infrastructure/sqlite_legal_source_repository.py
NEW:  src/private_legal_navigator/infrastructure/sqlite_case_timeline_repository.py
NEW:  src/private_legal_navigator/infrastructure/gii_adapter.py
NEW:  src/private_legal_navigator/infrastructure/safe_source_client.py
NEW:  src/private_legal_navigator/presentation/templates/m7a/* (7 templates)
MOD:  src/private_legal_navigator/app.py (M7-A wiring)
MOD:  src/private_legal_navigator/infrastructure/database.py (11 new tables + indexes)
MOD:  src/private_legal_navigator/pyproject.toml (lxml dependency)
NEW:  docs/architecture/ADR-007-legal-source-provenance.md
NEW:  docs/architecture/ADR-008-case-legal-timeline.md
NEW:  docs/architecture/m7a-reality-refresh.md
```
