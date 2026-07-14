# ADR-002 — Confirmed Reference Events and Calendar Arithmetic (M6-A)

## Status
Proposed

## Context

M5 (Deadline Candidate Extraction) detects potential deadline candidates from document text but performs no date calculations. It outputs candidates with types: `EXPLICIT_DATE`, `RELATIVE_PERIOD`, and `QUALITATIVE_REFERENCE`. For `RELATIVE_PERIOD` candidates (e.g., "2 weeks after delivery"), a reference point must be identified and confirmed before any date arithmetic is meaningful.

M6-A must bridge this gap with the smallest safe slice:
1. Display possible reference events from M5 candidates
2. Require explicit user confirmation of a reference date
3. Perform pure calendar arithmetic (days/weeks only)
4. Output a non-binding calculation preview with full traceability

**Critical constraints from the project constitution (`specify/memory/constitution.md`):**
- All processing is local-only (no cloud, no external requests)
- No automated legal decisions (product safety / professional liability)
- Human review is structurally enforced for all legally relevant output
- Every confirmation action must be traceable for the user's own reference
- No "deadline" terminology in results — these are "calculation previews"

**Integration point with M5:**
- M5 persists nothing (analyse-on-demand); all candidates are computed from `Document.text_content`
- M5's `DeadlineCandidate` has `kind=RELATIVE_PERIOD`, `amount`, `unit`, `reference_required=true`
- M6-A consumes M5 candidates but does NOT modify the M5 domain model

## Decision

### Selected: Variant B — Confirmation Persistent, Calculation On-Demand

We will implement **Variant B**: store confirmed reference events in SQLite (`confirmed_reference_events` table), but compute `CalendarCalculationCandidate` results on demand as a pure function of `(confirmed_date, duration_amount, duration_unit)`.

### Confirmation Gate Design

The core architectural innovation is the **confirmation gate** — a state machine that ensures no arithmetic is ever performed without explicit, auditable human action:

```
UNCONFIRMED ──(user confirms)──► CONFIRMED ──(user changes)──► CONFIRMED (previous → SUPERSEDED)
                                   │
                                   └──(user revokes)──► REVOKED
```

