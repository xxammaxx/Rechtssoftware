# ADR-008 — Case Legal Timeline and Case-Legal Links (M7-A)

**Status:** Accepted

**Date:** 2026-07-22

**Deciders:** Architecture Agent (ADR-008)

## Context

M6-A (ADR-002) introduced persistent reference event confirmation with an append-only audit trail
(`confirmed_reference_events` table, `supersedes_confirmation_id` chain) and the confirmation
lifecycle state machine: CANDIDATE → CONFIRMED → SUPERSEDED / REVOKED. ADR-003 (Local
Confirmation Workspace) extended this with idempotency, CSRF protection, and the PRG (POST-Redirect-GET)
pattern for all state-mutating actions.

M7-A must now build on these foundations to add **two new capabilities**:

1. **Case Legal Timeline** — A chronological record of all legally significant events within a case,
   enabling the user to trace the progression of their legal matter from initiation through
   administrative acts, hearings, objections, amendments, and deadlines. Every event is
   subject to human confirmation, correction, and revocation — nothing is auto-applied.

2. **Case-Legal Links** — Explicit, auditable connections between a case and the legal norms
   (from the M7-A legal source foundation) relevant to that case. A norm is proposed as a
   candidate, confirmed by the user, and may be corrected or revoked. Every state change
   is versioned.

**Existing architecture that M7-A must integrate with:**

| Component | Role in M7-A |
|---|---|
| `confirmed_reference_events` table (ADR-002) | Provides the append-only pattern: insert-only, supersession chain, no destructive updates |
| Confirm/Reject/Revoke lifecycle (ADR-002, ADR-003) | Reused identically for legal events and norm links |
| `supersedes_confirmation_id` column | Direct analogue for `previous_event_id` and `supersedes_link_id` |
| `Case` entity (`domain/case.py`) | Extended with timeline — `Case.case_id` anchors all events |
| App-state DI pattern (`app.state.*`) | Services wired through application factory |
| POST-only + PRG pattern (ADR-003) | All state-mutating endpoints follow this |
| Safe logging via `safe_log_event` | Applied to all event/link mutations |

**What does NOT yet exist** (from `m7a-reality-refresh.md`) and must be created:
- `case_legal_events` table
- `case_legal_links` (norm-to-case) table
- `event_relations` table
- Derived timeline projection (query, not table)
- Domain entities for legal events, relations, and legal links

**Key constraints from project constitution and prior ADRs:**
- All processing is local-only (no cloud, no external requests at runtime)
- No automated legal decisions — event types are descriptive labels only
- Human review is structurally enforced for all legally relevant output
- Every confirmation/correction/revocation action is auditable
- No "deadline" terminology in results unless explicitly user-confirmed
- Append-only data model: no row is ever silently overwritten

## Decision

We implement a unified **Case Legal Timeline and Case-Legal Links** system built on ten
architectural sub-decisions, each with its own rationale grounded in the existing codebase.

---

### Decision 1: Append-Only Legal Events

**All case legal events are append-only.** Corrections and state changes always create new
rows. The original record is never overwritten or deleted. This is the same pattern as
`confirmed_reference_events` (ADR-002), where each lifecycle transition produces a new
`confirmation_id` while the predecessor row persists.

**Rationale:**
- Legal traceability demands that no record of what the user entered, confirmed, or corrected
  is ever lost — even if it was erroneous.
- The existing `supersedes_confirmation_id` column in `confirmed_reference_events` has proven
  this pattern in M6-A: the `get_history_for_candidate()` method returns all versions,
  `get_active_confirmation()` returns only the latest non-superseded record.
- SQLite's write-ahead log (WAL) mode naturally supports this insert-heavy pattern without
  table locks on reads.

