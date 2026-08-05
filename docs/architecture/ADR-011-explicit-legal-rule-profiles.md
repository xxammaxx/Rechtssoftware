# ADR-011 — Explicit Legal Rule Profiles

**Status:** Proposed — requires owner approval before implementation.

## Decision

Legal rules are immutable, versioned profiles selected and confirmed explicitly by a human. No default, heuristic or contextual auto-selection exists. A profile contains source citation, temporal validity, jurisdiction, prerequisites and exclusions.

## Consequences

- Positive: the product does not silently decide which law governs.
- Cost: a user/reviewer must make and document a choice; unsupported scenarios remain blocked.
- Revocation blocks future use without rewriting prior provenance.
