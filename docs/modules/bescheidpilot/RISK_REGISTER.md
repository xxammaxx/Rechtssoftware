# Risk Register

| ID | Risiko | Wahrscheinlichkeit | Auswirkung | Status | Mitigation / Evidence |
|---|---|---:|---:|---|---|
| R-01 | Falsche oder übersehene Frist | Hoch | Kritisch | Offen | Fundstellen, Unsicherheit, Human Review, Validierungs-Issues |
| R-02 | Verdeckter Netzwerk- oder Uploadpfad | Mittel | Kritisch | Offen | Network-Deny, Dependency-Scan, Local-only Audit |
| R-03 | Sensible Inhalte in Logs | Mittel | Hoch | Offen | Marker-basierte Logtests, Logging-Policy |
| R-04 | Remote-LLM-/Cloud-OCR-Fallback | Mittel | Kritisch | Offen | Provider-Denylist, Offline-Test, Dependency Gate |
| R-05 | Produkt wird als Rechtsberatung verstanden | Hoch | Hoch | Offen | klare Grenzen, Human Review, Legal Review |
| R-06 | Ungeeignete oder rechtswidrige Testdokumente | Mittel | Hoch | Offen | Fixture- und Anonymisierungspolicy |
| R-07 | Website übertreibt Projektstand | Mittel | Hoch | Mitigation aktiv | Claim-Validator, Evidence-Seite, Public-draft-Status |
| R-08 | Fehlende echte Dokumentvalidierung | Hoch | Hoch | Offen | zwanzig Fälle und Goldstandard |
| R-09 | Fehlende Pilot- und Zahlungsvalidierung | Hoch | Mittel | Offen | Pilotprotokoll; Marktannahmen als Hypothese |
| R-10 | Keine Lizenzentscheidung | Hoch | Mittel | Blockiert | GitHub Issue #9 |
| R-11 | GitHub Pages nicht live ohne Push | Sicher | Mittel | Offen | Pages-Setup nach ausdrücklicher Push-Freigabe |
| R-12 | Inkonsistenter lokaler `gh auth status` | Mittel | Mittel | Offen | Authentifizierung vor unbeaufsichtigter Automation reparieren |
| R-13 | Privates Repository begrenzt öffentliche Evidence | Hoch | Mittel | Offen | öffentliche Evidence-Artefakte oder bewusste Sichtbarkeitsentscheidung vor Investor-Launch |

## Review

Das Register wird bei jedem Milestone-Gate und vor jeder öffentlichen Statusänderung überprüft.
