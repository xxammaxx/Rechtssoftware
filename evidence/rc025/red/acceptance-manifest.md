# RC-025 M7-B Contract Verification Manifest

**Verifier Role:** Independent (processual separation)
**Status:** FROZEN — Builder must not edit

## Acceptance Criteria

The following 10 RED conditions MUST be reproducibly demonstrated before any fix is applied.
Each test must:
1. Fail for the expected reason (contract violation, not a typo)
2. Pass after the fix
3. Fail again after targeted revert/seeded fault

## RED Test Matrix

| # | Contract | RED Condition | Files Affected | Expected Error |
|---|----------|---------------|----------------|----------------|
| RED-1 | Dry-Run Immutability | execute() with dry_run=True persists SyncRun + SyncItems to SQLite | `sync_service.py:438,470,476,488,499` | Database mutation detected during dry-run |
| RED-2 | Dry-Run History | Dry-run creates persistent sync history records | `sync_service.py:438,470` | SyncRun records found after dry-run |
| RED-3 | KNOWN without evidence | plan() classifies items as KNOWN without remote verification | `sync_service.py:171-189` | KNOWN used where KNOWN_UNVERIFIED required |
| RED-4 | Double download | _process_item downloads, then sync_gii_instrument downloads again | `sync_service.py:581,650` + `legal_source_service.py:150` | Content downloaded twice per item |
| RED-5 | Stale plan apply | Plan lacking digest can be applied after catalog/corpus change | `sync_service.py` Plan model | PLAN_STALE not raised |
| RED-6 | Tampered plan | Plan without plan_digest accepted without integrity check | `sync_service.py` Plan model | PLAN_INTEGRITY_FAILED not raised |
| RED-7 | No concurrent lock | Two apply processes can run simultaneously | `sync_service.py` execute() | SYNC_ALREADY_RUNNING not enforced |
| RED-8 | Byte identity mismatch | Downloaded bytes (hashed) ≠ bytes passed to import pipeline | `sync_service.py:581,621,650` | HASHED_BYTES != PARSED_BYTES |
| RED-9 | Non-atomic activation | FTS could be in partial state if import fails mid-way | `legal_source_service.py:172-196` | Partial FTS state possible |
| RED-10 | Truth mirror drift | README metrics can be changed without fresh evidence | README.md + docs | Numbers changed without fresh test run |

## Evidence Schema

Each RED test produces:
```json
{
  "test_id": "RED-N",
  "contract": "Description",
  "expected_failure": "What the test expects to see fail",
  "actual_failure": "What actually happened",
  "timestamp": "ISO datetime",
  "files_affected": ["list"],
  "reproduction_command": "exact command"
}
```

## Verifier Files (Read-Only)
- `evidence/rc025/red/` — RED test outputs (before fix)
- `evidence/rc025/green/` — GREEN test outputs (after fix)
- `evidence/rc025/fault-injection/` — Revert/seed fault re-validation

## Non-Touch Areas for Builder
- This manifest
- RED test source files once written
- Verifier evidence outputs
- Acceptance criteria wording
