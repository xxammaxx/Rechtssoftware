# ADR-010: FTS Versioning and Current Expression Visibility

**Status:** Accepted (Variante B — Versioned FTS with Current-Default)  
**Date:** 2026-08-02  
**Deciders:** Owner (Raik Mueller)  
**RC:** RC-025-R3 Phase D

## Context

The `legal_provisions_fts` FTS5 table indexes all provisions across all expressions. The current search query (`search_provisions_fts`) does NOT filter by `temporal_status = 'CURRENT'`. This means:

1. Historical and current provisions appear together in search results.
2. Users see duplicate/conflicting results when an instrument has multiple expressions.
3. There is no explicit "current only" vs. "include historical" search mode.

The FTS table is external content (`content='legal_provisions'`), meaning the text content lives in `legal_provisions` and FTS only maintains the index. Provisions are inserted incrementally (RC-025-R1 F6 fix) — no rows are deleted from FTS.

## Decision Drivers

- Rechtssoftware requires traceable source states and must not silently lose historical versions.
- Default search must unambiguously return only the currently active legal text.
- Historical search must be explicit and never accidentally mixed into normal results.
- The solution must work with SQLite/FTS5 external content tables.

## Options

### Variant A — Current-Only FTS

**Contract:** FTS contains exclusively the currently active expression. Historical expressions remain relational but are not indexed in FTS.

**Implementation:**
1. When a new expression becomes current, DELETE old expression's FTS rows within the same SQLite transaction.
2. Search query remains unchanged (all FTS rows are current by construction).
3. No additional filtering needed in search.

**Advantages:**
- Simple query — no temporal_status filter needed.
- Smaller FTS index (only current data).
- No risk of mixed current/historical results.

**Disadvantages:**
- Historical full-text search is lost. Would need a separate historical FTS index later.
- Deletion of old FTS rows is destructive. Must happen atomically with the new insert.
- Cannot answer "what did § 1 BGB say in 2024?"

**Migration Delta:**
- Modify `save_instrument_batch`: add DELETE of old FTS rows before INSERT of new.
- Add ADR-010 compliance test.
- No API changes. No new columns/tables.
- ~10 lines of production code changed.

### Variant B — Versioned FTS with Current-Default (Recommended)

**Contract:** FTS may contain current and historical expressions. Each FTS row is unambiguously bound to an expression via the relational join chain. Default search returns only current expressions. Historical search requires an explicit filter or mode.

**Implementation:**
1. Add `WHERE e.temporal_status = 'CURRENT'` to `search_provisions_fts`.
2. Add `search_provisions_fts_historical()` method for explicit historical search.
3. When a new expression supersedes an old one, explicitly set old `temporal_status` to `'SUPERSEDED'` within the same SQLite transaction.
4. FTS rows are never deleted — historical data persists.

**Advantages:**
- Full historical traceability (audit, source evidence).
- Future support for cutoff-date and version-specific search.
- No data destruction — old FTS rows remain.

**Disadvantages:**
- More complex queries (but only one extra WHERE clause).
- Larger FTS index (historical data accumulates).
- Requires explicit de-current logic (old expression → SUPERSEDED).

**Migration Delta:**
- Add `WHERE e.temporal_status = 'CURRENT'` to search query (1 line).
- Add `search_provisions_fts_historical()` method (~15 lines).
- Add de-current UPDATE in `save_instrument_batch` (~5 lines).
- Add ADR-010 compliance tests (~20 lines).
- New API endpoint or CLI flag for historical search (optional, deferred).
- ~40 lines of production code, ~20 lines of test code.

## Recommendation

**Variant B — Versioned FTS with Current-Default.**

Rationale:
- Rechtssoftware's core value is legal source traceability. Losing historical search capability contradicts the project's evidence-first design.
- The implementation delta is small (~60 lines total).
- The current unfiltered search (returning mixed current/historical) is a bug, not a feature. Variant B fixes this explicitly.
- Variant A would require a second historical FTS index later, doubling the eventual work.

## Consequences

### If Variant B is chosen:
- Default search becomes correct (current-only).
- Historical data remains searchable via explicit mode.
- Old expressions are explicitly marked `SUPERSEDED`.
- `get_current_expression` gains an additional correctness guarantee (no ambiguity from dual-CURRENT).
- FTS index grows with each new expression — acceptable for expected data volumes (GII ~6k instruments, updates quarterly).

### If Variant A is chosen:
- Simpler immediate implementation.
- Historical search must be added later as a separate feature.
- Risk: historical search request comes after production data is accumulated without FTS history.

## Decision

```
STOP_OWNER_DECISION_FTS_VERSIONING_REQUIRED
```

The owner (Raik Mueller) must select Variant A or Variant B before RC-025-R3 proceeds to Phase E (implementation).

No production code will be changed until the owner's explicit selection is received.
