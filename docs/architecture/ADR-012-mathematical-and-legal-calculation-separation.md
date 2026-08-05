# ADR-012 — Separation of Mathematical and Legal Calculation

**Status:** Proposed — requires owner approval before implementation.

## Decision

Keep pure calendar operations, calendar context and legal-profile operations as different trace steps. A weekend/holiday display does not itself change a candidate date. Legal-profile steps can occur only after explicit selection and prerequisite validation.

## Consequences

This preserves the M6-A boundary, makes non-application visible and prevents a date library from being misrepresented as legal reasoning.
