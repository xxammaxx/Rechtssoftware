# Status Codes and Enums — M7-B Incremental GII Sync

## Exit Codes (CLI)

| Code | Name | Meaning |
|------|------|---------|
| 0 | SUCCESS | Operation completed successfully. For apply: all items processed. For dry-run: plan created. For status: history displayed. For verify: all checks passed. |
| 1 | PARTIAL_FAILURE | Some items failed but overall run completed. At least one item has FAILED status. |
| 2 | FATAL_ERROR | Operation could not start or complete due to a system error (network failure, catalog parse error, database error). |
| 3 | INVALID_ARGS | Invalid command-line arguments (unknown flag, missing value, mutually exclusive flags). |
| 4 | CONFLICT | Sync already in progress (concurrent run detected). |
| 5 | VERIFY_FAILED | Sync verify found integrity violations (hash mismatches, missing snapshots). |

---

## SyncRun States

| State | Value | Meaning |
|-------|-------|---------|
| PLANNED | `PLANNED` | Plan completed, not yet applied. |
| IN_PROGRESS | `IN_PROGRESS` | Currently executing apply phase. |
| COMPLETED | `COMPLETED` | All items processed successfully. |
| FAILED | `FAILED` | All items processed, but some or all failed. |
| ABORTED | `ABORTED` | User interrupted (Ctrl+C) or system error. |

**Transitions:**
```
PLANNED ──► IN_PROGRESS ──► COMPLETED
  │                            │
  └──► (never applied)        └──► FAILED
                                   │
                                   └──► ABORTED
```

---

## SyncItem States

| State | Value | Meaning | Download? |
|-------|-------|---------|-----------|
| PENDING | `PENDING` | Initial state before classification. | N/A |
| NEW | `NEW` | In catalog, not in local corpus. | YES (if apply) |
| CHANGED | `CHANGED` | In both catalog and local, but SHA-256 differs. | YES (if apply) |
| UNCHANGED | `UNCHANGED` | In both catalog and local, SHA-256 matches. | NO |
| REMOTE_NOT_MODIFIED | `REMOTE_NOT_MODIFIED` | HTTP 304 response (Phase 2 only). | NO |
| REMOTE_MISSING | `REMOTE_MISSING` | In local corpus but not in current catalog. | NO (cannot download) |
| SKIPPED | `SKIPPED` | Skipped due to filter (--instrument, --catalog-only). | NO |
| FAILED | `FAILED` | Download or import failed. | Attempted |

**Transitions:**
```
PENDING ──► NEW ──► FAILED (download failed)
PENDING ──► CHANGED ──► FAILED (download/import failed)
PENDING ──► UNCHANGED
PENDING ──► REMOTE_NOT_MODIFIED (Phase 2)
PENDING ──► REMOTE_MISSING
PENDING ──► SKIPPED
```

**State transition constraints:**
- PENDING is the only valid initial state
- No transition from a terminal state (COMPLETED, FAILED, REMOTE_MISSING) to another state within the same SyncRun
- RETRY is modeled as a NEW SyncRun (append-only)

---

## Warning Codes

| Code | Context | Meaning |
|------|---------|---------|
| `CATALOG_FRESH` | Plan | Catalog stand date is newer than last known. |
| `CATALOG_STALE` | Plan | Catalog stand date matches last known. |
| `REMOTE_MISSING_ITEMS` | Plan/Result | Some local instruments are no longer in the catalog. |
| `FORCE_MODE_ACTIVE` | Plan | --force flag bypassed stand-date gate. |
| `INSTRUMENT_NOT_FOUND` | Plan | --instrument key not found in catalog. |
| `SOME_ITEMS_FAILED` | Result | Some items could not be processed. |
| `DOWNLOAD_FAILED` | Result | Network error during download. |
| `IMPORT_FAILED` | Result | Parse or database error during import. |
| `SHA256_MISMATCH` | Result | Downloaded content hash differs from expected. |
| `NO_CHANGES` | Result | No new or changed items found. |
| `NO_PREVIOUS_SYNC` | Plan | First sync — no previous state to compare. |
| `SYNC_IN_PROGRESS` | Plan/Result | A concurrent sync operation exists. |
| `HTTP_304_UNEXPECTED` | Result | Server returned 304 for an instrument without prior ETag. (Phase 2) |

---

## SyncRun Counter Fields

The following integer counters on SyncRun track item distribution:

| Field | Type | Description |
|-------|------|-------------|
| `total_items` | int | Total number of items in the catalog at sync time |
| `new_count` | int | Number of items classified as NEW |
| `changed_count` | int | Number of items classified as CHANGED |
| `unchanged_count` | int | Number of items classified as UNCHANGED |
| `remote_not_modified_count` | int | Number of items returning HTTP 304 (Phase 2) |
| `remote_missing_count` | int | Number of items locally known but absent from catalog |
| `failed_count` | int | Number of FAILED items |
| `skipped_count` | int | Number of SKIPPED items |

**Invariant:** `total_items = new_count + changed_count + unchanged_count + remote_not_modified_count + skipped_count + failed_count`
*(Note: remote_missing_count is NOT included in total_items — those items are not in the catalog)*
