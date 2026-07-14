# HERMES SNAPSHOT S1 — M6A SPECIFICATION REPAIRED

## Snapshot Metadata
- **Snapshot**: S1 (Corrected)
- **Phase**: LEGAL_SOURCE_COMPLIANCE_REPAIR (Complete)
- **Timestamp**: 2026-07-14T14:00:00Z
- **Agent**: issue-orchestrator (deepseek-v4-pro)
- **Previous Snapshot**: S0 (M5 Merged Baseline)

## System Reality
| Property | Value |
|----------|-------|
| OS | Microsoft Windows 10 Pro Education |
| Shell | PowerShell 5.1.19041.6456 |
| Working Directory | C:\Rechtssoftware |

## Git Reality (Final)
| Property | Value |
|----------|-------|
| Local main SHA | acf6995c32c5d06d22129581ec24faae8220edc2 |
| Remote main SHA | acf6995c32c5d06d22129581ec24faae8220edc2 |
| Local = Remote | YES |
| Spec Branch | spec/006a-reference-events-calendar-arithmetic |
| Original Spec Branch SHA | 6f9f8039e675c4e1fbc8063b27cf30658bdd9482 |
| Repair Commit SHA | 6aac7a4 (spec repair) |
| Snapshot Commit SHA | (recorded in follow-up commit) |

## Remote Reality (Final)
| Property | Value |
|----------|-------|
| Issue | #3 — M6-A (OPEN) |
| Draft-PR | #4 — spec: define M6-A (DRAFT, OPEN) |
| GitHub Actions | 0 workflows, 0 runs |

## Baseline Gates (post-repair)
| Gate | Result |
|------|--------|
| Tests | 165/165 passed |
| Coverage | 95.82% |
| Ruff | PASS |
| Mypy | PASS |
| pip check | PASS |

## Spec Gates (post-repair)
| Gate | Status |
|------|--------|
| Research | RESEARCH_PASS_WITH_NOTES (8 source documents) |
| Spec-Kit | SPEC_GREEN |
| Architecture | ARCH_PASS_WITH_NOTES (Variant B, product/safety rationale) |
| Security | SECURITY_PASS_WITH_NOTES |
| Compliance | COMPLIANCE_PASS_WITH_NOTES |
| Reviewer | 0 Critical, 0 Major, 2 Minor, 4 Notes |

## Repairs Applied
| # | Repair | Files Affected |
|---|--------|---------------|
| 1 | Source classification methodology established | research.md |
| 2 | dejure.org reclassified as SECONDARY_SOURCE | research.md |
| 3 | Source counts corrected (5+1+1+1=8 vs. 20+) | research.md, tasks.md, checklists, report |
| 4 | Art. 30 removed as event-level journal justification | adr-002, data-model.md, report |
| 5 | Art. 22 marked deployment-context-dependent | adr-002, research.md |
| 6 | No universal Art. 6 legal basis asserted | data-model.md |
| 7 | Data minimization claims match schema | adr-002, data-model.md |
| 8 | Variant B rejustified on product/safety criteria | adr-002, data-model.md |
| 9 | source_text removed from audit data; offsets used | research.md, adr-002 |
| 10 | FK redundancy removed; source_type default fixed | adr-002, data-model.md |
| 11 | 8 new data protection invariants added | spec.md |
| 12 | confirmed_by documented as optional label | spec.md, data-model.md |
| 13 | Report classification unified to SPEC_REPAIRED | report |

## Deliverables
| Deliverable | Location |
|-------------|----------|
| Research (corrected) | `specs/006a-.../research.md` |
| Specification (corrected) | `specs/006a-.../spec.md` |
| Data Model (corrected) | `specs/006a-.../data-model.md` |
| API Contract | `specs/006a-.../contracts/api.md` |
| Plan | `specs/006a-.../plan.md` |
| Tasks (corrected) | `specs/006a-.../tasks.md` |
| Test Vectors | `specs/006a-.../test-vectors.md` (64 vectors) |
| Checklist (corrected) | `specs/006a-.../checklists/requirements.md` |
| ADR-002 (corrected) | `docs/architecture/adr-002-...` |
| Final Report (corrected) | `docs/reports/M6A-research-spec-architecture.md` |

## Product Code Status
**NO product code was changed.** Only specification and documentation artifacts
(specs/, docs/) were modified. src/, tests/, pyproject.toml untouched.

## Final Status
**SPEC_REPAIRED_AWAITING_OWNER_APPROVAL**

The M6-A specification has been repaired to correct legal source classification,
GDPR compliance claims, data minimization accuracy, and architecture justification.
Variant B is retained as a product/safety decision. No statutory claims remain
that are not supported by official primary sources or clearly marked as
context-dependent.
