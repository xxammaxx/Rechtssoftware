# RC-025-R1 Byte Flow Map — F4 Single Download & Byte Identity

**Generated:** 2026-08-02 | **Branch:** fix/rc025-r1-m7b-integrity-closure

## Current Data Flow (Broken)

```
SyncPlanningService.plan()
  ── _fetch_catalog_with_metadata()
       └─ SourceClient.download(GII_CATALOG_URL)          ← CATALOG DOWNLOAD #1
       └─ compute_sha256(raw_bytes) → catalog_sha256
       └─ parse_xml_bytes(raw_bytes) → catalog items
  ── _build_local_index() → {sid: {sha256, instrument_id, ...}}
  ── Returns SyncPlan (no instrument downloads)

SyncExecutionService.execute(plan, dry_run)
  ── Phase 0: Plan integrity, lock acquisition
  ── Phase A: save_sync_run()                              ← SEPARATE TX
  ── Phase B: For each item:
       └─ _process_item(item, now)
            ── SourceClient.download_with_headers(sid)     ← INSTRUMENT DOWNLOAD #1
                 Returns DownloadResult(content=bytes, http_status, etag, ...)
            ── compute_sha256(download_result.content)     ← HASH FROM DL#1
            ── item.new_sha256 = computed_sha256
            ── LegalSourceService.sync_gii_instrument(abbrev)
                 └─ GiiAdapter.find_in_catalog(key)
                      └─ GiiAdapter.fetch_catalog()
                           └─ SourceClient.download(CATALOG_URL)  ← CATALOG DOWNLOAD #2
                 └─ GiiAdapter.sync_instrument(item)
                      └─ SourceClient.download(law_url)    ← INSTRUMENT DOWNLOAD #2
                      └─ _extract_xml_from_zip_bytes()     ← MAY MUTATE BYTES
                      └─ _write_content_addressed(xml_bytes)
                           └─ compute_sha256(xml_bytes)    ← HASH FROM DL#2
                      └─ _parse_law_xml(xml_bytes)         ← PARSES DL#2 BYTES
                      └─ Returns GiiParsedInstrument(snapshot, instrument, expression, provisions)
                 └─ save_instrument_batch()                ← ATOMIC TX
                      └─ INSERT snapshot (with DL#2 hash)
                      └─ INSERT instrument
                      └─ INSERT expression (temporal_status=CURRENT)
                      └─ INSERT provisions
                      └─ DELETE+INSERT FTS (rebuild)
            ── item.snapshot_id = parsed.snapshot.snapshot_id
            ── save_sync_item(item)                         ← SEPARATE TX
  ── Phase C: update_sync_run()                             ← SEPARATE TX
  ── Phase D: update_legal_source_catalog_stand_date()      ← SEPARATE TX
```

## Critical Violations Found

### F4.1: Double Download of Instrument Bytes
**Lines:** sync_service.py:650 (DL#1), gii_adapter.py:271 (DL#2)

The instrument XML is downloaded TWICE:
1. In `_process_item()` via `download_with_headers()` — hashed, then bytes DISCARDED
2. In `sync_gii_instrument → sync_instrument()` via `download()` — bytes used for import

**Risk:** DL#1 and DL#2 can return different bytes (race condition, server-side update between requests).

### F4.2: Mismatched Hash Truths
**Lines:** sync_service.py:690 (hash from DL#1), gii_adapter.py:290 (hash from DL#2)

- `item.new_sha256` = SHA-256 of DL#1 content
- `snapshot.sha256` = SHA-256 of DL#2 content (after potential ZIP extraction)
- These two hashes are NEVER compared!
- The saved snapshot bytes are DL#2, but the sync item records DL#1's hash.

### F4.3: Byte Mutation During Import
**Lines:** gii_adapter.py:274-277

If the GII serves a ZIP archive, `_extract_xml_from_zip_bytes()` extracts the XML from the ZIP. The raw downloaded bytes (ZIP) are DIFFERENT from the parsed bytes (XML). The hash is computed from the extracted XML bytes, not the raw download.

### F4.4: Re-fetched Catalog
**Lines:** sync_service.py:308 (Catalog DL#1), gii_adapter.py:207 (Catalog DL#2)

`find_in_catalog()` calls `fetch_catalog()` which downloads the full GII catalog AGAIN. This was already downloaded during planning.

### F4.5: No Content Integrity Verification
**Lines:** gii_adapter.py:290

`_write_content_addressed()` computes the hash during write, but the written file is never re-read and verified against the expected hash.

### F6.1: No Atomic Transaction Boundary
**Lines:** sync_service.py:498-610

The execution phase uses FIVE separate database transactions:
1. `save_sync_run()` — own connection + commit
2. `save_instrument_batch()` — transactional but per-item
3. `save_sync_item()` — own connection + commit (per item!)
4. `update_sync_run()` — own connection + commit
5. `update_legal_source_catalog_stand_date()` — own connection + commit

**Risk:** If the process crashes after step 3 but before step 5, the database is in an inconsistent state.

### F6.2: FTS Rebuild Is Destructive
**Lines:** sqlite_legal_source_repository.py:599-607

Each `save_instrument_batch` call DELETES ALL FTS rows and rebuilds from `legal_provisions`. The DELETE+INSERT is in a transaction, but if the rebuild fails, ALL FTS data is lost — not just the new instrument's data.

### F6.3: No "Current Expression" Gate
**Lines:** sqlite_legal_source_repository.py:401-411

The current expression is resolved by `temporal_status = 'CURRENT' ORDER BY valid_from DESC LIMIT 1`. When a new expression is inserted with `temporal_status=CURRENT`, it immediately becomes visible — there's no staged/unstaged mechanism.

## Required Architecture Changes

### To Fix F4 (Byte Identity):
1. Introduce `VerifiedSourcePayload` — immutable download artifact
2. Download exactly ONCE per instrument per sync run
3. SHA-256 computed ONCE from downloaded bytes
4. Same bytes object passed through: download → hash → snapshot → parse → verify
5. Snapshot file re-hashed after write, compared against payload hash
6. Cross-validate: `payload.sha256 == snapshot.sha256 == file_hash`

### To Fix F6 (Atomic Activation):
1. File operations FIRST (snapshot write → fsync → hash verify)
2. Database operations in ONE transaction:
   - All inserts (snapshot, instrument, expression, provisions, FTS)
   - Old expression de-current (temporal_status → 'SUPERSEDED')
   - New expression set as current
   - Sync item finalization
3. On failure: old state remains visible, new data never exposed
4. FTS: use incremental insert instead of DELETE+INSERT rebuild
