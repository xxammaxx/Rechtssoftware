# RC-025-R4 Phase I — Evolution Health Gate

## Baseline Commits

| Commit | Phase | Key Change |
|--------|-------|------------|
| `3e17c23` | RC-025 Checkpoint | Initial contract hardening |
| `11e75e1` | RC-025-R2 | F4 byte-identity + F6 incremental FTS |
| `47b9744` | RC-025-R3 | ADR-010 Variant B (FTS current/historical) |
| RC-025-R4 | Candidate | DB-level unique-current invariant |

## Architecture Metrics (RC-025-R4 vs RC-025-R3)

| Metric | RC-025-R3 (47b9744) | RC-025-R4 | Delta |
|--------|---------------------|-----------|-------|
| Download paths | 1 | 1 | 0 |
| Verified payload paths | 1 | 1 | 0 |
| Import paths | 1 | 1 | 0 |
| FTS search paths (default) | 1 | 1 | 0 |
| FTS search paths (historical) | 1 | 1 | 0 |
| FTS write paths | 1 | 1 | 0 |
| SQLite transaction boundaries | 1 | 1 | 0 |
| DB-enforced invariants | 0 | 1 (idx_le_one_current) | **+1** |
| Source files (mypy clean) | 73 | 73 | 0 |
| Test count (committed) | 1076 | 1076 | 0 |
| New DB indexes | 0 | 1 (partial unique) | **+1** |
| New constraints | 0 | 1 (CURRENT uniqueness) | **+1** |

## Contract Compliance

| Contract | Status |
|----------|--------|
| 1 Downloadpfad | ✅ Maintained |
| 1 Verified-Payload-Pfad | ✅ Maintained |
| 1 Importpfad | ✅ Maintained |
| 1 zentraler FTS-Suchpfad mit explizitem Modus | ✅ Maintained |
| 1 FTS-Schreibpfad | ✅ Maintained |
| 1 SQLite-Transaktionsgrenze | ✅ Maintained |
| 1 DB-seitig erzwungene Current-Invariante | ✅ **NEW** |
| 0 gemischte Current-/Historical-Suchergebnisse | ✅ Maintained |

## Assessment

The architecture has **improved** from RC-025-R3:
- Added one DB-level invariant (partial unique index) without adding new code paths
- No new download/import/search paths introduced
- No increase in cyclomatic complexity
- No new layer violations
- No duplication increase

## Classification

```text
GREEN_RC025_R4_EVOLUTION_HEALTH_IMPROVED
```
