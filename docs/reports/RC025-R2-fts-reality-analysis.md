# RC-025-R2 FTS Reality Analysis

**Generated:** 2026-08-02 | **Branch:** verify/rc025-r2-full-closure

## Current FTS Implementation

### Table Structure
The `legal_provisions_fts` table is an **external content** FTS5 table:
```sql
CREATE VIRTUAL TABLE legal_provisions_fts USING fts5(
    provision_number,
    heading,
    text_content,
    content='legal_provisions',
    content_rowid='rowid'
);
```

This means FTS queries the `legal_provisions` table directly for content — the FTS table only stores the index, not the text itself.

### Pre-Fix Behavior (destructive rebuild)
```sql
DELETE FROM legal_provisions_fts;
INSERT INTO legal_provisions_fts (rowid, provision_number, heading, text_content)
SELECT rowid, provision_number, heading, text_content FROM legal_provisions;
```
**Problem:** Every `save_instrument_batch` call deleted ALL FTS data and rebuilt from scratch. If the INSERT failed, ALL search was broken.

### Post-Fix Behavior (incremental insert)
```sql
INSERT OR REPLACE INTO legal_provisions_fts (rowid, provision_number, heading, text_content)
SELECT rowid, provision_number, heading, text_content FROM legal_provisions
WHERE provision_id IN (?, ?, ...);
```
**Improvement:** Only the newly inserted provisions are added to FTS. Existing FTS data remains intact.

## FTS5 Properties (empirical)

### Q1: Do old FTS rows remain active?
**Yes.** With incremental INSERT only, old provisions that were previously indexed remain in FTS. The `INSERT OR REPLACE` only touches rows matching the new provision_ids.

### Q2: Can duplicates occur?
**No** in normal operation. `INSERT OR REPLACE` uses the `rowid` from `legal_provisions` as the key. Since `legal_provisions` uses `INSERT OR REPLACE` with UUID-based `provision_id`, re-inserting the same provision_id results in the same `rowid`, and FTS replaces rather than duplicates.

### Q3: Can search return old and new versions simultaneously?
**Yes — this is the current ambiguity.** The FTS table indexes ALL provisions regardless of whether their expression is "current". A search for "Testnorm" returns all provisions containing that word, even if their expression has been superseded.

However, the search query joins through `legal_expressions`:
```sql
JOIN legal_expressions e ON e.expression_id = p.expression_id
JOIN legal_instruments i ON i.instrument_id = e.instrument_id
WHERE legal_provisions_fts MATCH ?
```
The FTS match returns rowids, which map to `legal_provisions`. The JOIN to `legal_expressions` filters by... nothing — there's no `WHERE temporal_status = 'CURRENT'` in the search query!

**Confirmed:** The search does NOT filter by current expression. All historical and current provisions are returned.

### Q4: Is FTS within the same SQLite transaction?
**Yes.** The FTS INSERT is inside `save_instrument_batch` which runs inside a `with transaction(self._db_path) as conn:` context manager. The FTS update is atomic with the relational inserts.

### Q5: Can FTS and relational tables diverge?
**Theoretically yes**, because:
- FTS uses `INSERT OR REPLACE` on provision rowids
- When a provision is deleted from `legal_provisions`, FTS is NOT updated
- There is no DELETE from FTS in the current code

**In practice, not yet** because:
- Provisions are never deleted in the current application
- `INSERT OR REPLACE` keeps FTS in sync for inserts/updates

### Q6: Are there triggers?
**No.** The FTS table has no triggers. FTS updates are manual in `save_instrument_batch`.

## FTS Versioning Contract Decision

### Current State: Implicit Variant A/B hybrid
- FTS contains ALL provisions (historical + current) — like Variant B
- Search returns ALL provisions without current-status filter — like Variant B
- But there's no explicit version/status column in FTS — ambiguous
- The JOIN to `legal_expressions` doesn't filter by temporal_status

### Recommended: Variante B — Explicit Versioning

FTS enthält historische und aktuelle Fassungen. Jede FTS-Zeile ist durch `rowid` eindeutig an `legal_provisions.provision_id` und via JOIN an `legal_expressions.expression_id` gebunden.

**Required changes (to be done in a future RC):**
1. Add `WHERE e.temporal_status = 'CURRENT'` to the default search query
2. Add an explicit "include historical" search mode
3. When a new expression supersedes an old one, explicitly set old `temporal_status` to `'SUPERSEDED'`

**Current status:** AMBER — search returns mixed current/historical results. For RC-025-R2 scope, this is documented as a known limitation. The fix requires ADR-level decisions about version visibility and is deferred to a subsequent RC.

## FTS Consistency Under Fault Injection

During `save_instrument_batch` failure (exception mid-transaction), the SQLite transaction rolls back:
- Relational inserts are rolled back
- FTS INSERT is rolled back (same transaction)
- No orphaned FTS rows remain

**Verified:** Test C5 (`test_old_fts_data_visible_after_failure`) confirms old FTS data survives a simulated save failure.

## Recommendations

1. **Short-term (RC-025-R2):** Incremental FTS insert is sufficient. Document the mixed-current-historical search behavior.
2. **Medium-term:** Add explicit `temporal_status = 'CURRENT'` filter to search query.
3. **Long-term:** Implement explicit superseding of old expressions + historical search mode.
