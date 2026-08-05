# RC-025-R6 Seeded Fault Report

**Date:** 2026-08-03
**Method:** RED→GREEN→RED→GREEN per fault boundary

## Results

| ID | Boundary | Seeded Mutation | RED Detected? | GREEN Restored? |
|----|----------|----------------|---------------|-----------------|
| SF2 | Payload-Hash | Content modified after hash | ✅ YES | ✅ YES |
| SF3 | Tempfile Write | I/O error during write_bytes | ✅ YES | ✅ YES |
| SF4 | Rename Gap | Tempfile without rename | ✅ YES | ✅ YES |
| SF5 | Cross-Validation | File tampered after hash | ✅ YES | ✅ YES |
| SF6 | Dedup | Second write without dedup check | ✅ YES | ✅ YES |
| SF8 | Normalization | File extension accepted as abbr | ✅ YES | ✅ YES |
| SF15 | Retry Dedup | Second CURRENT without dedup | ✅ YES | ✅ YES |

## Verdict

All 7 seeded fault tests correctly detect their intended mutations (RED phase) and recover to GREEN when the mutation is removed.

```text
GREEN_RC025_R6_SEEDED_FAULT_GATE_PASSED
```

Evidence: `tests/rc025_r6_verifier/test_seeded_fault.py` — 7/7 passed.
