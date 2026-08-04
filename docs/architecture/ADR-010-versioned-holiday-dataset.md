# ADR-010 — Versioned Holiday Dataset

**Status:** Proposed — requires owner approval before implementation.
**Context:** M6-B needs state-specific holiday context without cloud data or untraceable calendar tables.

## Decision

Use a local static, versioned dataset package with a manifest SHA-256 and record-level official-source provenance, jurisdiction, scope and temporal validity. Do not use runtime APIs or a generic holiday library as legal provenance.

## Consequences

- Positive: local operation, reproducibility and historic traceability.
- Cost: every shipped record needs source review and a controlled release/update process.
- Guardrail: unknown local scope or invalid validity blocks a legal-profile step.

## Alternatives rejected

- Cloud holiday API: violates local-only and reproducibility requirements.
- Unversioned table: cannot explain historic results.
- Generic library as source: cannot prove applicable statute/version/scope.
