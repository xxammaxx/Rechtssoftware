# Requirements Checklist — M6-UI (Hardened)

## Specification Completeness

- [x] User Stories (7 stories, P1–P2) — with neutral terminology
- [x] Action-Semantik-Tabelle (UI action → Domain command → SourceType mapping)
- [x] UI-Zustandsmodell (12 states) — no invented states; loading states omitted (server-rendered)
- [x] Funktionale Anforderungen (20 FRs)
- [x] Negativpfade (17 scenarios)
- [x] Product Invariants (15 UI-specific, 7 inherited from M6-A)
- [x] CSRF-Schutz-Spezifikation (Token-Modell, Rotation, constant-time, Origin, Testfaelle)
- [x] Host-Header-Validierung (konfigurierbar aus Settings)
- [x] Preview-Vertrag (Server-seitige Revalidierung, Cross-Resource-Check)
- [x] Idempotenz-Mechanismus (server-seitig, key-binding, atomic)
- [x] Architecture Decision (ADR-003) — mit Application-Layer-Entscheidung
- [x] Research (FastAPI, Jinja2, CSP, CSRF, Same-Origin Policy, Idempotency, DNS Rebinding)
- [ ] Architecture Review (delegated to architecture-agent)
- [x] Plan (implementation strategy, risk assessment, test tool strategy)
- [x] Tasks (23 tasks, dependency graph)
- [x] Data Model (view models, source-of-truth mapping, translation tables)
- [x] API Contracts (ui-routes, view-models, security-headers)
- [ ] Security Review (delegated to security-agent)
- [ ] Compliance Review (delegated to compliance-agent)
- [ ] Reviewer Gate (delegated to review-agent)
- [x] Test Strategy (unit, integration, E2E, accessibility)
- [x] Test Tools: clear distinction between product deps, dev deps, browser runtime
- [x] Accessibility Strategy: axe-core vendored, NVDA manual gate
- [x] Success Criteria (10 criteria)
- [x] Explicit exclusions (14 items)
- [x] Boundary to M6-B

## Gate Readiness

- [x] Truth Mirror updated (README reflects spec status)
- [x] Clean baseline verified: `c20240e`
- [x] Branch: `spec/006ui-local-confirmation-workspace-hardened` from `c20240e`
- [x] ADR-003 complete with Application-Layer decision
- [x] All 10 blockers addressed in spec documents
- [ ] Research Agent Gate passed
- [ ] Architecture Agent Gate passed
- [ ] Security Agent Gate passed
- [ ] Compliance Agent Gate passed
- [ ] Review Agent Gate: APPROVED
- [ ] Baseline tests unchanged (verified at end)
- [ ] Ruff: 0 errors
- [ ] Mypy: 0 errors
- [ ] pip check: green
- [ ] Coverage ≥ 90%

## Blocker Resolution Status

| # | Blocker | Status |
|---|---------|--------|
| 1 | Veraltete Architektur/entfernte Module | Spec referenziert nur kanonische Clean-Baseline-Typen |
| 2 | Preview-Contract unvollstaendig | Vollstaendiger Server-seitiger Revalidierungs-Flow spezifiziert |
| 3 | CSRF ("N/A") | Expliziter Signed-Token-CSRF-Mechanismus mit Origin-Prüfung |
| 4 | Host-Header hartcodiert | Konfigurierbare Allowlist aus Settings |
| 5 | CSP (Meta-Tag) | CSP ausschliesslich als HTTP-Header; kein Meta-Tag |
| 6 | Double Submit/Idempotenz | Server-seitige Idempotency-Keys mit atomarem Check-and-Set |
| 7 | Terminologie | Neutrale Systemlabels; Dokumentinhalte unveraendert |
| 8 | Action-Semantik | Action-Mapping-Tabelle; kein erfundener API-Wert |
| 9 | Erfundene Zustaende | Source-of-Truth-Mapping fuer jedes UI-Feld |
| 10 | Testwerkzeuge | Klare Trennung: Produkt/Dev/Browser-Runtime/Accessibility |