**Implementation:**
```sql
CREATE TABLE IF NOT EXISTS case_legal_events (
    event_id TEXT PRIMARY KEY,          -- UUID
    case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,           -- see Decision 3
    title TEXT NOT NULL,                -- user-visible short description
    description TEXT NOT NULL DEFAULT '', -- optional longer narrative
    occurred_at TEXT NOT NULL,          -- when the event actually happened (ISO date)
    known_at TEXT NOT NULL,             -- when the user learned of it (ISO date)
    recorded_at TEXT NOT NULL,          -- when it was entered (ISO datetime UTC)
    lifecycle_status TEXT NOT NULL DEFAULT 'candidate', -- see Decision 5
    previous_event_id TEXT,             -- for corrections: points to the record being corrected
    revoked_at TEXT,                    -- UTC datetime when revoked (NULL if active)
    revoked_by TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,           -- immutable creation timestamp
    created_by TEXT NOT NULL DEFAULT ''
);
```

- `previous_event_id` is the direct analogue of `supersedes_confirmation_id` from ADR-002.
- No `UPDATE` statements exist for this table in the repository layer — only `INSERT`.
- `DELETE` is reserved for the user's right to erasure (via `CASCADE` on case deletion), not
  for lifecycle operations.

---

### Decision 2: Separate Temporal Dimensions

Every event records three independent timestamps:

| Field | Meaning | Validation |
|---|---|---|
| `occurred_at` | When the legal event actually happened in the real world (e.g., the date on the Bescheid) | Must be present; must not be in the future relative to `known_at` |
| `known_at` | When the user first learned about the event (e.g., date of delivery/receipt) | Must be present; must be ≥ `occurred_at` |
| `recorded_at` | When the event was entered into PrivateLegalNavigator | Set by the system at insertion time (`datetime.now(UTC)`); immutable |

**Rationale:**
- In legal practice, the gap between `occurred_at` (the date on a document) and `known_at`
  (when it was received) is legally significant — it determines the start of appeal periods.
- Keeping them as separate columns in the same row avoids an explosion of auxiliary "delivery"
  events while preserving the data needed for future legal rule application (M6-B and beyond).
- `recorded_at` provides an audit trail independent of the legal content — it answers
  "when was this information added to the system?"
- All three timestamps use ISO-8601 TEXT in SQLite (consistent with `confirmed_reference_events`
  `confirmed_at` and `confirmed_date` columns).

---

### Decision 3: Event Types (Closed Enumeration)

The system supports exactly 11 event types, modelled as a `StrEnum` in the domain layer:

```
DOCUMENT_ISSUED              — A Bescheid, Urteil, or other official document was issued
DOCUMENT_RECEIVED             — A document was received by the user
DOCUMENT_OPENED               — The user opened/read a received document
ADMINISTRATIVE_ACT_EFFECTIVE  — A Verwaltungsakt took legal effect
HEARING_STARTED               — A hearing, Verhandlung, or oral proceeding began
HEARING_CONCLUDED             — A hearing ended (may produce new deadlines)
OBJECTION_FILED               — The user filed an objection (Widerspruch, Einspruch)
DECISION_AMENDED              — A prior decision was amended (Änderungsbescheid)
DECISION_REVOKED              — A prior decision was revoked (Rücknahme/Widerruf)
EVIDENCE_SUBMITTED            — The user submitted evidence to a court or authority
DEADLINE_STARTED              — A deadline period began (requires a confirmed reference event)
DEADLINE_EXPIRED              — A deadline period elapsed (informational only)
```

**Rationale:**
- These event types are **descriptive labels**, not legal triggers. They describe what
  happened, not what legal consequence follows. This aligns with the constitution's
  "no automated legal decisions" principle.
- The closed enumeration prevents unbounded complexity while covering the core events
  in German Verwaltungs- and Zivilverfahren.
- The list is forward-compatible: additional types can be added to the enum and schema
  without breaking existing data (new types are backwards-compatible with old records).
- Event types are stored as TEXT in SQLite (consistent with `event_type` in
  `confirmed_reference_events`).

