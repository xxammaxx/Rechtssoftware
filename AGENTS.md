# AGENTS.md — PrivateLegalNavigator

## Arbeitsprinzipien für Agenten

1. **Local-only**: Fallverarbeitung bleibt vollständig lokal. Keine Cloud-KI, keine Cloud-OCR, keine Cloud-Verarbeitung von Falldaten oder Dokumenten.
2. **Keine Telemetrie**: Keine Analytics, kein Error Tracking, keine Nutzungsdaten.
3. **Datenschutz**: Keine personenbezogenen Daten in Logs, kein Request-Body-Logging.
4. **Keine automatische Rechtsentscheidung**: Die Software bewertet keine Rechtslagen automatisch.
5. **Keine automatische Kommunikation**: Keine automatischen Schreiben an Behörden oder Dritte.
6. **Human Review**: Jede rechtlich relevante Ausgabe erfordert menschliche Prüfung.
7. **Lokale Tests als Primärwahrheit**: Der Zustand von Repo, Code, Tests und lokaler Runtime hat Vorrang vor Dokumentation oder Erinnerung.
8. **Kein Remote-CI ohne Freigabe**: GitHub Actions, Remote-CI, Auto-Merge sind ohne ausdrückliche Freigabe verboten.
9. **Kein Push oder Merge ohne Freigabe**: Lokale Commits sind erlaubt; Remote-Operationen nicht.
10. **Spec-Kit-gesteuert**: Der Entwicklungsprozess folgt dem Spec-Kit-Ablauf (constitution → specify → clarify → plan → tasks → analyze → implement).

## Sicherheitsgrenzen

- Backend bindet standardmäßig nur an 127.0.0.1
- Parametrisierte SQL-Abfragen (keine Stringverkettung)
- Keine Secrets im Repository
- Keine produktiven oder personenbezogenen Testdaten
- Testdaten beginnen mit dem Präfix "SYNTHETISCH –"

## Netzwerkgrenze (präziser Vertrag)

- **Falldaten, Dokumentinhalte und personenbezogene Daten verlassen das Gerät nicht.**
- Keine Cloud-KI, Telemetrie oder externes Logging.
- Ausschließlich explizit ausgelöste Rechtsquellen-Synchronisation (GII) darf über HTTPS auf eine enge Host-Allowlist zugreifen.
- Rechtsquellen-Sync und Fallverarbeitung bleiben strikt getrennt.
- Kein versteckter Scheduler oder Background-Sync.

## Architektur

Modularer Monolith mit FastAPI und SQLite. Schichten: API → Application → Domain → Infrastructure.

<!-- BEGIN OPENCODE-AGENT-ECOSYSTEM -->
> **Canonical Working Method:** The full 24-step execution order, risk tiers, context levels, verification contracts, and owner approval gates are defined in [`WORKING-METHOD.md`](WORKING-METHOD.md). This file provides project-specific agent rules that supplement the canonical method. In case of conflict, `WORKING-METHOD.md` prevails.
<!-- END OPENCODE-AGENT-ECOSYSTEM -->

## Source Of Truth

- Prefer a GitHub issue as the source of truth when GitHub context is available.
- For local diagnostics, dry-runs, and tool-gap analysis, the local run report is the temporary source of truth.
- Never claim that you read an issue if GitHub access was unavailable.

## Default Run Order

For larger bootstrap, architecture, or integration work, use the [Canonical 24-Step Execution Order](WORKING-METHOD.md#agent-execution-order) defined in `WORKING-METHOD.md`. The abbreviated summary is:

1. Reality Refresh → Context Manifest → Research → Planning → Architecture
2. **Security** → **Compliance** (Security runs BEFORE Compliance)
3. Verification Contract → Red Tests → Owner Approval
4. Implementation → Local Validation → Reality Gate
5. Living Truth Mirror → Reviewer → Evidence-Abschluss
6. Commit Gate → Push Gate → PR Gate → Merge Gate → Deployment Gate

## Read Before Sketch

For architecture, APIs, SDKs, providers, security, CI/CD, MCP, data models, external tools, or other non-trivial changes:

1. Read the relevant project instructions first, including `AGENTS.md`, `SECURITY.md`, and any task-specific notes.
2. Read the linked issue or local run report in full before sketching a plan.
3. Read the affected repository files, tests, and docs before editing.
4. Check current official documentation when external APIs, SDKs, providers, MCP, or security are involved.
5. Summarize validated facts and explicit uncertainties before proposing changes.
6. Run the relevant checks or explain why they could not run.

## Spec-Driven Development Mandate

The Speckit workflow intensity depends on the Risk Tier (see `WORKING-METHOD.md` for full risk tier definitions):

| Risk Tier | Speckit Scope | Verification Contract |
|-----------|---------------|----------------------|
| **LOW_LOCAL** | Lightweight Spec (goal, scope, acceptance criteria only) | Mandatory |
| **MEDIUM_REVIEW** | Spec + Plan + Tasks | Mandatory |
| **HIGH_HUMAN_GATE** | Full Speckit (Constitution → Specify → Plan → Tasks) + GitHub Issues | Mandatory |
| **CRITICAL_BLOCK** | ❌ No implementation until blocker is resolved | N/A |

**Gate:** No code without completed specification, acceptance criteria, and tests defined.

## Evidence-Gated Progression

Before claiming:

- **Severity** → CVSS vector + PoC reproduction + log evidence
- **Architecture Decision** → ADR documented + dependency analysis
- **Migration Ready** → Rollback tested + data integrity verified
- **Bug Fixed** → Test passes + regression test added
- **Feature Complete** → Acceptance criteria met + test coverage maintained
- **DSGVO/GDPR Compliant** → Data flow diagram + consent verified + retention enforced

## Prohibited Actions (Always)

- Never implement from memory without validating the local repository state.
- Never commit `*.db`, `*.db-shm`, `*.db-wal`, `.env`, or secrets.
- Never skip the GitHub comment cycle when an issue exists.
- Never modify canonical production data autonomously.
- Never claim severity without evidence.
- Never skip the Speckit workflow for features.

## Externes Bootstrap-Material

Die folgenden Dateien sind gepinnte externe Referenzen aus dem OpenCode-Hermes-Agent-Bootstrap und gelten als read-only Vendor-Material. Sie definieren den generischen Agenten-Workflow, sind aber nicht projektspezifisch für Rechtssoftware:

- `WORKING-METHOD.md` — Kanonische 24-Schritt-Arbeitsmethode (read-only Referenz)
- `BOOTSTRAP.md` — Bootstrap-Anleitung (nur als Dokumentation)
- `ecosystem.manifest.json` — Generisches Ökosystem-Manifest (nur zur Referenz; projektspezifische Regeln in AGENTS.md und `.specify/memory/constitution.md` haben Vorrang)

Nicht aktiv für Rechtssoftware: Tierheim-Detektoren, Funding-Dokument-Generatoren, Civic-Tech-Regeln, generische Agenten-Kataloge aus `ecosystem.manifest.json`. Die aktiven Projektregeln sind minimal und projektbezogen.

## Security & Compliance

Load these files on relevant tasks:

- `SECURITY.md`
- `.specify/memory/constitution.md`

**Important:** Security runs BEFORE Compliance in the agent execution order. Security findings can invalidate compliance assessments — a system that is insecure cannot be DSGVO-compliant (Art. 32 DSGVO). See [WORKING-METHOD.md: Security Before Compliance](WORKING-METHOD.md#security-before-compliance).
