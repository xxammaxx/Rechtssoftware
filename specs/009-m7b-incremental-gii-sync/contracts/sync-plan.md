# Sync Plan Output Format — Dry-Run

## Overview

The sync plan is the output of `pln sync gii --dry-run` (or default mode). It shows what would happen during an apply run without actually downloading or modifying anything.

---

## Output Structure

```
╔══════════════════════════════════════════════════════════════╗
║              SYNC PLAN — Gesetze im Internet                ║
║              (Dry-Run — no changes made)                    ║
╚══════════════════════════════════════════════════════════════╝

Source:           gesetze-im-internet
Catalog URL:      https://www.gesetze-im-internet.de/gii-toc.xml
Catalog SHA-256:  a1b2c3d4e5f6... (first 16 chars)
Catalog Stand:    24. Juli 2026
Last Known Stand: 20. Juli 2026
Catalog Fresh:    YES (3 days newer)

Item Classification:
────────────────────────────────────────────────────────────────
  Status          Count     Will Download?
  ──────          ─────     ───────────────
  NEW                 3     YES
  CHANGED            12     YES
  UNCHANGED        6100     NO
  REMOTE_MISSING      5     NO (removed from catalog)
  ─────────────────────────────────
  TOTAL            6120

Download Estimate:
  Items to download:  15
  Est. total size:    ~25 MB
  Est. time:          ~2 min (at 200 KB/s)

Changes if applied:
  - 3 new instruments will be added to the corpus
  - 12 instruments will be updated to their latest version
  - 5 instruments will be marked as REMOTE_MISSING
  - 6100 instruments remain unchanged
  - All existing snapshots and metadata preserved

────────────────────────────────────────────────────────────────
Run ID (if persisted):  (dry-run — not persisted)
Status:                DRY_RUN
```

---

## Machine-Readable Format (JSON)

For programmatic consumption, `--format json` flag outputs:

```json
{
  "mode": "dry_run",
  "source_key": "gesetze-im-internet",
  "catalog": {
    "url": "https://www.gesetze-im-internet.de/gii-toc.xml",
    "sha256": "a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890",
    "stand_date": "24. Juli 2026",
    "stand_date_iso": "2026-07-24",
    "total_items": 6120
  },
  "last_known_stand_date": "20. Juli 2026",
  "last_known_stand_date_iso": "2026-07-20",
  "catalog_fresh": true,
  "items": {
    "total": 6120,
    "new": 3,
    "changed": 12,
    "unchanged": 6100,
    "remote_not_modified": 0,
    "remote_missing": 5,
    "skipped": 0,
    "failed": 0
  },
  "download_estimate": {
    "items_to_download": 15,
    "estimated_total_bytes": 25000000,
    "estimated_time_seconds": 120
  },
  "warnings": [
    {
      "code": "CATALOG_FRESH",
      "message": "Catalog stand date is 3 days newer than last known. Changes detected."
    },
    {
      "code": "REMOTE_MISSING_ITEMS",
      "message": "5 instruments are no longer in the GII catalog. These may have been removed or consolidated."
    }
  ],
  "status": "DRY_RUN",
  "no_changes_made": true
}
```

---

## Warning Codes in Plan

| Code | Meaning | Severity |
|------|---------|----------|
| `CATALOG_FRESH` | Catalog stand date is newer | INFO |
| `CATALOG_STALE` | Catalog stand date matches last known (no catalog-level changes) | INFO |
| `REMOTE_MISSING_ITEMS` | Some local instruments no longer in catalog | WARNING |
| `FORCE_MODE_ACTIVE` | --force flag bypassed stand-date gate | WARNING |
| `INSTRUMENT_NOT_FOUND` | --instrument key not found in catalog | ERROR |
| `NO_PREVIOUS_SYNC` | First sync — no previous state to compare | INFO |

---

## Error Plan Output

If the plan cannot be created (catalog fetch fails):

```
╔══════════════════════════════════════════════════════════════╗
║              SYNC PLAN FAILED                               ║
╚══════════════════════════════════════════════════════════════╝

Error: Failed to fetch GII catalog
Reason: HTTP 503 — Service Unavailable
Source: https://www.gesetze-im-internet.de/gii-toc.xml

Suggested actions:
  - Check internet connection
  - Verify GII is accessible (https://www.gesetze-im-internet.de)
  - Try again later
  - Use --force to skip catalog check (if offline)

Exit code: 2
```
