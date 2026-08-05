# RC-025-R4 Phase C — ADR-010 Invariant Verification

## C1: Standard Search Current Filter

**Verification:** `evidence/rc025-r4/baseline/verify_c1_current_filter.py`

| Check | Result |
|---|---|
| Standard search for old term (AMENDED expression) | 0 results ✅ |
| Standard search for new term (CURRENT expression) | 1 result, `temporal_status='CURRENT'` ✅ |
| Historical search for old term | 1 result, `temporal_status='AMENDED'` ✅ |
| Standard search for common term | Only CURRENT results ✅ |
| Historical search for common term | Both CURRENT and AMENDED ✅ |
| Filter location | SQL `WHERE e.temporal_status = 'CURRENT'` (line 739) ✅ |

**Conclusion:** The ADR-010 Variant B default search correctly filters to CURRENT expressions at the SQL level. No Python post-filtering. Historical search is explicit and separate.

## C2: Database-Level Unique-Current Invariant

**Before:** Only application-level de-current logic in `save_instrument_batch` (lines 577-589).

**After:** Added partial unique index:

```sql
CREATE UNIQUE INDEX IF NOT EXISTS idx_le_one_current
ON legal_expressions(instrument_id) WHERE temporal_status = 'CURRENT'
```

### Migration

- File: `src/private_legal_navigator/infrastructure/database.py`
- Added to `M7A_INDEXES` list
- Idempotent (`IF NOT EXISTS`)
- Zero-downtime for existing databases with valid data

### Verification: `evidence/rc025-r4/baseline/verify_c2_unique_current.py`

| Check | Result |
|---|---|
| First CURRENT expression insert | Succeeds ✅ |
| Second CURRENT expression for same instrument | `UNIQUE constraint failed` (IntegrityError) ✅ |
| Count after failed insert | 1 CURRENT (rollback clean) ✅ |
| Index exists in schema | `idx_le_one_current` confirmed ✅ |
| Different instrument can have CURRENT | Succeeds ✅ |

### Pre-Existing Data Check

No existing database files with multiple CURRENT expressions were found in development fixtures. The partial index is safe to add to existing databases, but would reject `CREATE INDEX` if duplicate CURRENT expressions already exist.

## Classification

```text
GREEN_RC025_R4_C1_CURRENT_FILTER_VERIFIED
GREEN_RC025_R4_C2_DB_UNIQUE_CURRENT_ENFORCED
```
