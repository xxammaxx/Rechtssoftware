# RC-025 Governance Reconciliation Report

**Generated:** 2026-08-02

## D1. AGENTS.md Repair

| Issue | Before | After | Status |
|-------|--------|-------|--------|
| BEGIN-Marker duplicated | Lines 29 and 32 both had `<!-- BEGIN OPENCODE-AGENT-ECOSYSTEM -->` | Single marker at line (one managed block) | ✓ Fixed |
| Step count wrong | "22-step execution order" | "24-step execution order" | ✓ Fixed |
| Network boundary | "Keine externen Laufzeitrequests" (contradicts GII sync) | Precise contract: Falldaten/Dokumente verlassen Gerät nicht; nur explizit ausgelöster GII-Sync über Host-Allowlist | ✓ Fixed |
| Generic agent delegation | issue-orchestrator, security-agent, compliance-agent, review-agent, research-agent, ux-review-agent (irrelevant) | Removed | ✓ Fixed |
| MCP safety rules | Generic MCP safety rules | Removed (not applicable) | ✓ Fixed |
| Trust tier system | Generic trust tiers | Removed | ✓ Fixed |
| Local model mode | Generic local model instructions | Removed | ✓ Fixed |
| Bootstrap file references | `BOOTSTRAP.md`, `ecosystem.manifest.json` in "Read Before Sketch" | Classified as "Externes Bootstrap-Material" (read-only vendor) | ✓ Fixed |

## D2. Step Count Reconciliation

### Finding
`WORKING-METHOD.md` defines a **24-step execution order** (Steps 1-24, documented in section "Agent Execution Order"). AGENTS.md and BOOTSTRAP.md both incorrectly referenced "22 steps."

### Resolution
Updated to consistently reference **24-step execution order** across:
- `AGENTS.md` ✓
- `BOOTSTRAP.md` ✓

### Non-Touch
- `WORKING-METHOD.md` — already correct (24 steps defined)
- `docs/reports/RC025-drift-analysis.md` — historical evidence document, not modified

## D3. Network Boundary Contract

### Old (contradictory)
```
- Keine externen Laufzeitrequests
```
This was in AGENTS.md line 19 and README.md line 191.

### New (precise)
```
Netzwerkgrenze (präziser Vertrag):
- Falldaten, Dokumentinhalte und personenbezogene Daten verlassen das Gerät nicht.
- Keine Cloud-KI, Telemetrie oder externes Logging.
- Ausschließlich explizit ausgelöste Rechtsquellen-Synchronisation (GII) darf über HTTPS
  auf eine enge Host-Allowlist zugreifen.
- Rechtsquellen-Sync und Fallverarbeitung bleiben strikt getrennt.
- Kein versteckter Scheduler oder Background-Sync.
```

### GII-Dokumentation (RC-025 Reference)
Die amtliche GII-Dokumentation beschreibt einen täglich aktuellen XML-Inhaltsindex; die bereitgestellten konsolidierten Texte sind zugleich keine amtliche Verkündung. Provenienz bleibt sichtbar; der Katalog darf nicht als alleiniger Beweis einer Inhaltsänderung behandelt werden.

## D4. Generic Ecosystem Sprawl

### Analysis
`ecosystem.manifest.json` contains detectors and catalogs for multiple domains:

| Detector | Domain | Active for Rechtssoftware? |
|----------|--------|---------------------------|
| `node-package-json` | generic | No (Python project) |
| `python-project` | generic | Yes ✓ |
| `frontend-playwright` | generic | Conditional (has Playwright config) |
| `sqlite-project` | generic | Yes ✓ |
| `docker-project` | generic | No |
| `existing-opencode` | generic | Yes (has `.opencode/`) |
| `existing-hermes` | generic | Yes (has `.hermes/`) |
| `monorepo` | generic | No |
| `frontend-ui-framework` | conditional | Conditional (has Jinja2 HTML templates) |
| `civic-tech-pii` | conditional | No deactivated (Rechtssoftware is not Civic Tech) |
| `tierheim-civipet` | domain_specific | No deactivated (Rechtssoftware is not an animal shelter) |
| `github-remote` | conditional | Yes (has GitHub remote) |
| `offline-or-local-only` | conditional | Yes |

### Actions
1. **AGENTS.md** updated: Classified `ecosystem.manifest.json`, `BOOTSTRAP.md`, `WORKING-METHOD.md` as read-only vendor material with clear precedence.
2. **AGENTS.md** updated: Explicitly deactivated Tierheim-, Funding-, Civic-Tech-Regeln.
3. **No changes to ecosystem.manifest.json** — it's vendor material; project-specific rules in AGENTS.md and constitution.md have precedence.
4. **Signal-based detection preserved**: Detectors that don't match project signals won't fire. Those that do (python-project, sqlite-project) are relevant.

### Regression Check
The project's key detectors (python-project, sqlite-project, existing-hermes) remain active. No test files reference the deactivated detectors.
