# RC-025 Drift Analysis

**Generated:** 2026-08-02
**Canonical Worktree:** `/media/xxammaxx/projekte/Rechtssoftware`
**HEAD:** `a6e4c24f8eec0e9df6a4d7e6c1b12f0af70269fc`

## NO_OP_HYPOTHESIS

> "Besteht der geforderte Zielzustand möglicherweise bereits im kanonischen Worktree?"

**Verdict: FALSIFIED.** The required target state does NOT already exist. RC-025 reconciliation work is needed.

## Baseline Metrics

| Metric | Value | Status |
|--------|-------|--------|
| Tests Collected | 1123 | — |
| Tests Passed | 1123 | GREEN |
| Ruff (src + tests) | 25 errors | AMBER |
| Mypy (src) | Clean (73 files) | GREEN |
| pip check (project deps) | Multiple conflicts (hermes/gradio) | AMBER |
| Build (wheel + sdist) | Success (1.0.0rc2) | GREEN |
| Package Version | 1.0.0rc2 | — |
| Python Version | 3.12.3 | — |

## Identified Drift (What's Missing for GREEN_RC025)

### 1. Governance Drift (Phase D)
- AGENTS.md has duplicated `<!-- BEGIN OPENCODE-AGENT-ECOSYSTEM -->` markers (lines 29 and 32)
- Step count: AGENTS.md references "22-step execution order" — needs reconciliation with actual step count
- Network boundary: AGENTS.md line 19 says "Keine externen Laufzeitrequests" but GII sync makes HTTPS requests
- Generic ecosystem sprawl: `ecosystem.manifest.json` contains Tierheim-, Civic-Tech-, Funding-detectors irrelevant to Rechtssoftware

### 2. Skill Drift (Phase C)
- No `.agents/skills/` directory exists
- No `skills-lock.json` exists
- Three required skills (test-driven-development, systematic-debugging, verification-before-completion) not installed
- Skills currently available are global Hermes skills, not project-local

### 3. M7-B Contract Drift (Phase F)
- The M7-B sync code exists in HEAD (inherited from main)
- But contract verification tests are not present:
  - Dry-Run immutability not verified with RED→GREEN tests
  - Plan binding/tamper detection not tested
  - Single-run lock not tested
  - Atomic activation not verified
  - Catalog-Stand-Date semantics not enforced

### 4. Truth Mirror Drift (Phase G)
- README numbers unverified (tests, coverage claims)
- Version numbers may be inconsistent across files
- Release artifacts (`dist/`) are versioned but should be generated-only per RC-025

### 5. Independent Verifier Drift (Phase E)
- No separated verifier worktree or read-only protection
- No acceptance manifest
- No seeded fault tests
- RED reproductions not yet created

### 6. Integration Options (Phase H)
- `docs/architecture/RC025-integration-options.md` not yet created

## Pre-existing Issues (Not Introduced by RC-025)

- Ruff errors in `tests/project_enforcement/` (E402) — pre-existing, untracked test files
- pip check conflicts from hermes-agent and gradio packages — pre-existing venv pollution
- AGENTS.md duplicate markers — pre-existing governance defect
- `ecosystem.manifest.json` generic detectors — pre-existing over-provisioning

## Conclusion

The project is in a **functional state** (1123 tests pass, mypy clean, build succeeds) but has **governance, contract, and verification drift** that RC-025 must repair. The NO_OP hypothesis is falsified — work is required.