---

### Decision 4: Explicit Relations Between Events

Events are connected through a dedicated relation table with a closed set of relation types:

```sql
CREATE TABLE IF NOT EXISTS event_relations (
    relation_id TEXT PRIMARY KEY,
    source_event_id TEXT NOT NULL REFERENCES case_legal_events(event_id),
    target_event_id TEXT NOT NULL REFERENCES case_legal_events(event_id),
    relation_type TEXT NOT NULL,
    created_at TEXT NOT NULL,
    CHECK (source_event_id != target_event_id)
);
```

**Relation types:**

| Relation | Semantics | Example |
|---|---|---|
| AMENDS | Source amends/corrects target (lighter than REPLACES) | Änderungsbescheid amends original Bescheid |
| REPLACES | Source fully replaces target | New decision replaces prior one |
| REVOKES | Source formally revokes target | Rücknahme revokes prior Bescheid |
| CHALLENGES | Source contests target | Widerspruch challenges a Bescheid |
| RESPONDS_TO | Source is a response to target | Gericht responds to Klage |
| EVIDENCES | Source provides evidence for target | Beweismittel submitted for a hearing |
| TRIGGERS_DEADLINE | Source event starts a deadline clock | Bescheid triggers a 4-week appeal deadline |

**Rationale:**
- Relations make the case narrative explicit and machine-readable. Without them, the user
  sees a flat list of events; with them, the system can render a chronological graph showing
  cause and effect.
- Each relation is itself an auditable record — created at a specific time, never silently
  removed (though it may be revoked via the lifecycle pattern).
- The `CHECK` constraint prevents self-referential relations.
- This is a **separate table** (not a self-referencing column on `case_legal_events`) because
  relations are many-to-many: a single Bescheid can trigger multiple deadlines and be
  challenged by a Widerspruch.

---

### Decision 5: Human Review Lifecycle (Identical to ADR-002 Pattern)

Every legal event and every norm-to-case link starts as a **CANDIDATE** and progresses
through the same lifecycle state machine established in ADR-002:

```
CANDIDATE ──(user confirms)──► CONFIRMED ──(user corrects)──► CONFIRMED (previous → CORRECTED)
   │              │                  │
   │              │                  └──(user revokes)──► REVOKED
   │              │
   └──(user rejects)──► REJECTED
```

**Lifecycle states and transitions:**

| State | Meaning | Transition trigger |
|---|---|---|
| CANDIDATE | Auto-detected or user-proposed, not yet reviewed | System detection or user proposal |
| CONFIRMED | User reviewed and accepted; active in timeline | User confirms via UI |
| REJECTED | User reviewed and explicitly rejected | User rejects via UI |
| CORRECTED | User corrected the event details; new CONFIRMED record created | User corrects via UI |
| REVOKED | User withdrew a previous confirmation | User revokes via UI |

**Rationale:**
- This is the identical state machine from ADR-002 (`ConfirmationStatus` enum: UNCONFIRMED,
  CONFIRMED, REJECTED, REVOKED, SUPERSEDED). The M7-A lifecycle uses `CORRECTED` instead of
  `SUPERSEDED` for naming clarity, but both represent the same pattern: a new record replaces
  a previous one while the old record is preserved.
- The API follows the same pattern as `reference_event_routes.py`:
  - Single `POST /legal-events/confirm` endpoint with `action` field (`confirm` | `reject` | `revoke` | `correct`)
  - `GET /legal-events/{event_id}/history` for full audit trail
- All lifecycle transitions follow the POST-only + PRG pattern from ADR-003.
- Idempotency keys from ADR-003 apply to prevent double-submission of confirm/reject/revoke
  actions.

---

### Decision 6: Correction and Revocation Preserve History

When an event is corrected or revoked, the original record is preserved:

