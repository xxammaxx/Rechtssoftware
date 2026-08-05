# ADR-013 — Temporal Validity and Provenance

**Status:** Proposed — requires owner approval before implementation.

## Decision

Every holiday record and rule profile is versioned with `valid_from`, optional `valid_to`, official source URL, source hash and review metadata. A trace references exact versions. Missing or non-covering validity is a blocking condition, never a fallback to “current”.

## Consequences

Historic calculations remain explainable; source updates append a version. This increases review and data-maintenance work but avoids silent legal drift.
