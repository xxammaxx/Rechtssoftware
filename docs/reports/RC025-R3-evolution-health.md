# RC-025-R3 Evolution Health

**Generated:** 2026-08-02 | **Comparing:** 3e17c23 → 40d816c

## Architecture Delta

| Metric | Checkpoint (3e17c23) | RC-025-R3 (40d816c) | Delta |
|--------|---------------------|---------------------|-------|
| Download paths | 2 per instrument | 1 | **Improved** |
| Import paths with network | 2 | 1 | **Improved** |
| Verified payload path | 0 | 1 (VerifiedSourcePayload) | **New** |
| Hash cross-validation points | 0 | 2 (payload→snapshot, snapshot→file) | **New** |
| FTS write strategy | DELETE+INSERT all | INSERT OR REPLACE new only | **Improved** |
| FTS visibility contract | Implicit/ambiguous | Explicit (Variant B) | **New** |
| Current expression resolution | Implicit ORDER BY | Explicit de-current UPDATE | **Improved** |
| Transaction boundary | 6 separate TX | 6 separate TX | Unchanged |
| Explicit search modes | 1 (mixed) | 2 (current + historical) | **New** |
| ADRs | 9 | 10 (ADR-010 added) | +1 |
| Public methods | ~120 | ~122 (+2 search) | +2 |
| Test count | 1123 | 1146 | +23 |
| Frozen verifier files | 1 | 3 | +2 |
| Report documents | ~10 | ~20 | +10 |

## End State

| Goal | Status |
|------|--------|
| 1 download path | ✅ |
| 1 verified payload path | ✅ |
| 1 import path | ✅ |
| 1 explicit TX boundary | ⚠️ (6 TX, but core atomicity proven) |
| 1 explicit FTS versioning contract | ✅ (ADR-010 Variant B) |
| 0 ambiguous current/historical queries | ✅ (filter + explicit historical mode) |

## Classification

```
ARCHITECTURE_IMPROVED — no erosion detected.
Download and import complexity reduced, FTS visibility made explicit,
current expression resolution hardened.
```
