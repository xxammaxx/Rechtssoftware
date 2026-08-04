# Spec — M6-B Calendar Context and Versioned Legal Rule Profiles

**Status:** `M6B_SPEC_READY_AWAITING_OWNER_APPROVAL`
**Local Spec-Kit identifier:** 010 (no GitHub issue is assigned)
**Scope of this document:** specification only — no product code, migration, holiday JSON, UI, or legal calculation is created by this milestone.

## Purpose

M6-A deliberately produces only a mathematical calendar-date preview. M6-B defines the next safe boundary: calendar context, locally versioned holiday-source data, and explicitly selected legal rule profiles. It does not turn the application into a legal adviser and it does not choose, activate, or apply a legal profile silently.

The output remains a reviewable calculation candidate. A human must supply and confirm the factual inputs and explicitly select a profile before a later implementation can evaluate any legal rule.

## Product invariants

| ID | Invariant |
|---|---|
| INV-M6B-01 | No result is a legally binding deadline or legal advice. |
| INV-M6B-02 | A weekend may be displayed as calendar context without asserting a legal shift. |
| INV-M6B-03 | A holiday may be displayed only when a locally installed, integrity-verified dataset and an explicit jurisdiction are present. |
| INV-M6B-04 | The system must never infer Bundesland, municipality, court, delivery method, posting date, or receipt date. |
| INV-M6B-05 | Every rule profile is explicitly selected by a human; the default is `NO_PROFILE_SELECTED`. |
| INV-M6B-06 | A selected profile remains an input to a calculation trace, not proof that it is the correct legal rule. |
| INV-M6B-07 | Rule profiles carry norm citation, jurisdiction, version, temporal validity, provenance and review state. |
| INV-M6B-08 | A profile whose validity is unknown or does not cover the reference date must not be applied. |
| INV-M6B-09 | A missing, revoked, conflicting or unsupported profile produces structured warnings and no legal conclusion. |
| INV-M6B-10 | Dataset and rule-profile content are local, static and versioned; runtime network access is forbidden. |
| INV-M6B-11 | Dataset integrity is checked before a later rule engine may consume it. |
| INV-M6B-12 | Calculation traces record input facts, selected versions, every mathematical step, every rule step, warnings and non-application. |
| INV-M6B-13 | Mathematical operations and legal-rule operations are separate trace step types. |
| INV-M6B-14 | Delivery and announcement fictions are excluded from the first M6-B build. |
| INV-M6B-15 | A presumed delivery or announcement date is never auto-confirmed. |
| INV-M6B-16 | No case text, names, addresses or input dates may be emitted to logs. |
| INV-M6B-17 | Tests use only data beginning with `SYNTHETISCH –`. |
| INV-M6B-18 | Revoking a profile invalidates future use and makes prior trace provenance visible; it does not rewrite history. |

## Slices and dependency decision

The earlier suggestion “M6-B.3 first” is rejected. A profile that refers to a state-recognised general holiday cannot be safely evaluated without a dated, jurisdiction-bound holiday source. The implementation order is therefore:

1. **M6-B.2 — Holiday Data Foundation (first build slice):** provenance model, local static source package contract, integrity verification and date/jurisdiction lookup interface. No shipped holiday dataset in this milestone.
2. **M6-B.1 — Calendar Context:** display weekend and, where source data exists, holiday context with an explicit “no legal adjustment performed” state.
3. **M6-B.3 — Versioned Rule Profiles:** explicit profile selection, validity/provenance gates and trace composition. A later owner-approved implementation may initially support only one narrowly scoped profile.
4. **M6-B.4 — Delivery and Announcement Fictions:** separate future specification and owner gate. It is not a feature of the first M6-B build.

This is an architecture dependency, not a legal conclusion about any individual case.

## User stories and acceptance criteria

### US-01 — Calendar context (M6-B.1, P1)

As a user, I can see whether a candidate date is Saturday, Sunday or a documented holiday context, without the product claiming that the date changes.

- The output contains the ISO date, weekday and `weekend=true|false`.
- A weekend produces `WEEKEND_CONTEXT_ONLY`, never an automatic shift.
- A holiday label requires an explicitly selected Bundesland and verified dataset version.
- Missing jurisdiction or dataset produces a visible warning, not a guessed holiday result.

