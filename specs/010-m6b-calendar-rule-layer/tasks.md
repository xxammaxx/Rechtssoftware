# Tasks — M6-B Calendar Context and Versioned Legal Rule Profiles

## Specification tasks — completed in this closure run

- [x] T001 — Check M6-A/M6-UI boundaries and existing ADRs.
- [x] T002 — Re-measure v0.2.1 local quality and installed-wheel gates before M6-B specification.
- [x] T003 — Research official federal sources for § 193 BGB, § 222 ZPO, § 41 VwVfG and § 4 VwZG.
- [x] T004 — Define state-holiday source registry and version/provenance requirements without shipping data.
- [x] T005 — Reject M6-B.3-first ordering; select M6-B.2 → M6-B.1 → M6-B.3.
- [x] T006 — Define product boundaries and Human Gates.
- [x] T007 — Define contracts, data model, warning codes and red-test plan.
- [x] T008 — Record four ADRs.

## Implementation tasks — future only, owner approval required

### Gate 0 — owner and source readiness

- [ ] T101 — Assign/confirm a GitHub issue; no issue state is changed by this specification.
- [ ] T102 — Owner approves the selected first slice and legal/product boundaries.
- [ ] T103 — Legal reviewer validates each exact official source and each record to be shipped.
- [ ] T104 — Security review of data package/update/rollback design.
- [ ] T105 — Compliance review after Security approval.

### M6-B.2 — Holiday Data Foundation

- [ ] T110 — Write red tests for invalid manifest, missing hash, invalid validity range and unreviewed source.
- [ ] T111 — Define immutable domain models and local package parser.
- [ ] T112 — Implement local-only integrity validation and provenance lookup.
- [ ] T113 — Test package rollback and source-version preservation.

### M6-B.1 — Calendar Context

- [ ] T120 — Write red tests for weekend context, missing jurisdiction and unknown holiday coverage.
- [ ] T121 — Implement non-legal context/trace representation.
- [ ] T122 — Add accessible UI/API display only after acceptance of terminology and warnings.

### M6-B.3 — Versioned Rule Profiles

- [ ] T130 — Write red tests for no selection, revoked/expired/conflicting profile and unsupported legal area.
- [ ] T131 — Implement explicit selection/revocation and immutable calculation trace.
- [ ] T132 — Implement only an owner-approved narrow profile, with source version and Human Gate.

### Deferred M6-B.4

- [ ] T140 — Create separate specification for delivery/announcement fictions before product work.

### Final future gates

- [ ] T150 — Run full local test, lint, typing, dependency, coverage and browser accessibility gates.
- [ ] T151 — Independent read-only review.
- [ ] T152 — Owner approval for any remote operation (none is implied).
