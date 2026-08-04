# RC-025-R2 Atomicity Verification

**Generated:** 2026-08-02 | **Branch:** verify/rc025-r2-full-closure

## F6 Atomicity Contract Status

### What Was Fixed (RC-025-R1)
- **FTS rebuild:** Destructive `DELETE+INSERT` → incremental `INSERT OR REPLACE`
- **Single download:** `download_verified()` replaces dual `download_with_headers()` + `download()`

### What Remains

| Aspect | Status | Evidence |
|--------|--------|----------|
| Snapshot file write | Content-addressed, immutable | `_write_content_addressed()` |
| File before DB | Correct pattern per ADR | Snapshot written, then DB insert |
| DB transaction scope | Per-instrument (save_instrument_batch) | `with transaction()` context manager |
| FTS within transaction | Yes | Same conn as relational inserts |
| Current expression switch | Implicit (temporal_status='CURRENT') | No explicit de-current |
| Sync item finalization | Separate TX from import | save_sync_item has own connection |
| Rollback on failure | Partial — save_instrument_batch rolls back | save_sync_item/save_sync_run do NOT roll back |
| Orphaned snapshots | Content-addressed, not auto-deleted | Treated as repairable artifacts per ADR |

### Transaction Boundary Map

```
execute()
  ├─ save_sync_run()          ← TX #1 (own connection)
  ├─ _process_item()          ← per item:
  │    ├─ download_verified()  ← network (no TX)
  │    ├─ sync_gii_instrument()
  │    │    ├─ sync_instrument()
  │    │    │    ├─ _write_content_addressed()  ← file I/O (no TX)
  │    │    │    └─ returns GiiParsedInstrument
  │    │    └─ save_instrument_batch()  ← TX #2 (atomic per instrument)
  │    │         ├─ INSERT snapshot
  │    │         ├─ INSERT instrument
  │    │         ├─ INSERT expression
  │    │         ├─ INSERT provisions
  │    │         ├─ INSERT FTS (incremental)
  │    │         └─ COMMIT
  │    ├─ cross-validate payload.sha256 == snapshot.sha256
  │    └─ save_sync_item()     ← TX #3 (own connection)
  ├─ update_sync_run()         ← TX #4 (own connection)
  └─ update_catalog_stand_date() ← TX #5 (own connection)
```

### Post-Fix Verifier Test Results

| Test | What It Proves | Result |
|------|---------------|--------|
| C1: download_count == 1 | Single network retrieval per instrument | ✅ |
| C2: Byte identity | hash chain: download → snapshot → file | ✅ |
| C3: Adversarial stub | No second download; V2 never reaches pipeline | ✅ |
| C4: Tamper detection | Modified snapshot detected as mismatch | ✅ |
| C5: Old data survives failure | FTS still returns old results after fault | ✅ |
| C6: New data after success | FTS, integrity_check, foreign_key_check pass | ✅ |
| C7: Retry idempotency | No duplicate expressions, only one current | ✅ |

### Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| save_sync_item failure after instrument import | LOW | Instrument data committed; sync item missing. Repairable by re-running sync (idempotent). |
| Snapshot file orphaned on DB failure | LOW | File is content-addressed; no DB reference. Repairable by cleanup or re-import. |
| Implicit current expression (no de-current) | AMBER | Two expressions can both have temporal_status='CURRENT'. `ORDER BY valid_from DESC LIMIT 1` picks newest. Works but not explicit. |

## Classification

```
AMBER_F6_ATOMICITY_PARTIAL — core atomicity proven,
transaction boundary hardening deferred.
```