```
┌─────────────────────────────────────────────────────┐
│ ORIGINAL RECORD (persists)                           │
│   event_id: "abc-123"                                │
│   lifecycle_status: "corrected"                      │
│   previous_event_id: NULL       ← was the first      │
│   revoked_at: NULL                                   │
│   ...all original field values preserved...          │
└─────────────────────────────────────────────────────┘
                         │
                         │ previous_event_id points to
                         ▼
┌─────────────────────────────────────────────────────┐
│ CORRECTION RECORD (new row)                          │
│   event_id: "def-456"                                │
│   lifecycle_status: "confirmed"                      │
│   previous_event_id: "abc-123"  ← links to original  │
│   occurred_at: "2025-06-15"     ← corrected date     │
│   ...corrected field values...                       │
└─────────────────────────────────────────────────────┘
```

For revocation:
```
   lifecycle_status: "revoked"
   revoked_at: "2026-07-20T14:30:00Z"
   previous_event_id: "abc-123"  ← points to the revoked original
```

**Rationale:**
- This is the direct analogue of `supersedes_confirmation_id` in `confirmed_reference_events`
  (ADR-002). The old record's `lifecycle_status` becomes `"corrected"` (or the correction
  record has `previous_event_id` pointing to it) while the new record carries
  `lifecycle_status: "confirmed"`.
- The `get_active_events_for_case()` repository method uses the same subquery pattern as
  `get_active_confirmation()`: filter out records that are superseded by checking
  `previous_event_id NOT IN (SELECT event_id FROM ...)`.
- For revocation, `revoked_at IS NOT NULL` excludes the event from the active timeline.
- No `UPDATE` ever modifies the original row's content fields — only the status column
  may change (from `confirmed` to `corrected`), and this is acceptable because it
  describes a state change, not a data overwrite.

---

### Decision 7: Derived Timeline as Read Model

The chronological timeline display is a **computed projection**, not a stored table.

```
SELECT event_id, event_type, title, occurred_at, known_at, recorded_at,
       lifecycle_status, previous_event_id
FROM case_legal_events
WHERE case_id = ?
  AND lifecycle_status IN ('confirmed')
  AND revoked_at IS NULL
  AND event_id NOT IN (
      SELECT previous_event_id FROM case_legal_events
      WHERE previous_event_id IS NOT NULL
        AND case_id = ?
  )
ORDER BY occurred_at ASC
```

**Rationale:**
- The `case_legal_events` table is the **single source of truth**. Storing a separate
  materialized timeline would introduce consistency problems — every event mutation would
  need to update both tables.
- The active timeline query is a simple projection with three filters (status, not revoked,
  not superseded) and an `ORDER BY`. For a single-user, single-case workload, this query
  is trivially fast — even with thousands of events, SQLite scans are sub-millisecond.
- This is the same architectural principle as ADR-002's decision to compute
  `CalendarCalculationCandidate` on demand from `confirmed_reference_events` rather than
  storing pre-computed results.
- If performance ever becomes a concern (unlikely for single-user), a SQLite view or
  covering index can be added without changing the domain model.

The timeline **includes** related relations when rendered:
- Each event in the timeline can be decorated with its outgoing relations (AMENDS, CHALLENGES,
  TRIGGERS_DEADLINE, etc.) by joining `event_relations` on `source_event_id`.
- This creates a navigable graph: "This Bescheid triggered a 4-week deadline; that deadline
  was challenged by this Widerspruch; the Widerspruch was responded to by this Gerichtsbescheid."

---

### Decision 8: Connection to Existing History Mechanisms

The case legal timeline **integrates with** — rather than **replaces** — the existing
`confirmed_reference_events` pattern.

**Integration points:**

1. **`DEADLINE_STARTED` events** reference a `confirmation_id` from `confirmed_reference_events`:
   ```sql
   ALTER TABLE case_legal_events ADD COLUMN reference_confirmation_id TEXT
       REFERENCES confirmed_reference_events(confirmation_id);
   ```
   A `DEADLINE_STARTED` event is only valid if the referenced confirmation exists and is
   in `CONFIRMED` state. This enforces that no deadline can be asserted without a
   user-confirmed reference date.

