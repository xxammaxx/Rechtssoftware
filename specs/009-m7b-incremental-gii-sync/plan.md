# Plan — M7-B Incremental GII Sync & Corpus Change Management

## Overview

This plan maps the M7-B specification to an implementation strategy with two phases. Phase 1 (M7-B MVP) is the primary implementation target. Phase 2 (M7-B+) is a documented optimization path.

## Architecture Decision

**Variant D: Evidence-Based Hybrid (Selected)**

The sync pipeline uses three evidence sources in priority order:

| Priority | Evidence Source | What It Detects | Cost |
|----------|----------------|-----------------|------|
| 1 (cheapest) | Catalog Stand-Date | Whether catalog metadata has changed | ~300 KB download |
| 2 | Catalog Presence Diff | Which items were added/removed | O(n) set comparison |
| 3 | SHA-256 Dedup | Whether content actually changed | Local file hash |
| 4 (Phase 2) | HTTP ETag/304 | Whether remote content unchanged | ~1 KB HEAD request |

**Why not Variant A (Catalog-Only):** Catalog has no per-item hashes or timestamps — impossible to detect content changes from catalog alone.

**Why not Variant B (Always-Download):** This is the M7-A full sync approach — wastes bandwidth.

**Why not Variant C (HTTP-Conditional Only):** Requires per-instrument HEAD requests (~5,000 requests) which is acceptable but not needed for Phase 1.

**Phase 1 (M7-B MVP) uses Evidence 1 + 2 + 3. Phase 2 (M7-B+) adds Evidence 4.**

---

## Two-Phase Approach

### Phase 1: M7-B MVP (This Implementation)

```
catalog_stand_date gate → catalog presence diff → SHA-256 comparison → selective download
```

1. Fetch GII catalog (gii-toc.xml)
2. Check catalog_stand_date against last known value
3. Compare catalog items against local state (by source_identifier)
4. Classify each item: NEW, CHANGED, UNCHANGED, REMOTE_MISSING
5. For CHANGED: compare SHA-256 of local snapshot against hash at last sync
6. Download only NEW and verified-CHANGED items
7. Import via existing M7-A pipeline (SHA-256 dedup, atomic batch commit)

### Phase 2: M7-B+ (Future Optimization)

```
Phase 1 + HTTP conditional request layer
```

1. Before downloading a NEW/CHANGED instrument, send HEAD with If-None-Match / If-Modified-Since
2. If server returns 304, mark as REMOTE_NOT_MODIFIED (skip download)
3. If server returns 200, proceed with download as before
4. Requires SourceClient enhancement to capture and send ETag/Last-Modified headers

---

## Affected Layers

| Layer | Changes | Type |
|-------|---------|------|
| **Domain** | New entities: SyncRun, SyncItem, SyncRunStatus, SyncItemStatus | New file: `sync_run.py` in domain/ |
| **Application** | New services: SyncPlanningService, SyncExecutionService; modified: LegalSourceService (delegation) | New files + edits |
| **Infrastructure** | New repository: SqliteSyncRunRepository; modified: SourceClient (header capture), GiiAdapter (catalog stand date extraction) | New file + edits |
| **API** | New CLI entry points (pln sync gii, pln sync status, pln sync verify) | New CLI module |
| **Presentation** | UI status page updates (add sync history) | Edits to Jinja2 template |
| **Database** | New tables: sync_runs, sync_items; new column: legal_sources.last_catalog_stand_date | Migration |

## No Changes To

| Area | Rationale |
|------|-----------|
| M7-A domain entities (LegalSource, SourceSnapshot, etc.) | Extended via new sync entities, not modified |
| M7-A pipeline (download → hash → snapshot → parse → persist) | Reused as-is for instrument download |
| Citation resolution | Unchanged |
| FTS5 search | Unchanged |
| Case-related code | Isolation maintained (ADR-007 Decision 7) |
| pyproject.toml | No new dependencies |
| Existing API routes | Unchanged |

---

## Dependency Graph

```
User (CLI)
  │
  ▼
SyncCli (pln sync ...)
  │
  ├──► SyncPlanningService
  │     ├── GiiAdapter.fetch_catalog() → GiiCatalog (items + stand_date + sha256)
  │     ├── SyncRunRepository.get_last_catalog() → last catalog state
  │     └── CatalogDiffEngine.compare() → dict[source_identifier, SyncItemStatus]
  │
  └──► SyncExecutionService
        ├── SyncPlanningService.plan (reuse for classification)
        ├── GiiAdapter.sync_instrument() for NEW/CHANGED items
        ├── SyncRunRepository.save_run() to persist results
        └── LegalSourceRepository.update_catalog_stand_date()
```

---

## Implementation Order

1. **Domain layer** — SyncRun, SyncItem entities + enums
2. **Database migration** — sync_runs, sync_items tables + last_catalog_stand_date column
3. **SourceClient enhancement** — Header capture (ETag, Last-Modified → DownloadResult)
4. **GiiAdapter enhancement** — Catalog stand_date extraction, GiiCatalog dataclass
5. **SyncRunRepository** — SQLite implementation for sync history
6. **SyncPlanningService** — Catalog diff, state classification, plan generation
7. **SyncExecutionService** — Selective download, hash compare, import orchestration
8. **CLI entry points** — pln sync gii, pln sync status, pln sync verify
9. **UI updates** — Sync history display on legal sources status page
10. **Tests** — Unit, integration, e2e (see testing checklist)

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| GII catalog XML format changes | Low | Medium | Pipeline architecture isolates parser; FAILED item, not corrupt corpus |
| SHA-256 collision (theoretical) | Negligible | High | Use SHA-256 (not MD5); collision is cryptographically impractical |
| User interrupts sync mid-download | Medium | Low | SHA-256 dedup prevents re-processing; atomic writes prevent partial snapshots |
| catalog_stand_date not updated on GII side despite content changes | Low | Medium | Force mode (`--force`) bypasses date gate; SHA-256 comparison still detects |
| Very slow sync due to many changed items | Low | Low | CLI shows progress per item; background processing not needed |
| Disk space exhaustion | Low | Medium | Snapshot cleanup deferred to M7-C |
| User runs multiple concurrent syncs | Low | Low | Rejected: single-user, foreground operation |

---

## Phase 2 (M7-B+) Design Sketch

**Not for implementation in Phase 1.** Forward-looking sketch for HTTP conditional request layer:

```python
# In SourceClient (Phase 2 enhancement):
class DownloadResult:
    content: bytes
    etag: str
    last_modified: str

def conditional_download(self, url: str, etag: str, last_modified: str) -> DownloadResult | None:
    """Download with conditional headers. Returns None if 304 (not modified)."""
    headers = {}
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified
    response = self._get_with_headers(url, headers)
    if response.status_code == 304:
        return None  # Not modified
    return DownloadResult(content=response.content, etag=response.headers.get("etag", ""), ...)
```

Sync planning would then:
1. For CHANGED items with known ETag: try conditional download first
2. If 304: mark REMOTE_NOT_MODIFIED (source unchanged despite SHA-256 mismatch — local corruption detected!)
3. If 200: proceed with normal download

---

## References

- [Spec](spec.md) — Full specification with user stories, acceptance criteria, invariants
- [Data Model](data-model.md) — Schema, entities, state machine
- [ADR-007](docs/architecture/ADR-007-legal-source-provenance.md) — Legal Source Provenance
- [Tasks](tasks.md) — Atomic task breakdown
- [Sync CLI Contract](contracts/sync-cli.md) — CLI interface contract
- [Status Codes](contracts/status-codes.md) — Exit codes and status enum
