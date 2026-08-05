# RC-025-R1 Atomicity Map — F6 Atomic Activation & FTS5 Consistency

**Generated:** 2026-08-02 | **Branch:** fix/rc025-r1-m7b-integrity-closure

## Current Transaction Boundaries

### Import Path (per instrument)
```
sync_gii_instrument()
  └─ GiiAdapter.sync_instrument(item, payload)
       └─ _write_content_addressed()          ← File I/O (NOT in DB TX)
       └─ Returns GiiParsedInstrument
  └─ repo.save_instrument_batch()             ← DB TX #1 (atomic within itself)
       └─ INSERT snapshot
       └─ INSERT instrument  
       └─ INSERT expression (temporal_status=CURRENT)
       └─ INSERT provisions
       └─ DELETE FROM legal_provisions_fts    ← DESTRUCTIVE: removes ALL FTS data
       └─ INSERT INTO legal_provisions_fts    ← REBUILDS from legal_provisions
       └─ COMMIT                              ← Auto on context exit
  └─ repo.update_snapshot_status()            ← DB TX #2 (separate connection)
```

### Sync Run Path (per run)
```
SyncExecutionService.execute()
  └─ repo.save_sync_run()                     ← DB TX #3
  └─ For each item:
       └─ _process_item()
            └─ download_verified()            ← Network I/O
            └─ sync_gii_instrument()          ← DB TX #1 (above)
            └─ repo.save_sync_item()          ← DB TX #4
  └─ repo.update_sync_run()                   ← DB TX #5
  └─ repo.update_legal_source_catalog_stand_date() ← DB TX #6
```

## Violations Found

### F6.1: Non-Atomic Boundary
6 separate database transactions per sync run. If a failure occurs between TX #1 and TX #4:
- New instrument data is committed (TX #1)
- Sync item record is NOT committed (TX #4 failed)
- → Orphaned instrument data with no sync trace

### F6.2: Destructive FTS Rebuild
Each `save_instrument_batch` call DELETES ALL FTS rows and rebuilds from `legal_provisions`. If the INSERT fails:
- All FTS search data is lost until next rebuild
- Existing search results become empty

### F6.3: Implicit "Current Expression"
The current expression is determined by `temporal_status = 'CURRENT'`. When a new expression is saved, there's no explicit de-current of the old one — both have `temporal_status=CURRENT`, and `get_current_expression` uses `ORDER BY valid_from DESC LIMIT 1`.

### F6.4: No Rollback Guard for File Operations
The snapshot file is written BEFORE the database transaction. If the DB transaction fails, an orphaned content-addressed file remains on disk with no DB record referencing it.

## Fix Implemented (F6 Minimal)

The F6 fix needs to:
1. Change FTS rebuild from DELETE+INSERT to incremental INSERT (for the new provisions only)
2. Add explicit de-current of old expression when new one is inserted

The file-before-DB strategy (snapshot written first, then DB transaction) is actually the CORRECT pattern per the runcard's Section 14.4:
- Snapshot first written content-addressed and immutable
- File hash verified
- Then DB transaction starts
- On DB failure: orphaned snapshot file is a repairable artifact

The orphaned file pattern is acceptable per the runcard:
> "orphaned Snapshots werden nicht automatisch gelöscht, sondern als reparierbare technische Artefakte behandelt"
