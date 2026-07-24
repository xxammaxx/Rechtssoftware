# Sync Result Output Format — Apply

## Overview

The sync result is the output of `pln sync gii --apply`. It shows what actually happened during execution, including per-item results and a summary.

---

## Output Structure

```
╔══════════════════════════════════════════════════════════════╗
║              SYNC RESULT — Gesetze im Internet              ║
║              (Apply completed)                              ║
╚══════════════════════════════════════════════════════════════╝

Source:           gesetze-im-internet
Run ID:           a1b2c3d4-e5f6-7890-abcd-ef1234567890
Started:          2026-07-24 10:00:00 UTC
Completed:        2026-07-24 10:04:32 UTC
Duration:         4m 32s
Catalog Stand:    24. Juli 2026

Item Results:
────────────────────────────────────────────────────────────────
  Status          Count
  ──────          ─────
  NEW                 3     ✅ Imported
  CHANGED            12     ✅ Updated
  UNCHANGED        6100     ⏭️  Skipped (unchanged)
  REMOTE_MISSING      5     ⚠️  Removed from catalog
  FAILED              0     —
  ─────────────────────────────────
  TOTAL            6120

Downloads:
  Attempted:  15
  Successful: 15
  Failed:     0
  Total size: 24.3 MB
  Avg speed:  91 KB/s

Errors:
  (none)

────────────────────────────────────────────────────────────────
Corpus status:   UP TO DATE (as of 24. Juli 2026)
Total snapshots: 6115 (unchanged: 6100, new: 3, updated: 12)
Total instruments: 6115
Total provisions: ~672,000
```

---

## Machine-Readable Format (JSON)

```json
{
  "mode": "apply",
  "run_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "source_key": "gesetze-im-internet",
  "catalog": {
    "url": "https://www.gesetze-im-internet.de/gii-toc.xml",
    "sha256": "a1b2c3d4...",
    "stand_date": "24. Juli 2026",
    "stand_date_iso": "2026-07-24",
    "total_items": 6120
  },
  "timing": {
    "started_at": "2026-07-24T10:00:00Z",
    "completed_at": "2026-07-24T10:04:32Z",
    "duration_seconds": 272
  },
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
  "downloads": {
    "attempted": 15,
    "successful": 15,
    "failed": 0,
    "total_bytes": 24300000,
    "avg_speed_bytes_per_sec": 91000
  },
  "errors": [],
  "failed_items": [],
  "warnings": [
    {
      "code": "REMOTE_MISSING_ITEMS",
      "detail": "5 instruments are no longer in the GII catalog.",
      "items": ["sgb_10_anhang", "bgb_anhang_1", "..."],
      "suggestion": "Use 'pln sync verify' to check snapshot integrity."
    }
  ],
  "corpus_status": "UP_TO_DATE",
  "corpus_as_of": "2026-07-24",
  "snapshot_count": 6115,
  "total_provisions_estimate": 672000
}
```

---

## Per-Item Detail Output (--verbose)

```
Per-Item Details:
────────────────────────────────────────────────────────────────
NEW       BGB           Bürgerliches Gesetzbuch          ✅ 2.3 MB
CHANGED   StGB          Strafgesetzbuch                  ✅ 1.1 MB (was a1b2..., now c3d4...)
CHANGED   VwGO          Verwaltungsgerichtsordnung        ✅ 0.8 MB (was e5f6..., now g7h8...)
UNCHANGED SGB_I         Sozialgesetzbuch I               ⏭️
... (6100 unchanged — hidden unless --verbose)
REMOTE_MISSING alte_verordnung                           ⚠️  removed
────────────────────────────────────────────────────────────────
```

---

## Partial Success Output

If some items fail but the overall run completes:

```
FAILED              2     ❌ Import errors (see below)

Failed Items:
────────────────────────────────────────────────────────────────
FAILED   altes_gesetz  Netzwerkfehler während Download   HTTP 504
FAILED   test_norm     XML-Parsefehler nach Download     Invalid XML structure
────────────────────────────────────────────────────────────────

Suggested actions:
  - Use 'pln sync gii --apply --instrument altes_gesetz' to retry
  - Check network connectivity
  - If XML parse errors persist, file a bug report with the error_summary
```

---

## Warning Codes in Result

| Code | Meaning | Severity |
|------|---------|----------|
| `REMOTE_MISSING_ITEMS` | Instruments no longer in GII catalog | WARNING |
| `SOME_ITEMS_FAILED` | Some items could not be processed | ERROR |
| `SHA256_MISMATCH` | Downloaded content hash differs from expected | ERROR |
| `DOWNLOAD_FAILED` | Network error during download | WARNING |
| `IMPORT_FAILED` | Parse or database error during import | ERROR |
| `NO_CHANGES` | No new or changed items found | INFO |
