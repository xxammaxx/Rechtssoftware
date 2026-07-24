# Data Integrity Invariants — M7-B

## Schema Integrity

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| DI-SCH-01 | SyncRun.run_id ist UUID und PRIMARY KEY | SQL schema |
| DI-SCH-02 | SyncItem.item_id ist UUID und PRIMARY KEY | SQL schema |
| DI-SCH-03 | SyncItem.run_id ist FK zu SyncRun.run_id mit ON DELETE CASCADE | SQL schema |
| DI-SCH-04 | SyncItem.snapshot_id ist FK zu legal_source_snapshots.snapshot_id mit ON DELETE SET NULL | SQL schema |
| DI-SCH-05 | SyncItem.instrument_id ist FK zu legal_instruments.instrument_id mit ON DELETE SET NULL | SQL schema |
| DI-SCH-06 | legal_sources.last_catalog_stand_date ist TEXT (ISO date or empty string) | SQL schema |
| DI-SCH-07 | sync_runs.status MUSS einer der SyncRunStatus-Werte sein | Domain enum |
| DI-SCH-08 | sync_items.item_status MUSS einer der SyncItemStatus-Werte sein | Domain enum |

## Business Integrity

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| DI-BIZ-01 | Ein COMPLETED SyncRun MUSS completed_at gesetzt haben | Service layer |
| DI-BIZ-02 | Ein FAILED SyncItem MUSS nicht-leeren error_summary haben | Service layer + domain validation |
| DI-BIZ-03 | Ein NEW SyncItem DARF kein previous_sha256 haben (leerer String) | Domain validation |
| DI-BIZ-04 | Ein UNCHANGED SyncItem DARF kein new_sha256 haben (leerer String) | Domain validation |
| DI-BIZ-05 | Ein SyncItem mit snapshot_id MUSS ein new_sha256 haben | Service layer |
| DI-BIZ-06 | Die Summe der item_counts MUSS total_items ergeben (excl. remote_missing) | Domain validation |
| DI-BIZ-07 | Ein dry_run=1 SyncRun DARF keine snapshot_id setzen (keine Snapshots) | Service layer |
| DI-BIZ-08 | Ein apply SyncRun MUSS legal_sources.last_catalog_stand_date aktualisieren | Service layer |

## Temporal Integrity

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| DI-TMP-01 | SyncRun.started_at MUSS vor SyncRun.completed_at liegen | Service layer |
| DI-TMP-02 | Alle sync_runs Zeitstempel MÜSSEN ISO 8601 UTC sein | Domain validation |
| DI-TMP-03 | SyncRun.started_at DARF nicht in der Zukunft liegen (max 5 min Toleranz) | Service layer |

## Referential Integrity

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| DI-REF-01 | Jeder SyncRun.source_key MUSS in legal_sources.source_key existieren (oder zuvor angelegt werden) | Service layer |
| DI-REF-02 | SyncItem.instrument_id, wenn gesetzt, MUSS in legal_instruments.instrument_id existieren | FK constraint |
| DI-REF-03 | SyncItem.snapshot_id, wenn gesetzt, MUSS in legal_source_snapshots.snapshot_id existieren | FK constraint |

## Item Status Count Invariant

```python
# For any SyncRun where total_items > 0:
assert (
    run.new_count +
    run.changed_count +
    run.unchanged_count +
    run.remote_not_modified_count +
    run.skipped_count +
    run.failed_count ==
    run.total_items
), "Item counts must sum to total_items"
```

Note: `remote_missing_count` is NOT included in this invariant because those items exist only in local state, not in the catalog. The invariant for remote_missing is: `remote_missing_count <= number of local instruments for this source`.
