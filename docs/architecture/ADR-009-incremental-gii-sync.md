# ADR-009 — Incremental GII Sync & Corpus Change Management (M7-B)

**Status:** Accepted

**Date:** 2026-07-25

**Deciders:** Architecture Agent (ADR-009)

## Context

M7-A (ADR-007) established the legal source foundation: a full GII corpus download with
SHA-256 snapshot integrity, FTS5 full-text search, and citation resolution. The M7-A
`GiiAdapter.sync_instrument()` performs a **full re-download** of every instrument to
detect changes — all ~5,000–6,100 catalog items are downloaded unconditionally, regardless
of whether their content has changed since the last sync.

M7-B must extend this foundation with **incremental sync capability**: a catalog-based
change detection layer that identifies new, changed, and unchanged instruments before
downloading, reducing bandwidth, time, and server load.

**Key constraints from existing architecture:**

| Source | Constraint |
|--------|-----------|
| ADR-001 | Modular monolith — all sync code extends existing layers |
| ADR-007 Decision 1 | No microservices — SQLite is the single database |
| ADR-007 Decision 3 | Immutable SHA-256 snapshots — content-addressable storage |
| ADR-007 Decision 4 | Pipeline stages: Download → Parse → Normalize → Index |
| ADR-007 Decision 7 | Strict isolation — no case data during sync |
| ADR-007 Decision 8 | Secure XML parsing (lxml, XXE protection) |
| ADR-007 Decision 9 | Pluggable adapter pattern — GiiAdapter enhanced, not replaced |
| Project constitution | Local-only, no background sync, human-gated operations |

**What the GII catalog provides (research findings):**

- `gii-toc.xml`: A single XML file (~300 KB) listing all instruments with abbreviation,
  title, and a per-instrument `builddate`
- A `<stand>` date in the catalog root indicating when the catalog metadata was last updated
- **No** per-item content hashes in the catalog
- **No** per-item `Last-Modified` timestamps
- HTTP `ETag` and `Last-Modified` headers are available per-instrument download (not per-catalog)

**Core architectural tension:** The catalog tells us *what exists* (instrument presence/absence),
but not *what changed* (content changes). Content change detection requires either (a) downloading
every item and comparing SHA-256 hashes (full download, M7-A approach), or (b) sending per-item
conditional HTTP requests (5,000+ HEAD requests). Neither extreme is ideal.

---

## Decision

We implement an **Evidence-Based Hybrid Sync Architecture** (Variant D) with two phases,
using four evidence sources in priority order:

| Priority | Evidence Source | What It Detects | Cost |
|----------|----------------|-----------------|------|
| 1 (cheapest) | `catalog_stand_date` | Whether catalog metadata has changed | ~300 KB (one catalog fetch) |
| 2 | Catalog Presence Diff | Which items were added/removed (set comparison, O(n)) | In-memory |
| 3 | SHA-256 Content Dedup | Whether local content actually matches remote | Local file hash lookup |
| 4 (Phase 2) | HTTP ETag / 304 | Whether remote content unchanged (conditional request) | ~1 KB per item HEAD |

### Phase 1 (M7-B MVP): Evidence Sources 1 + 2 + 3

```
catalog_stand_date gate → catalog presence diff → SHA-256 comparison → selective download
```

1. Fetch GII catalog (`gii-toc.xml`)
2. Compare `catalog_stand_date` against `legal_sources.last_catalog_stand_date` — skip if unchanged and `--force` not set
3. Perform catalog presence diff: compare catalog item set against locally known instruments (by `source_identifier`)
4. Classify each item: `NEW` (in catalog, not local), `KNOWN` (in both), `REMOTE_MISSING` (local, not in catalog)
5. For `KNOWN` items: compare SHA-256 of the local snapshot against the SHA-256 from the last sync — if unchanged, classify as `UNCHANGED`; if different, classify as `CHANGED`
6. Download only `NEW` and `CHANGED` items via the existing M7-A pipeline (Download → Hash → Snapshot → Parse → Normalize → Index)
7. Skip `UNCHANGED` items entirely

### Phase 2 (M7-B+, Future): Add Evidence Source 4

Phase 2 adds HTTP conditional requests (`If-None-Match` / `If-Modified-Since`) before
downloading `NEW`/`CHANGED` instruments. If the server returns `304 Not Modified`, the
item is classified as `REMOTE_NOT_MODIFIED` and the download is skipped. This requires
the `SourceClient.download_with_headers()` enhancement (capturing and sending
`ETag`/`Last-Modified`), which is implemented in Phase 1 infrastructure but only
actively used for optimization in Phase 2.