2. **Event provenance:** Legal events can be linked to the documents that evidence them:
   ```sql
   ALTER TABLE case_legal_events ADD COLUMN source_document_id TEXT
       REFERENCES documents(document_id);
   ```
   This is optional — not all events originate from a document (e.g., a manually entered
   hearing date).

3. **No duplicate history system:** Events are NOT stored in `confirmed_reference_events`.
   That table remains dedicated to its M6-A purpose: reference dates for calendar arithmetic.
   Legal events have different semantics (timeline position, relations, temporal dimensions)
   and belong in their own table. The architectural *pattern* is reused; the data is not
   mixed.

4. **Case lifecycle extension:** The `Case` entity's `updated_at` timestamp is updated
   whenever an event is added, corrected, or revoked within that case. In a future build,
   `Case.status` may derive from the event timeline (e.g., `CaseStatus.ACTIVE_APPEAL` when
   the timeline contains a non-revoked `OBJECTION_FILED` event), but no automatic status
   transitions occur in M7-A.

---

### Decision 9: Case-Legal Links (Norm-to-Case Connections)

Norms (legal sources from the M7-A legal source foundation) are linked to cases through
`case_legal_links`, which follows the same lifecycle pattern as legal events:

```sql
CREATE TABLE IF NOT EXISTS case_legal_links (
    link_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    norm_id TEXT NOT NULL,              -- reference to the norm in the legal source table
    norm_citation TEXT NOT NULL,        -- e.g., "§ 70 VwGO"
    link_rationale TEXT NOT NULL DEFAULT '', -- why the user believes this norm applies
    lifecycle_status TEXT NOT NULL DEFAULT 'candidate',
    previous_link_id TEXT,              -- for corrections
    revoked_at TEXT,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL DEFAULT ''
);
```

**Lifecycle:** CANDIDATE → CONFIRMED → CORRECTED → REVOKED (same as legal events).

**Rationale:**
- Norm links connect the abstract legal framework (norms) to the concrete case (events).
  A user may propose: "§ 70 VwGO applies here because this is a Widerspruchsverfahren."
- The lifecycle ensures that norm assignments are auditable. If the user later determines
  that § 73 VwGO is more relevant, they correct the link — the old § 70 assignment is
  preserved with `lifecycle_status: 'corrected'` for traceability.
- The `previous_link_id` column is the direct analogue of `previous_event_id` (events)
  and `supersedes_confirmation_id` (reference events).
- Links are displayed alongside the timeline: when viewing the chronological event list,
  the user can see which norms were associated at each point in time.

---

### Decision 10: No Automatic Legal Effect

Event types are **descriptive labels only**. The system never infers legal consequences
from event types alone.

**Specifically:**

| What the system does | What the system does NOT do |
|---|---|
| Records that the user filed an `OBJECTION_FILED` event on `2026-06-15` | Conclude that the objection was timely (requires human review of `occurred_at` vs. `known_at`) |
| Displays a `DEADLINE_STARTED` event linked to a confirmed reference event | Calculate when the deadline expires or whether it has passed |
| Shows that a `DECISION_REVOKED` event is related to a prior `DOCUMENT_ISSUED` via the REVOKES relation | Determine whether the revocation was lawful or effective |
| Links a norm citation to the case via `case_legal_links` | Assess whether the norm actually applies to this case |

**Rationale:**
- This is a structural enforcement of the constitution's "no automated legal decisions" rule.
- Event types are user-assigned (via confirmation of a candidate or manual entry). The user
  decides what label applies — the system validates only that the label is in the allowed
  enumeration, not that it is legally correct.
