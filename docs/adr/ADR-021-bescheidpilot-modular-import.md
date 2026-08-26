# ADR-021: BescheidPilot modular import first

## Status

Accepted — `MODULAR_IMPORT_FIRST`, runtime convergence deferred until verification.

## Context

`BescheidPilot` contains a distinct local-only notice-analysis vertical slice with
its own evidence, redaction, network-deny guardrails, synthetic fixtures and web
demo. `Rechtssoftware` already owns the broader PrivateLegalNavigator runtime.
Directly replacing or renaming the existing runtime would make provenance and
regression boundaries unclear.

## Decision

Import the BescheidPilot slice under `src/bescheidpilot/`, with its tests under
`tests/bescheidpilot_*.py`, its site and contracts under
`docs/modules/bescheidpilot/`, and namespaced helper scripts. Existing
`private_legal_navigator` modules are not overwritten.

Runtime convergence may be considered only after independent verification of
contracts, security boundaries, test coverage and an explicit follow-up ADR.

## Consequences

- Source provenance remains visible at module and test boundaries.
- BescheidPilot's offline and human-review invariants remain independently testable.
- Duplicate concepts may exist temporarily; this is intentional until convergence evidence exists.
- The target's `src` pytest path is declared explicitly in `pyproject.toml`.

## Evidence

- Source HEAD: `f9e674f57908e13713580a10a848108e106baa8e`
- Target start HEAD: `a26968bb3ea10394edc27e410f25280950e9d7a2`
- Source tests: 284 passed, 332 subtests passed
- Modular target tests: 284 passed, 332 subtests passed
- Modular Ruff: PASS
- Full target regression: 1,087 passed; 4 pre-existing Frozen-RED tests fail identically against `origin/main`