### New Domain Entities

Two new entities in `domain/sync_run.py`:

1. **`SyncRun`** — A single execution of the sync pipeline (plan + optional apply).
   - Attributes: `run_id`, `source_key`, `started_at`, `completed_at`, `catalog_stand_date`,
     `catalog_url`, `catalog_sha256`, per-status item counts, `status` (PLANNED/IN_PROGRESS/
     COMPLETED/FAILED/ABORTED), `dry_run`, `error_summary`
   - Lifecycle: `PLANNED → IN_PROGRESS → COMPLETED | FAILED | ABORTED`

2. **`SyncItem`** — One instrument's status within a `SyncRun`. One `SyncItem` per
   catalog item per run.
   - Attributes: `item_id`, `run_id` (FK), `source_identifier`, `abbreviation`, `title`,
     `item_status` (enum: PENDING/NEW/CHANGED/UNCHANGED/REMOTE_NOT_MODIFIED/REMOTE_MISSING/
     SKIPPED/FAILED), `previous_sha256`, `new_sha256`, `snapshot_id` (FK), `instrument_id`
     (FK), HTTP metadata, `error_summary`
   - State machine: `PENDING → NEW | CHANGED | UNCHANGED | REMOTE_NOT_MODIFIED |
     REMOTE_MISSING | SKIPPED | FAILED`

Both entities follow the append-only pattern established in ADR-002 and ADR-008:
`sync_items` are inserted once and never updated (except for status transitions within a
single run). Deleted runs cascade to their items.

### Sync Pipeline — Two-Phase Split

The key architectural innovation is splitting sync into two phases with a mandatory
human gate:

| Phase | Operation | Mutations | Persisted? |
|-------|-----------|-----------|-----------|
| **Plan** (always) | Fetch catalog, diff, classify, produce `SyncPlan` | None | No (dry-run default) |
| **Execute** (--apply) | Download NEW/CHANGED items, import via M7-A pipeline | Database + filesystem | Yes |

**Critical invariant (INV-M7B-01):** No direct "apply without plan" path exists. The
plan must always be computed and displayed before execution can proceed.

### CLI Interface

```
pln sync gii [--dry-run|--apply] [--instrument KEY] [--catalog-only] [--force]
pln sync status [--source KEY] [--last N]
pln sync verify [--source KEY]
```

- `--dry-run` is the default (safe by default)
- `--apply` requires explicit user intent
- `--force` bypasses the `catalog_stand_date` gate but preserves SHA-256 dedup
- `--instrument KEY` enables targeted single-instrument sync

### Database Schema Extension

| Change | Table/Column | Purpose |
|--------|-------------|---------|
| New table | `sync_runs` | Records each sync execution (metadata, counts, status) |
| New table | `sync_items` | Per-instrument status within a run (1 row per item per run) |
| New column | `legal_sources.last_catalog_stand_date` | Tracks the last seen catalog `<stand>` date for freshness gating |

All M7-A tables (`legal_sources`, `legal_instruments`, `legal_expressions`,
`legal_provisions`, `legal_source_snapshots`, `legal_citations`) remain unchanged.

### Service Architecture

| Layer | Component | Role |
|-------|-----------|------|
| **Domain** | `sync_run.py` | `SyncRun`, `SyncItem`, `SyncRunStatus`, `SyncItemStatus`, `SyncPlan` (frozen value object) |
| **Application** | `SyncPlanningService` | Orchestrates catalog fetch + diff + classification → produces `SyncPlan` |
| **Application** | `SyncExecutionService` | Executes the plan: selective download via `GiiAdapter`, imports, persists `SyncRun` |
| **Infrastructure** | `SourceClient` (enhanced) | New `download_with_headers()` returns `DownloadResult` (content + ETag + Last-Modified) |
| **Infrastructure** | `GiiAdapter` (enhanced) | `fetch_catalog()` now returns `GiiCatalog` (items + stand_date + sha256) |
| **Infrastructure** | `SqliteSyncRunRepository` | Persists `SyncRun` and `SyncItem` entities |
| **API** | CLI module (`cli/`) | `pln sync` subcommands |

---

## Alternatives Considered

### Alternative A: Catalog-Only Diff (Rejected)

**Approach:** Detect changes solely from the GII catalog XML, without examining
actual instrument content.

| Pros | Cons |
|------|------|
| Simplest implementation — one catalog fetch | Catalog has **no** per-item content hashes |
| No per-instrument HTTP requests during plan phase | Catalog has **no** per-item modification timestamps |
| Very fast plan phase | Cannot detect content changes for items already known locally |
| | Only detects additions and removals, not modifications |
| | Would miss all content updates — instruments silently drift out of date |