- Relations between events (AMENDS, REVOKES, TRIGGERS_DEADLINE) are also user-assigned and
  do not trigger any automatic computation.
- Future builds (M6-B and beyond) may add legal rule profiles that *advise* on deadlines
  based on confirmed reference events and timeline data, but even then, the output will be a
  non-binding calculation preview with mandatory human review flags — matching the
  `CalendarCalculationCandidate.human_review_required=True` pattern from ADR-002.

---

## Alternatives Considered

### Alternative A: Update-in-Place Events (Rejected)

**Approach:** Allow `UPDATE` on `case_legal_events` rows when the user corrects or changes
an event.

| Advantage | Disadvantage |
|---|---|
| Simpler schema, fewer rows | No audit trail — cannot prove what was originally entered |
| Simpler queries (no active/inactive filtering) | Violates legal traceability requirements |
| | Inconsistent with ADR-002's append-only pattern |

**Rejected:** Legal support software must maintain a complete, immutable record of user
actions. The append-only pattern from `confirmed_reference_events` has been validated in M6-A
and there is no reason to abandon it for legal events.

---

### Alternative B: Single "Timeline" Events Table (Rejected)

**Approach:** A single `timeline_entries` table holding all types of timeline data — reference
events, legal events, norm links — in one flat structure with a `type` discriminator column.

