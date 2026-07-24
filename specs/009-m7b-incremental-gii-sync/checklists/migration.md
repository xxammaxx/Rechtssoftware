# Migration Testing Checklist — M7-B

## Overview

M7-B adds two new tables and one new column to the existing SQLite schema. This checklist covers migration safety, backward compatibility, and rollback scenarios.

---

## Schema Migration

| # | Item | Validation |
|---|------|------------|
| M-01 | sync_runs table created with all columns | SELECT * FROM sync_runs returns empty set |
| M-02 | sync_items table created with all columns | SELECT * FROM sync_items returns empty set |
| M-03 | sync_runs.run_id PRIMARY KEY constraint | INSERT duplicate run_id → sqlite3.IntegrityError |
| M-04 | sync_items.run_id FK → sync_runs.run_id CASCADE DELETE | DELETE sync_run → sync_items deleted |
| M-05 | sync_items.snapshot_id FK → legal_source_snapshots.snapshot_id SET NULL | DELETE snapshot → sync_items.snapshot_id becomes NULL |
| M-06 | sync_items.instrument_id FK → legal_instruments.instrument_id SET NULL | DELETE instrument → sync_items.instrument_id becomes NULL |
| M-07 | Indexes created (6 indexes) | EXPLAIN QUERY PLAN shows index usage |
| M-08 | last_catalog_stand_date column added to legal_sources | Existing sources get empty string default |
| M-09 | Idempotent: running migration twice does not cause errors | Second run: no change |
| M-10 | Existing M7-A tables unchanged | SELECT COUNT(*) on all M7-A tables matches pre-migration |

---

## Data Preservation

| # | Item | Validation |
|---|------|------------|
| D-01 | Existing legal_sources rows preserved | Row count unchanged after migration |
| D-02 | Existing source snapshots preserved | Row count and hashes unchanged |
| D-03 | Existing legal_instruments preserved | Row count and data unchanged |
| D-04 | Existing legal_provisions preserved | Row count and data unchanged |
| D-05 | Existing FTS5 index preserved | Search still returns correct results |
| D-06 | Existing case data preserved | Row count unchanged |

---

## Rollback Scenarios

| # | Scenario | Procedure | Expected |
|---|----------|-----------|----------|
| R-01 | Migrate → rollback tables | DROP sync_runs, sync_items (CASCADE) | Tables removed; existing data intact |
| R-02 | Migrate → rollback column | ALTER TABLE legal_sources DROP COLUMN last_catalog_stand_date (or recreate table) | Column removed; existing data intact |
| R-03 | Migrate → sync → rollback | DROP tables + column after sync | Sync history lost; existing legal corpus intact |

---

## Upgrade Path

| From | To | Steps |
|------|----|-------|
| v0.2.0 (M7-A) | v0.3.0 (M7-B) | 1. Run `initialize_schema()` which creates new tables + column idempotently |
| Fresh install | v0.3.0 | Schema created at startup; all tables present from first run |

---

## Migration Testing (Automated)

```python
def test_migration_idempotent():
    """Running initialize_schema() twice produces same result."""
    db_path = tmp_path / "test.db"
    initialize_schema(db_path)
    first_tables = set(get_table_names(db_path))
    
    # Add some data to verify preservation
    conn = get_connection(db_path)
    conn.execute("INSERT INTO legal_sources (...) VALUES (...)")
    conn.commit()
    
    # Run migration again
    initialize_schema(db_path)
    second_tables = set(get_table_names(db_path))
    
    assert first_tables == second_tables
    # And data is preserved
    

def test_existing_data_preserved():
    """Verify existing M7-A data survives migration."""
    # Setup: create schema, insert M7-A data
    db_path = tmp_path / "test.db"
    initialize_schema(db_path)
    insert_m7a_test_data(db_path)
    
    # Record counts before migration
    before = count_all_tables(db_path)
    
    # Migration is idempotent — just call initialize_schema again
    initialize_schema(db_path)
    
    # Verify counts unchanged
    after = count_all_tables(db_path)
    assert before == after
    

def test_cascade_delete_sync_run():
    """Deleting a sync_run cascades to sync_items."""
    db_path = tmp_path / "test.db"
    initialize_schema(db_path)
    
    run_id = insert_test_sync_run(db_path)
    insert_test_sync_items(db_path, run_id, 5)
    
    conn = get_connection(db_path)
    conn.execute("DELETE FROM sync_runs WHERE run_id = ?", (run_id,))
    conn.commit()
    
    remaining = conn.execute(
        "SELECT COUNT(*) FROM sync_items WHERE run_id = ?", (run_id,)
    ).fetchone()[0]
    assert remaining == 0
    

def test_set_null_on_snapshot_delete():
    """Deleting a snapshot sets sync_items.snapshot_id to NULL."""
    db_path = tmp_path / "test.db"
    initialize_schema(db_path)
    
    run_id = insert_test_sync_run(db_path)
    snapshot_id = insert_test_snapshot(db_path)
    insert_sync_item_with_snapshot(db_path, run_id, snapshot_id)
    
    conn = get_connection(db_path)
    conn.execute("DELETE FROM legal_source_snapshots WHERE snapshot_id = ?", (snapshot_id,))
    conn.commit()
    
    result = conn.execute(
        "SELECT snapshot_id FROM sync_items WHERE run_id = ?", (run_id,)
    ).fetchone()[0]
    assert result is None
```

---

## Migration Safety Notes

1. **The migration is purely additive:** Two new tables + one new column. No existing tables are altered (except adding a column).
2. **Idempotent:** `CREATE TABLE IF NOT EXISTS` and `_migrate_add_column` pattern handle re-runs.
3. **Existing data is never modified:** The migration reads no existing rows.
4. **No foreign key to existing data:** `sync_items.snapshot_id` and `sync_items.instrument_id` use `SET NULL` on delete, not `CASCADE`.
5. **Backward compatible:** All M7-A code paths continue to work unchanged.