**Rejected:** The GII catalog metadata simply does not contain the information needed
for content change detection. A catalog-only approach would give false confidence in
corpus freshness.

### Alternative B: Full Re-Download Every Time (M7-A Approach, Rejected as M7-B default)

**Approach:** Continue downloading all ~5,000–6,100 instruments on every sync — the
current M7-A behavior.

| Pros | Cons |
|------|------|
| No additional code — reuse M7-A pipeline as-is | Downloads ~500+ MB every sync, regardless of actual changes |
| Guaranteed correctness — no diff logic to get wrong | ~5,000 HTTP GET requests per sync |
| Simple mental model — always a full corpus refresh | Most items (typically >95%) are unchanged between syncs |
| | Unnecessary server load on GII infrastructure |
| | Sync takes minutes instead of seconds |

**Rejected as default, preserved as fallback.** Full re-download remains available
via `--force`, but must not be the only option. The M7-A pipeline is reused for
individual instrument downloads within M7-B — only the *decision* of which items
to download is new.

### Alternative C: HTTP Conditional Requests Only (Deferred to Phase 2)

**Approach:** Send `If-None-Match` / `If-Modified-Since` headers for every instrument
to determine if content has changed, without a catalog-level diff.

| Pros | Cons |
|------|------|
| Leverages HTTP protocol semantics correctly | Requires ~5,000 HEAD/GET requests even when catalog unchanged |
| Server returns 304 for unchanged items — no body transfer | Catalog-level changes (added/removed items) invisible — must still fetch catalog |
| ETag comparison is simpler than SHA-256 (no local hash needed) | Requires storing ETag/Last-Modified per instrument from previous sync |
| | No standalone plan phase — the "plan" is the 5,000 requests themselves |

**Deferred, not rejected.** The HTTP conditional request layer is explicitly designed as
Phase 2 (M7-B+). The Phase 1 implementation already captures ETag and Last-Modified
headers (`SourceClient.download_with_headers()` returns `DownloadResult`) — this data
is stored in `sync_items` and will be available for Phase 2 conditional requests.
Phase 2 is implemented when per-instrument HTTP overhead becomes the dominant cost,
which is unlikely until corpus size exceeds ~10,000 instruments or sync frequency
reaches daily.

### Alternative D: Evidence-Based Hybrid (Selected — Variant D)

**Approach:** Combine catalog-level metadata, set-based presence diff, and SHA-256
content comparison in a multi-tier evidence hierarchy. (See Decision section above.)

| Pros | Cons |
|------|------|
| Fast plan phase: 1 catalog fetch + in-memory set comparison | More complex than any single-source approach |
| Only downloads instruments that actually changed | Requires maintaining SHA-256 history from previous sync |
| Graceful degradation: each tier provides partial information | Requires new domain entities (SyncRun, SyncItem) for tracking |
| Phase 1 already captures data needed for Phase 2 optimization | Two-phase split requires discipline (no plan-skipping shortcuts) |
| SHA-256 dedup prevents re-processing interrupted syncs | |

**Selected.** This approach correctly answers the core question: "How do we detect
what changed when the catalog doesn't tell us?" The answer is a layered evidence
model where cheap checks gate expensive ones, and SHA-256 is the ultimate content
integrity anchor (consistent with ADR-007 Decision 3).

---

## Consequences

### Positive

1. **Sync speed improvement:** A typical no-change sync goes from ~5,000 downloads and
   several minutes (M7-A full sync) to 1 catalog fetch (~300 KB) + in-memory O(n) set
   comparison (<1 second for plan phase). Only when instruments actually change are
   downloads triggered.

2. **Safe-by-default CLI:** Dry-run is the default. `--apply` must be explicit. The
   two-phase split (plan → human review → apply) mirrors the confirmation workflow
   pattern from ADR-002 and ADR-003.

3. **Resilience to interruption:** SHA-256 content-addressable snapshots (ADR-007
   Decision 3) ensure that a partially downloaded sync can be resumed: the next run
   detects the existing snapshots by hash and skips re-download. No transaction
   rollback complexity.

4. **Reuses M7-A pipeline unchanged:** The existing GII adapter's `sync_instrument()`
   method (download → hash → snapshot → parse → normalize → index) is called for
   each NEW/CHANGED item — no modification to the import pipeline. The M7-B layer
   is purely about *selecting which items to feed* to the pipeline.

