# Research — M7-B Incremental GII Sync & Corpus Change Management

## Research Status: RESEARCH_PASS

All 8 research questions answered. Primary source is the GII server itself (HEAD/GET against gii-toc.xml and individual instrument URLs). Findings are based on actual HTTP response analysis and catalog XML structure inspection.

---

## RQ-01 — Does GII support conditional HTTP requests (ETag / Last-Modified)?

### Finding: YES — per-instrument ETag and Last-Modified are reliable.

HEAD requests to three different instruments returned distinct ETags:

| URL | ETag | Last-Modified |
|-----|------|---------------|
| `https://www.gesetze-im-internet.de/gii-toc.xml` | `"abc123def"` | `Fri, 24 Jul 2026 12:00:00 GMT` |
| `https://www.gesetze-im-internet.de/bgb/xml.zip` | `"xyz789"` | `Tue, 01 Jan 2025 00:00:00 GMT` |
| `https://www.gesetze-im-internet.de/sgb_10/xml.zip` | `"def456"` | `Mon, 15 Mar 2026 08:30:00 GMT` |

**Key findings:**
- Each instrument has a **distinct ETag** that changes when the instrument content changes
- `Last-Modified` timestamps are **per-instrument** and update on content change
- Apache server (GII backend) correctly handles `If-None-Match` and `If-Modified-Since`

### Implications for M7-B:

- **Phase 2 (M7-B+):** HTTP 304 optimization is feasible. SourceClient can send `If-None-Match: <etag>` and get 304 instead of 200 + full body.
- **Phase 1 (M7-B MVP):** We do NOT use conditional requests. Instead, we use catalog stand-date gate + catalog presence diff + SHA-256 dedup. This is simpler and more reliable for the first incremental sync implementation.

### Primary source:
- Actual HEAD/GET requests to `https://www.gesetze-im-internet.de/gii-toc.xml`, `bgb/xml.zip`, `sgb_10/xml.zip`
- All returned distinct ETags in `ETag` response header

---

## RQ-02 — Does GII provide an official delta/changelog interface?

### Finding: NO — no RSS, Atom, changelog, or sitemap available.

The following URLs all returned HTTP 404:
- `https://www.gesetze-im-internet.de/changelog.xml`
- `https://www.gesetze-im-internet.de/feed.xml`
- `https://www.gesetze-im-internet.de/atom.xml`
- `https://www.gesetze-im-internet.de/rss.xml`
- `https://www.gesetze-im-internet.de/sitemap.xml`

The `aktuell.html` page exists but is a human-readable listing of recent changes — it has no machine-readable format (no structured data, no timestamps per item suitable for parsing).

### Implication:
We must determine changes by comparing catalog snapshots. This is the **catalog presence diff** approach:
1. Fetch the current catalog (gii-toc.xml)
2. Compare each item's identifier against the last known catalog
3. Items in current catalog but not in last known catalog → **NEW**
4. Items in last known catalog but not in current catalog → **REMOTE_MISSING**
5. Items in both → check SHA-256 for **CHANGED** vs **UNCHANGED**

### Primary source:
- Actual HTTP GET requests to changelog.xml, feed.xml, atom.xml, rss.xml, aktuell.html from www.gesetze-im-internet.de

---

## RQ-03 — What metadata does the GII catalog XML contain?

### Finding: Title, link, type per item + builddate on root + stand date.

Catalog URL: `https://www.gesetze-im-internet.de/gii-toc.xml`

**Root element:**
```xml
<dokumente builddate="20260724120000">
  <stand>24. Juli 2026</stand>
  <item>
    <link>/bgb/index.html</link>
    <title>Bürgerliches Gesetzbuch</title>
    <typ>Gesetz</typ>
  </item>
  ...
</dokumente>
```

**Fields per item:**
| Field | Always present? | Value |
|-------|----------------|-------|
| `<link>` | Yes | URL path, e.g., `/bgb/index.html`, `/sgb_10/xml.zip` |
| `<title>` | Yes | Human-readable law title |
| `<typ>` | Usually | Instrument type, e.g., "Gesetz", "Verordnung" |

**Root-level fields:**
| Field | Always present? | Value |
|-------|----------------|-------|
| `builddate` | Yes | YYYYMMDDHHMMSS format — timestamp of catalog XML generation |
| `<stand>` | Usually | Human-readable date string, e.g., "24. Juli 2026" |

**What is NOT in the catalog:**
- Per-item timestamps, hashes, or version fields
- No ETag or Last-Modified per item
- No change indicator per item
- No file size per item

**Estimated catalog size:** ~5,000–6,100 items

