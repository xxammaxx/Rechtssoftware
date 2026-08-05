# RC-025-R3 FTS and Transaction Reality Analysis

**Generated:** 2026-08-02 | **Branch:** verify/rc025-r3-atomicity-closure  
**HEAD:** 11e75e1

## 1. FTS5 Table Structure

**Source:** `src/private_legal_navigator/infrastructure/database.py:251`

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS legal_provisions_fts USING fts5(
    provision_id UNINDEXED,
    provision_number,
    heading,
    text_content,
    content='legal_provisions',
    content_rowid='rowid'
)
```

### Type: External Content FTS5

The table uses `content='legal_provisions', content_rowid='rowid'` — this is an **external content** FTS5 table. The actual text is stored in `legal_provisions.text_content`, not duplicated in FTS. FTS only maintains the search index.

### Columns
| Column | Indexed | Notes |
|--------|---------|-------|
| provision_id | UNINDEXED | Stored but not searchable; identifies which provision |
| provision_number | Yes | e.g., "§ 1" |
| heading | Yes | e.g., "Beginn der Rechtsfähigkeit" |
| text_content | Yes | Full provision text |

### Identity Binding

Each FTS row is bound to `legal_provisions` via `rowid`. Through joins:
- FTS.rowid → legal_provisions.rowid → provision_id
- legal_provisions.expression_id → legal_expressions.expression_id
- legal_expressions.instrument_id → legal_instruments.instrument_id

**No explicit current/historical flag in FTS.** The current status is only in `legal_expressions.temporal_status`.

## 2. Query Behavior

**Source:** `sqlite_legal_source_repository.py:704-728`

```sql
SELECT p.provision_id, p.provision_number, p.heading,
       p.stable_key, p.text_content,
       e.expression_id, i.abbreviation, i.official_title,
       i.authority_tier, e.temporal_status, e.retrieved_at,
       snippet(legal_provisions_fts, 2, ...) as snippet
FROM legal_provisions_fts fts
JOIN legal_provisions p ON p.rowid = fts.rowid
JOIN legal_expressions e ON e.expression_id = p.expression_id
JOIN legal_instruments i ON i.instrument_id = e.instrument_id
WHERE legal_provisions_fts MATCH ?
ORDER BY rank
LIMIT ?
```

### Critical Finding: NO Current Filter

The search query does **NOT** filter by `e.temporal_status = 'CURRENT'`. It returns ALL provisions matching the search term, regardless of whether their expression is current, superseded, or historical.

### Consequences

1. **Old and new versions appear together.** If "§ 1 BGB" exists in both a 2024 and a 2026 expression, searching for "Rechtsfähigkeit" returns BOTH.
2. **No historical search mode.** There is no explicit filter or mode to toggle between "current only" and "include historical."
3. **Rank-based ordering, not temporal.** Results are ordered by FTS rank, not by `valid_from` date.

## 3. Current Expression Resolution

**Source:** `sqlite_legal_source_repository.py:401-411`

```sql
SELECT * FROM legal_expressions
WHERE instrument_id = ? AND temporal_status = 'CURRENT'
ORDER BY valid_from DESC LIMIT 1
```

### Mechanism: Implicit, not explicit

- When a new expression is inserted, its `temporal_status` is set to `'CURRENT'` (see `_parse_law_xml` in `gii_adapter.py:393`).
- The old expression's `temporal_status` is **NOT** changed to `'SUPERSEDED'`.
- Multiple expressions for the same instrument can have `temporal_status='CURRENT'`.
- `get_current_expression()` resolves ambiguity via `ORDER BY valid_from DESC LIMIT 1` — newest wins.

### Risk

If two expressions have the same `valid_from` date, which one is "current" is non-deterministic (depends on insertion order within the LIMIT 1).

## 4. Transaction Boundary

**Source:** `sqlite_legal_source_repository.py:489-614`, `sync_service.py:498-610`

### Within save_instrument_batch (ONE transaction)

```
BEGIN TRANSACTION
  INSERT OR REPLACE INTO legal_source_snapshots     (snapshot)
  INSERT OR REPLACE INTO legal_instruments           (instrument)
  INSERT OR REPLACE INTO legal_expressions           (expression) ← temporal_status='CURRENT'
  INSERT OR REPLACE INTO legal_provisions            (provisions × N)
  INSERT OR REPLACE INTO legal_provisions_fts        (incremental, new provisions only)
COMMIT ← auto on context manager exit
```

**All five inserts are atomic within this transaction.** If any fails, all roll back.

### Outside the Transaction

| Operation | File | Connection |
|-----------|------|------------|
| Snapshot file write | `gii_adapter.py:_write_content_addressed` | None (file I/O) |
| Hash cross-validation | `sync_service.py:_process_item` (step 8) | None (in-memory) |
| save_sync_item | `sqlite_legal_source_repository.py:994` | Own connection + commit |
| save_sync_run | `sqlite_legal_source_repository.py:850` | Own connection + commit |
| update_sync_run | `sqlite_legal_source_repository.py:889` | Own connection + commit |
| update_catalog_stand_date | `sqlite_legal_source_repository.py:1073` | Own connection + commit |

### Gap Analysis

| Risk | Severity | Detail |
|------|----------|--------|
| save_sync_item fails after instrument import | Medium | Instrument data committed; sync item lost. Idempotent re-run fixes this. |
| Snapshot file orphaned on DB rollback | Low | Content-addressed; no DB reference. No data corruption. |
| Multiple CURRENT expressions | Low | `ORDER BY valid_from DESC LIMIT 1` resolves. No explicit de-current needed for correctness in single-instrument context. |
| FTS returns historical+current mixed | High | Search returns all versions. User sees duplicate/conflicting results. |

## 5. Error Behavior

### Exception during save_instrument_batch

- Transaction rolls back completely.
- Snapshot file exists on disk (content-addressed, no DB reference) — orphaned file.
- Old instrument/expression/provisions remain unchanged.
- Old FTS data remains intact (was never deleted since incremental INSERT).

### Process crash between save_instrument_batch and save_sync_item

- Instrument data committed to DB.
- New expression visible (temporal_status='CURRENT').
- FTS contains new provisions.
- Sync item NOT saved — no trace in sync history.
- Catalog stand date NOT updated.
- **State:** Data imported but no sync record. Idempotent re-run handles safely.

### Process crash during save_sync_item

- If save_sync_item's own transaction fails, sync item lost.
- Instrument data already committed (separate transaction).
- Idempotent re-run detects unchanged hash → UNCHANGED → no re-import.

## 6. FTS Rebuild

**Source:** `sqlite_legal_source_repository.py:730-734`

```python
def rebuild_fts_index(self) -> None:
    conn.execute("INSERT INTO legal_provisions_fts(legal_provisions_fts) VALUES('rebuild')")
```

The `rebuild` command forces FTS5 to re-read content from the external content table. This is a full, potentially expensive operation. It is NOT called during normal sync — only available as a manual recovery tool.

## References

- FTS table DDL: `database.py:251-258`
- Search query: `sqlite_legal_source_repository.py:708-721`
- save_instrument_batch: `sqlite_legal_source_repository.py:489-614`
- get_current_expression: `sqlite_legal_source_repository.py:401-411`
- save_sync_item: `sqlite_legal_source_repository.py:994-1031`
- _process_item: `sync_service.py:629-780`
- Expression temporal_status: `gii_adapter.py:393`
