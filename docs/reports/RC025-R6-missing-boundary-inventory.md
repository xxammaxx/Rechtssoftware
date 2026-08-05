# RC-025-R6 Missing Fault Boundary Inventory

**Date:** 2026-08-03
**Base:** RC-025-R5 Fault Injection Reconciliation
**Computed:** 18 total, 11 covered, 7 uncovered

## All 18 Fault Boundaries — Complete Mapping

| ID | Fault Boundary | Code Location | Test | Status |
|----|---------------|---------------|------|--------|
| 1 | Nach Download | `sync_service._process_item:653` (download_verified call) | D1.1 (weak) | COVERED |
| **2** | **Nach Payload-Hash** | `gii_adapter.sync_instrument:310` (after `_write_content_addressed` computes hash) | — | **UNCOVERED** |
| **3** | **Während Snapshot-Tempfile-Schreiben** | `safe_source_client._write_content_addressed:458` (`tmp_file.write_bytes`) | — | **UNCOVERED** |
| **4** | **Nach Tempfile, vor Rename** | `safe_source_client._write_content_addressed` between :458 (write) and :459 (replace) | — | **UNCOVERED** |
| **5** | **Nach Rename, vor Rehash** | `gii_adapter.sync_instrument` between :310 (write+hash) and :313 (cross-validate) | — | **UNCOVERED** |
| **6** | **Nach Snapshot-Rehash** | `gii_adapter.sync_instrument` between :313-319 (cross-validation) and :326 (entity creation) | — | **UNCOVERED** |
| 7 | Während Parse | `gii_adapter._parse_law_xml:399` (XML parse) | D1.7 | COVERED |
| **8** | **Während Normalisierung** | `gii_adapter._normalize_abbreviation:526` / `_extract_metadata:479` | — | **UNCOVERED** |
| 9 | Nach Expression-Insert | `sqlite_legal_source_repository.save_instrument_batch:554-575` | D2.9 | COVERED |
| 10 | Nach Provision-Insert | `sqlite_legal_source_repository.save_instrument_batch:591-611` (within transaction) | D2.11 (implicit) | COVERED |
| 11 | Während FTS-Schreiben | `sqlite_legal_source_repository.save_instrument_batch:613-626` | D2.11 | COVERED |
| 12 | Vor De-Current | `sqlite_legal_source_repository.save_instrument_batch:581-589` | D2.12 | COVERED |
| 13 | Nach De-Current, vor Aktivierung | Within transaction (line 581-589 → commit) | D2.9 (implicit) | COVERED |
| 14 | Nach Aktivierung, vor Commit | Within transaction context manager exit | D2.9+D2.11 (implicit) | COVERED |
| **15** | **Nach Commit, vor Erfolgsrückgabe** | `legal_source_service.sync_gii_instrument:186-218` (between save and return) | — | **UNCOVERED** |
| 16 | Während SyncItem-Finalisierung | `sync_service._process_item:777-783` (save_sync_item) | D3.18 (implicit — retry idempotency) | COVERED |
| 17 | Während SyncRun-Finalisierung | `sync_service.apply:590-606` (update_sync_run) | D3.18 (implicit — retry idempotency) | COVERED |
| 18 | Prozessabbruch nach Commit | DB close/reopen | D3.15 | COVERED |

## Summary

```
18 total
11 covered (6 direct + 3 implicit + 2 retry-implicit)
 7 uncovered
```

## The 7 Uncovered Boundaries — Details

### #2: Nach Payload-Hash
**Where:** `gii_adapter.sync_instrument:310` — `_write_content_addressed()` returns `(path, sha256)`.
**Risk:** If the hash is computed but snapshot entity creation fails, the content-addressed file exists on disk but no DB record references it.
**Injection:** Fault between `_write_content_addressed` return and `SourceSnapshot` entity creation (line 326).

### #3: Während Snapshot-Tempfile-Schreiben
**Where:** `_write_content_addressed:458` — `tmp_file.write_bytes(content)`.
**Risk:** I/O error during write. Tempfile may contain partial data. Cleanup in except block (line 462) should handle this.
**Injection:** Simulate disk full / I/O error during `write_bytes`.

### #4: Nach Tempfile, vor Rename
**Where:** Between `tmp_file.write_bytes` (:458) and `tmp_file.replace(target_path)` (:459) in `_write_content_addressed`.
**Risk:** Tempfile exists but rename hasn't happened yet. Crash at this point leaves orphan tempfile.
**Injection:** Fault between write and rename — tempfile should not be confused with completed file.

### #5: Nach Rename, vor Rehash
**Where:** Between `_write_content_addressed` return (:310) and cross-validation (:313) in `sync_instrument`.
**Risk:** File is at final path with correct hash, but cross-validation hasn't confirmed payload.sha256 == snapshot hash yet. If payload bytes were somehow mutated between download and here, the mismatch should be caught.
**Injection:** Inject hash mismatch at this point — should raise SNAPSHOT_INTEGRITY_FAILED.

### #6: Nach Snapshot-Rehash
**Where:** Between cross-validation (:313-319) and SourceSnapshot entity creation (:326) in `sync_instrument`.
**Risk:** Hash is verified but DB entity creation fails before snapshot record is written. Content-addressed file exists orphaned on disk.
**Injection:** Fault after hash verification, before DB snapshot insert.

### #8: Während Normalisierung
**Where:** `_normalize_abbreviation:526` / `_extract_metadata:479` during `_parse_law_xml`.
**Risk:** Normalization failure during parse — should not leave partial DB records.
**Injection:** Fault during abbreviation normalization — DB should be untouched (normalization happens before any DB write).

### #15: Nach Commit, vor Erfolgsrückgabe
**Where:** `legal_source_service.sync_gii_instrument:186-218` — between `save_instrument_batch` commit and `return parsed`.
**Risk:** Commit succeeded but caller crashes before returning success. On retry, should detect the already-committed state and not duplicate.
**Injection:** Simulate crash after commit but before SyncItem/SyncRun finalization. Retry should find existing data.