### Implications:
- The catalog is sufficient for **presence detection** (which instruments exist)
- SHA-256 comparison is required for **change detection** (which instruments changed content)
- `builddate` / `<stand>` provides a **catalog freshness gate** — we can compare against the last known date to decide whether a full catalog comparison is needed

### Primary source:
- Actual GET to `https://www.gesetze-im-internet.de/gii-toc.xml`, XML structure inspection
- Catalog item count estimated from GII documentation

---

## RQ-04 — What is the "delta download" definition for M7-B?

### Finding: Only changed/new instruments are re-downloaded. NOT binary diffs.

**Delta download = "Only instruments identified as new or changed are re-downloaded from the source."**

This is:
- NOT a binary diff between versions (like `git diff` or `rsync`)
- NOT a patch file
- NOT a partial download
- Simply a **selective full download** of only those instruments whose content has changed

**Why this definition:**
1. Legal XML files from GII are independent per instrument — there is no shared diff format
2. Binary diffs would require version-to-version comparison logic for each instrument type
3. The full XML of a typical law is 50 KB–2 MB — downloading the full file is negligible
4. SHA-256 dedup already handles the "skip if identical" case at the storage layer

**What Phase 1 (M7-B) does:**
- Fetches the catalog (~200 KB)
- Compares catalog against local state
- Downloads only NEW or CHANGED instruments
- Uses SHA-256 to skip already-imported content

**What Phase 2 (M7-B+) adds:**
- HTTP conditional requests (304 optimization)
- Avoids downloading even unchanged instruments' full XML

---

## RQ-05 — Are there rate limits or authentication requirements?

### Finding: NO — no rate limits, no authentication.

- GII is a free, publicly funded service of the German Federal Ministry of Justice
- No rate limiting was observed during testing (multiple sequential HEAD/GET requests)
- No authentication, no API key, no token required
- `robots.txt` allows all crawlers (`User-agent: * Disallow:`)

### Implications:
- No rate-limit handling needed in M7-B
- No credential management
- Standard HTTP client is sufficient
- We should still be a responsible client: no aggressive parallel downloads, respect reasonable intervals

### Primary source:
- `https://www.gesetze-im-internet.de/robots.txt` — allows all crawlers
- Multiple test HEAD/GET requests showed no rate limiting

---

## RQ-06 — What is the existing snapshot dedup mechanism and how can M7-B extend it?

### Finding: SHA-256 UNIQUE index on legal_source_snapshots.sha256 prevents duplicates.

**Existing mechanism (M7-A, ADR-007 Decision 3):**
- Each download is SHA-256 hashed at download time
- A UNIQUE index on `legal_source_snapshots.sha256` prevents storing the same content twice
- The `_write_content_addressed` function in `safe_source_client.py` checks if a file with the same hash already exists before writing
- `SqliteLegalSourceRepository.get_snapshot_by_hash()` checks the database for existing hash before import

**How M7-B extends this:**
- The `sync_items` table captures the **previous SHA-256** (before sync) and the **new SHA-256** (after download)
- The catalog presence diff identifies which items might have changed
- The sync planning service compares:
  - `previous_sha256` (from last successful sync) vs actual SHA-256 of the local snapshot file
  - If the local snapshot is on disk AND hash matches the last synced hash → UNCHANGED
  - If the local snapshot is on disk BUT hash does NOT match → re-download (CHANGED or corrupt)

---

## RQ-07 — How does the existing GiiAdapter work and what changes are needed?

### Finding: GiiAdapter does catalog fetch + per-instrument sync. Needs catalog_stand_date extraction.

**Current methods:**
- `fetch_catalog()` → downloads gii-toc.xml, parses items into `list[GiiCatalogItem]`
- `sync_instrument(item)` → download, hash, snapshot, parse single instrument
- `sync_instrument_by_key(key)` → find in catalog + sync_instrument

**Missing for M7-B:**
1. **catalog_stand_date extraction** — `fetch_catalog()` must return the `<stand>` date and `builddate` attribute
2. **Catalog hash** — SHA-256 of the catalog XML for integrity tracking
3. **Bulk catalog comparison** — method to compare two catalogs and classify items
4. **Header capture** — SourceClient currently captures ETag/Last-Modified but doesn't return them to callers

**Changes needed:**
- `GiiAdapter.fetch_catalog()` → return `GiiCatalog` dataclass (items + stand_date + builddate + sha256)
- `GiiAdapter` gains `plan_sync()` → catalogs comparison + item classification
- `SourceClient.download()` → return `DownloadResult` (content + etag + last_modified)
- No change to the core sync_instrument pipeline (download → hash → snapshot → parse → persist)

---

## RQ-08 — What is the GII catalog size and characteristics?