### US-02 — Holiday source provenance (M6-B.2, P1)

As a reviewer, I can determine which local dataset and official source support a displayed holiday.

- Every record has source URL, authority, source retrieval/review date, `valid_from`, `valid_to`, jurisdiction and content hash.
- The package manifest has a dataset version and SHA-256 integrity value.
- Invalid or expired source coverage blocks legal-rule use.
- No runtime download occurs.

### US-03 — Explicit rule profile (M6-B.3, P1)

As a user, I can deliberately select a narrow rule profile and see its limits before any later calculation.

- The UI/API cannot select a profile implicitly.
- Selection requires a profile id, version, jurisdiction/context and a human confirmation action.
- Profile labels state norm citation, temporal validity, assumptions and exclusions.
- Unsupported legal area or conflicting selection stops the operation with a structured warning.

### US-04 — Reviewable trace (M6-B.1–B.3, P1)

As a reviewer, I can reconstruct what was mathematical context and what was a selected legal-rule step.

- The trace includes immutable input snapshot identifiers rather than copied document text.
- Each step declares `MATHEMATICAL`, `CALENDAR_CONTEXT`, `HOLIDAY_LOOKUP`, `LEGAL_PROFILE`, or `NOT_APPLIED`.
- Warnings remain structured and visible at top level and per step.
- Every output says `human_review_required=true` and `legal_validity_assessed=false` unless a later separately approved legal-assessment policy changes that invariant.

### US-05 — Revoke selection (M6-B.3, P2)

As a user, I can revoke a profile selection and prevent its later reuse.

- Revoke is explicit and auditable.
- Future application is blocked with `RULE_PROFILE_REVOKED`.
- Existing traces retain the profile version and revoke relationship for review.

## Functional requirements

| ID | Requirement |
|---|---|
| FR-M6B-001 | The first implementation must provide the versioned holiday-dataset contract before any profile consumes holidays. |
| FR-M6B-002 | Weekend context must be computed from ISO calendar data only and labelled non-legal. |
| FR-M6B-003 | Holiday lookup requires a user-supplied jurisdiction and date within source validity. |
| FR-M6B-004 | A data package must include a manifest, record schema version, content hash and official provenance references. |
| FR-M6B-005 | A holiday record must distinguish state-wide, local/municipal and unknown scope; unknown scope cannot establish a legal adjustment. |
| FR-M6B-006 | Rule profiles must be immutable versioned definitions, not editable free text. |
| FR-M6B-007 | A profile must name the applicable norm down to paragraph/sentence where applicable. |
| FR-M6B-008 | The application must require an explicit human selection and confirmation timestamp before a profile can be considered. |
| FR-M6B-009 | Profile matching must not infer jurisdiction, delivery channel or factual trigger. |
| FR-M6B-010 | Expired, future, unsigned/invalid, unknown or contradictory profile data must not be applied. |
| FR-M6B-011 | Every candidate must expose `warnings`, `trace`, `human_review_required`, and `legal_validity_assessed`. |
| FR-M6B-012 | The future implementation must preserve M6-A’s append-only confirmation/revocation semantics. |
| FR-M6B-013 | Delivery and announcement fictions must return `DELIVERY_FICTION_OUT_OF_SCOPE` in the first M6-B build. |
| FR-M6B-014 | The product must remain local-only and make no external requests during operation or tests. |
| FR-M6B-015 | No production holiday data, database migration or endpoint is permitted until owner approval for implementation. |

## Explicit exclusions

- No automatic choice of BGB, ZPO, VwVfG, VwZG or any other norm.
- No assertion that a state holiday is legally relevant to a particular declaration, performance place, court proceeding or authority procedure.
- No delivery, access, announcement, posting, receipt or mailbox fiction.
- No calculation of limitation, appeal, procedural or substantive-law periods as legally binding.
- No automatic jurisdiction or municipality selection.
- No cloud API, cloud OCR, telemetry or remotely updated holiday feed.
- No legal dataset in this specification commit.

## Success criteria for implementation approval

Before implementation begins, the owner must approve this specification and the selected first slice. The implementation plan must then show: an official-source review for every shipped record; red tests listed in `tasks.md`; integrity and rollback tests; Security review before Compliance review; local quality gates; and a UI accessibility contract.