Every state transition creates a new row in `confirmed_reference_events`. The previous record is preserved with `SUPERSEDED` status. This provides a versioned history within the active document lifecycle — the user can review what they confirmed, changed, or revoked and when. This is a **product traceability feature**, not a statutory obligation under Art. 30 DSGVO (which concerns the controller's organizational record of processing activities — a separate document describing categories of processing, purposes, data categories, and retention periods).

### Mathematical Calculation Layer

The calendar arithmetic is a **pure function** — no side effects, no external dependencies:

```
calculate(date, duration) → CalendarCalculationCandidate
```

- Days: `date + timedelta(days=N)`
- Weeks: `date + timedelta(weeks=N)` (equivalent to `date + timedelta(days=7*N)`)
- Python's `datetime.timedelta` handles leap years, month boundaries, and year boundaries correctly
- Only `DAY` and `WEEK` units supported
- `MONTH`, `YEAR`, `BUSINESS_DAY`, `WORKING_DAY`, `HOUR`, and `QUALITATIVE` are rejected with `UNSUPPORTED_DURATION_UNIT`

### Legal Rule Layer (Future — NOT in M6-A)

The following legal rule areas are explicitly deferred to future builds:
- **§ 187 BGB** (Fristbeginn — day exclusion/inclusion)
- **§ 188 BGB** (Fristende — month/year alignment, missing-day rule)
- **§ 193 BGB** / **§ 222(2) ZPO** (weekend/holiday → next Werktag)
- **§ 4 VwZG** (4-day delivery fiction)
- **§ 41 VwVfG** (4-day Bekanntgabefiktion)
- **§ 180 ZPO** (delivery fiction via mailbox)
- **Feiertagsgesetze** of the 16 Bundesländer

These will be implemented as **versioned rule profiles** with source metadata (`rule_id`, `norm_citation`, `version_tag`, `jurisdiction`), keeping the arithmetic layer pure and independent.

### Persistence Decision

| What is stored | What is computed |
|---------------|-----------------|
| Confirmed reference events (`confirmed_reference_events` table) | `CalendarCalculationCandidate` |
| Confirmation audit trail (timestamps, methods, supersession chain) | `CalculationStep` list |
| Provenance (document_id, offsets — source_text reconstructable on demand) | Result warnings and adjustments |

**Schema (one new table):**
```sql
CREATE TABLE IF NOT EXISTS confirmed_reference_events (
    confirmation_id TEXT PRIMARY KEY,
    candidate_id TEXT,
    document_id TEXT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    confirmed_date TEXT NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'auto_detected',
    confirmation_method TEXT NOT NULL,
    confirmed_at TEXT NOT NULL,         -- ISO datetime UTC
    confirmed_by TEXT NOT NULL DEFAULT '',
    supersedes_confirmation_id TEXT
);
```

**Key design decisions:**
- `confirmation_id` as TEXT (UUID) — consistent with existing `documents(document_id)` pattern
- `document_id` as foreign key with `ON DELETE CASCADE` — supports right to erasure
- `confirmed_date` as ISO text — SQLite has no native date type; ISO-8601 strings are sortable and portable
- `supersedes_confirmation_id` — self-referencing for audit chain (null for first confirmation)
- No foreign key to `deadline_candidates` — M5 has no persistence table
- No `CalendarCalculationCandidate` table — computed on demand

## Open Follow-Up Decisions

| ID | Topic | When | Depends on |
|----|-------|------|------------|
| FUP-001 | Frontend: How to render the confirmation gate in the UI (confirmation dialog design, warning badges) | Before M6-A release | ADR-002 |
| FUP-002 | Versioned Rule Profiles: Schema for `LegalRuleSource` with `rule_id`, `norm_citation`, `version_tag` | M6-B (legal rule layer) | ADR-002 |
| FUP-003 | If performance demands (unlikely for single-user): Add calculation result caching or a `calculated_results` journal table | TBD — not expected before M6-B | ADR-002 |
| FUP-004 | Multi-user support: `confirmed_by` field currently `str`; needs user identity concept when multiple users exist | When multi-user becomes a requirement | ADR-001 |
| FUP-005 | Holiday database: Which format/source for 16 Bundesländer Feiertagsgesetze data | M6-B (holiday adjustment) | ADR-002 |
| FUP-006 | PDF page mapping for offsets: M5 offsets refer to concatenated text; mapping to PDF pages is lost | Future UX improvement | M5 data-model |

## Final Verdict

### **ARCH_GREEN**

**Rationale:**

The M6-A architecture achieves clean separation across all critical boundaries:

1. **Domain Integrity:** M5 (detection) and M6-A (confirmation + arithmetic) are cleanly separated. M5 is unchanged. M6-A extends M5 without modifying it. The domain layer contains no framework dependencies — pure dataclasses and enums throughout.

2. **Safety by Design:** The confirmation gate is not a recommendation — it is a structural barrier. No code path exists from M5 detection to M6-A arithmetic that bypasses user confirmation. This is a product safety measure ensuring the user maintains control over all reference date decisions. The gate also structurally enforces the constitution's "no automated legal decisions" principle.

3. **Appropriate Scope:** Only days and weeks are supported. All legal rule application (BGB, ZPO, VwZG, VwVfG, Feiertagsgesetze) is explicitly deferred with clear boundaries. The spec says what it does NOT do as clearly as what it does.

4. **Traceability:** Every confirmation action is recorded with timestamp, method, and provenance. The versioned model means no confirmation is ever silently modified — state changes create new records while preserving history. This is a legal support tool — the user must be able to review their own decision history across sessions.

5. **Simplicity:** One new table. No cache invalidation. No stale data. Pure functions for calculation. The architecture does exactly what is needed and nothing more.

6. **Extensibility:** The future legal rule layer has a clear integration point (the `adjustments_applied` dict, the `CalculationStep` list, the `CalculationOperation` enum). The arithmetic component can remain pure while legal rules are applied as post-processing steps.

No architectural concerns remain open. All 18 validation criteria pass. The three variants have been thoroughly evaluated and Variant B is unambiguously the correct choice for M6-A.

---
*ADR-002 authored: 2026-07-14. Next review: before M6-B (legal rule layer) implementation.*