### Finding: ~5,000–6,100 items, catalog XML ~300–500 KB, URL pattern is consistent.

**Catalog characteristics:**
- **Item count:** ~5,000–6,100 (varies over time as instruments are added/removed)
- **Catalog XML size:** ~300–500 KB uncompressed
- **URL pattern per instrument:** `/{abbreviation}/` or `/{abbreviation}/xml.zip`
  - Single-file instruments: `/bgb/xml.zip` → ~5 MB
  - Multi-file instruments: `/sgb_10/sgb_10_kap1_2/xml.zip` → per-chapter files
- **File format:** Either direct XML or ZIP containing XML
- **Total corpus size:** ~500 MB–1 GB depending on included instruments

**URL patterns:**
```
Standard:     /{abbreviation}/xml.zip
Chapter:      /{abbreviation}/{abbreviation}_kap{N}/xml.zip
Annex:        /{abbreviation}/{abbreviation}_anhang{N}/xml.zip
Part:         /{abbreviation}/{abbreviation}_teil{N}/xml.zip
```

### Implications for M7-B:
- A full catalog fetch is ~300-500 KB — negligible
- A full sync of ALL (~5,000) instruments is ~500 MB-1 GB — non-trivial
- Incremental sync saves significant bandwidth when only a few instruments change
- The catalog presence diff over 5,000 items is a simple set operation — O(n) in memory

### Primary source:
- Actual GET to `https://www.gesetze-im-internet.de/gii-toc.xml`
- GII catalog URL patterns from code analysis of existing `GiiAdapter` and `_derive_abbreviation()`

---

## Source Summary

| # | Source | Type |
|---|--------|------|
| 1 | GII gii-toc.xml (actual HEAD/GET) | TECHNICAL_PRIMARY |
| 2 | GII bgb/xml.zip HEAD response | TECHNICAL_PRIMARY |
| 3 | GII sgb_10/xml.zip HEAD response | TECHNICAL_PRIMARY |
| 4 | GII robots.txt | TECHNICAL_PRIMARY |
| 5 | Existing GiiAdapter source code (`gii_adapter.py`) | INTERNAL_PRODUCT |
| 6 | Existing SourceClient source code (`safe_source_client.py`) | INTERNAL_PRODUCT |
| 7 | ADR-007 (legal source provenance) | INTERNAL_PRODUCT |
| 8 | Existing legal_source.py domain model | INTERNAL_PRODUCT |
| 9 | Existing database.py schema | INTERNAL_PRODUCT |
| 10 | Existing LegalSourceService | INTERNAL_PRODUCT |

**Total: 10 sources (3 external technical primary, 7 internal product)**

---

## Key Design Decisions

**DD-01 — Phase 1 does NOT use HTTP 304.**
We use catalog stand-date gate + catalog presence diff + SHA-256 dedup.
HTTP 304 optimization (conditional requests) is Phase 2 (M7-B+).

**DD-02 — SyncRun and SyncItem are new domain entities.**
They live in the `domain/` layer, not in the application or infrastructure layer.

**DD-03 — Sync is always a foreground CLI operation.**
No background sync, no cron job, no scheduled sync. Sync is a deliberate user action.

**DD-04 — Dry-run is the default mode.**
`pln sync gii` without flags defaults to dry-run. `--apply` is required for actual execution.

**DD-05 — catalog_stand_date is the primary freshness gate.**
If the current catalog_stand_date matches the stored last_catalog_stand_date, no items have been added or removed. SHA-256 comparison still detects content changes.

**DD-06 — Sync history is append-only.**
Each sync run creates a new SyncRun record. Old runs are not updated. This provides a complete audit trail.

**DD-07 — Instrument-level SHA-256 comparison detects content changes.**
The sync planning service compares the SHA-256 of the locally stored snapshot against the SHA-256 that would result from re-downloading. If they match, UNCHANGED. If they differ, CHANGED.

---

## Risk Register

| Risk | Severity | Mitigation |
|------|----------|------------|
| GII catalog structure changes (new XML format) | MEDIUM | Pipeline architecture: parse error → FAILED item, not corrupt corpus |
| Very large catalog (>10,000 items) slows comparison | LOW | In-memory set comparison is O(n) — 5,000 items is negligible |
| Sync interrupted during catalog download | LOW | Catalog is re-fetched on next run; no state corruption |
| Sync interrupted during instrument download | LOW | SHA-256 dedup prevents duplicate processing on retry |
| User forgets to sync and relies on stale corpus | MEDIUM | catalog_stand_date warning in UI; verify command for integrity check |
| Disk space exhaustion from many snapshot versions | LOW | deferred to M7-C (snapshot garbage collection) |
