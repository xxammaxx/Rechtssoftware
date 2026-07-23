# Changelog — PrivateLegalNavigator

## v0.2.0-rc (2026-07-23) — M7-A Legal Source Foundation + Case Legal Timeline

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