5. **Auditable sync history:** The append-only `sync_runs` + `sync_items` tables
   provide a complete, immutable record of every sync operation — what was detected,
   what was downloaded, what failed, and the SHA-256 state before and after.

6. **Phase 2 path is paved:** `SourceClient.download_with_headers()` and the
   `http_etag`/`http_last_modified` columns in `sync_items` are implemented in
   Phase 1. When HTTP conditional requests become the optimization target, the
   data is already being collected.

7. **Instrument-targeted sync:** `--instrument KEY` allows updating a single
   instrument (e.g., after a known amendment) without a full catalog scan.

### Negative

1. **New domain complexity:** Two new entities (`SyncRun`, `SyncItem`) with state
   machines and a new repository (`SqliteSyncRunRepository`). Adds ~500 lines of
   domain/repository code and two new database tables.

2. **SHA-256 history dependency:** The sync planner must access the SHA-256 hash
   of the most recent snapshot for each instrument. This requires either a new
   query pattern (joining `sync_items` with `legal_source_snapshots`) or storing
   the last-known SHA-256 in `legal_instruments`. The design uses `sync_items`
   from the last successful run.

3. **catalog_stand_date gate risks false negatives:** If GII updates instrument
   content without updating the catalog `<stand>` date (which has been observed),
   the catalog date gate would incorrectly skip the sync. Mitigation: `--force`
   bypasses the date gate and falls through to SHA-256 comparison.

4. **No snapshot garbage collection yet:** Superseded snapshots (from instrument
   updates) accumulate on disk. Snapshot cleanup is deferred to M7-C. Disk usage
   for a typical corpus with monthly syncs is estimated at ~1-2 GB/year — acceptable
   for now, but needs a retention policy.

5. **Catalog format brittleness:** The GII catalog XML format has changed in the
   past. If the `<stand>` element or the per-item structure changes, the catalog
   parser must be updated. The pipeline architecture isolates this (parse failures
   become FAILED items, not corrupted corpus), but maintenance is required.

### Neutral

1. **Sync is foreground-only:** Sync remains a user-initiated CLI operation — no
   background daemon, no scheduled cron job, no automatic trigger on application
   start. This is a constitutional constraint (local-only, no background processing)
   and matches the project's human-gated operation model. It means the user must
   remember to sync, but this is acceptable for the target audience (individual
   legal self-help, not enterprise document management).

2. **CLI is the primary sync interface:** The UI status page shows sync history
   but does not trigger syncs. This separation of concerns (CLI for operations,
   UI for review) is consistent with the project's design philosophy. A future
   UI sync trigger button is possible but not in M7-B scope.

3. **No cross-source sync orchestration:** M7-B handles only GII. If multiple
   sources are registered (e.g., future BGBl and EUR-Lex adapters), each must
   be synced individually (`pln sync gii`, `pln sync bgbl`, etc.). A
   `pln sync all` command is deferred to a future milestone.

4. **FTS5 index is synchronous:** When instruments are re-imported (updated
   provisions), FTS5 automatically reflects the new content because we use the
   `content=` parameter pointing to `legal_provisions`. No separate index rebuild
   step is needed.

---

## References

- [ADR-007 — Legal Source Provenance and Corpus Foundation](ADR-007-legal-source-provenance.md) — M7-A foundation; Decisions 1, 3, 4, 7, 8, 9 directly constrain M7-B
- [ADR-008 — Case Legal Timeline and Case-Legal Links](ADR-008-case-legal-timeline.md) — Append-only state machine pattern reused in M7-B
- [ADR-002 — Confirmed Reference Events](adr-002-confirmed-reference-events.md) — Original append-only confirmation pattern
- [ADR-001 — Local Modular Monolith](adr-001-local-modular-monolith.md) — Layer architecture
- [M7-B Spec](../specs/009-m7b-incremental-gii-sync/spec.md) — Full specification with user stories, invariants, state machine
- [M7-B Plan](../specs/009-m7b-incremental-gii-sync/plan.md) — Implementation strategy, phase split, risk assessment
- [M7-B Data Model](../specs/009-m7b-incremental-gii-sync/data-model.md) — Schema, entities, repository ports
- [M7-B Tasks](../specs/009-m7b-incremental-gii-sync/tasks.md) — Atomic task breakdown (13 phases)
- [Sync CLI Contract](../specs/009-m7b-incremental-gii-sync/contracts/sync-cli.md)
- [Sync Status Codes](../specs/009-m7b-incremental-gii-sync/contracts/status-codes.md)
- [Security Checklist](../specs/009-m7b-incremental-gii-sync/checklists/security.md)
- [Project Constitution](../../.specify/memory/constitution.md)