| Advantage | Disadvantage |
|---|---|
| One table to query for the timeline | Mixes fundamentally different entities with different columns |
| Simpler schema migration | Null-heavy rows (norm links don't have `occurred_at`) |
| | Violates single-responsibility at the data layer |
| | Makes foreign keys ambiguous (`source_id` could reference any of 3 tables) |

**Rejected:** Legal events, reference events, and norm links have different schemas, different
lifecycle rules, and different query patterns. Separate tables with clear foreign keys are
more maintainable and self-documenting.

---

### Alternative C: Timeline Stored as Materialized JSON (Rejected)

**Approach:** Pre-compute and store the chronological timeline as a JSON blob in a `case_timeline`
column, updated whenever an event changes.

| Advantage | Disadvantage |
|---|---|
| Fast reads (single column fetch) | Requires synchronization logic for every event mutation |
| | Stale data bugs (forgotten update after direct event insert) |
| | Violates single source of truth principle |
| | Inconsistent with ADR-002's compute-on-demand pattern |

**Rejected:** The derived timeline query (Decision 7) is trivially fast for single-user workloads.
Materializing introduces consistency problems without meaningful performance gain.

---

### Alternative D: Automatic Legal Effect Inference (Rejected)

**Approach:** When the user marks an event as `OBJECTION_FILED`, automatically calculate
whether the objection deadline was met based on the preceding `DOCUMENT_RECEIVED` event.

| Advantage | Disadvantage |
|---|---|
| Faster for experienced users | Violates constitution's "no automated legal decisions" rule |
| | Requires legal rule profiles (not yet built in M7-A) |
| | Could mislead users into relying on incorrect automated assessments |
| | Liability risk: software making legal determinations |

**Rejected:** The product is a legal *support* tool, not a legal *decision* tool. All legal
interpretation must be human-initiated and human-reviewed. The event type is a label, not a
trigger.

---

## Consequences

### Positive

1. **Complete audit trail:** Every event and norm link is versioned. The user can always
   reconstruct what they entered, when they corrected it, and what the previous state was.
   This supports the product's goal of traceable legal self-management.

2. **Consistent lifecycle pattern:** The CANDIDATE → CONFIRMED → CORRECTED → REVOKED state
   machine is identical across reference events (M6-A), legal events (M7-A), and norm links
   (M7-A). Developers only need to learn one lifecycle model. API endpoints follow the same
   POST /confirm with `action` field pattern.

3. **Clean separation of temporal concerns:** `occurred_at`, `known_at`, and `recorded_at`
   capture the three distinct time dimensions of legal events. Future legal rule profiles
   can consume these fields independently (e.g., a delivery fiction rule uses `known_at`,
   a Fristbeginn rule uses `occurred_at`).

4. **Single source of truth:** The timeline is always computed from `case_legal_events`.
   There is no cache to invalidate, no stale projection to debug.

5. **Extensible relations:** The `event_relations` table can grow new relation types
   (`PRECEDES`, `FOLLOWS`, `SUPERSEDES_BY_DATE`) without schema changes to the events table.

6. **Forward-compatible with M6-B:** The `DEADLINE_STARTED` event type and `reference_confirmation_id`
   foreign key provide a clean integration point for future legal rule application. When M6-B
   adds BGB/ZPO rule profiles, they can consume confirmed reference events directly through
   the existing `confirmed_reference_events` table.

### Negative

1. **More tables, more joins:** The design adds three new tables (`case_legal_events`,
   `event_relations`, `case_legal_links`). Timeline rendering requires a join across events
   and relations. For the single-user workload, this is negligible; for a hypothetical
   multi-user version, query optimization may be needed.

2. **Event type granularity trade-off:** The 11-event-type enumeration is opinionated.
   Some users may want more granular types (e.g., `BESCHEID_ERLASSEN` vs.
   `URTEIL_VERKUENDET`). The enumeration can be extended, but the closed model means
   every addition requires a code change and migration. A tag-based system (`event_tags`
   table) could be added in the future without breaking the current design.

3. **Norm link table dependency:** `case_legal_links.norm_id` references a norm table that
   does not yet exist in the schema as of this ADR's writing. The foreign key constraint
   must be deferred until the M7-A legal source foundation is implemented, or the column
   must initially be a plain TEXT without a FK. The decision is to add the FK when the
   norm table is created, using a two-phase schema migration.

4. **No automatic timeline pruning:** The append-only model means the `case_legal_events`
   table grows monotonically. For a single case spanning years, this could reach thousands
   of rows. This is well within SQLite's comfort zone (millions of rows), but the query
   pattern (active-only filter + ORDER BY) benefits from a covering index:
   ```sql
   CREATE INDEX idx_cle_active_timeline
   ON case_legal_events(case_id, lifecycle_status, revoked_at, occurred_at);
   ```

### Neutral

1. **Domain event types are in English:** The 11 event types use English identifiers
   (`DOCUMENT_ISSUED`, `OBJECTION_FILED`) while the UI presents German labels. This mirrors
   the existing pattern in `EventType` (ADR-002: `DELIVERY`, `RECEIPT`, etc.). The mapping
   from code identifiers to display labels is handled in the presentation layer.

2. **Three copies of the lifecycle state machine:** The `ConfirmationStatus` pattern now
   exists in `confirmed_reference_events`, `case_legal_events`, and `case_legal_links`.
   This is deliberate — each table has its own domain meaning for the same states. A
   shared lifecycle library or abstract base class could be refactored later if needed,
   but the current copy-paste approach avoids premature abstraction.

---

## References

- [ADR-001 — Local Modular Monolith](adr-001-local-modular-monolith.md)
- [ADR-002 — Confirmed Reference Events and Calendar Arithmetic](adr-002-confirmed-reference-events.md)
- [ADR-003 — Local Confirmation Workspace](../specs/006-local-confirmation-workspace/spec.md)
- [M7-A Reality Refresh](m7a-reality-refresh.md)
- [Domain — ReferenceEvent](src/private_legal_navigator/domain/reference_event.py)
- [Infrastructure — SqliteReferenceEventRepository](src/private_legal_navigator/infrastructure/sqlite_reference_event_repository.py)
- [Application — ReferenceEventService](src/private_legal_navigator/application/reference_event_service.py)
- [API — Reference Event Routes](src/private_legal_navigator/api/reference_event_routes.py)
- [Project Constitution](../../.specify/memory/constitution.md)

---

Verdict: APPROVED
