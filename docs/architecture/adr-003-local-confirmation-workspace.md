# ADR-003 — Server-Rendered HTML UI for Confirmation Workspace (M6-UI)

## Status

Proposed

## Context

M6-A delivered JSON API endpoints for reference event confirmation and calendar arithmetic calculation previews. The system has 379 passing tests, 91.04% coverage, and a stable four-layer architecture (API → Application → Domain → Infrastructure).

The M6-UI milestone requires a minimal browser UI for the existing M6-A confirmation gate workflow:

```
Case selection → Document selection → Deadline candidates
→ Reference events → Confirmation (accept/reject/manual/revoke)
→ Calculation preview → History
```

The project constitution and M6-A spec impose hard constraints:
- Fully local processing (no cloud, no CDN, no external requests)
- No automated legal decisions, no binding deadline calculation
- Human review structurally enforced (INV-M6A-03, INV-M6A-11, INV-M6A-12)
- Windows compatibility without additional system dependencies
- No Node.js unless absolutely proven necessary
- Existing 379 tests must continue to pass unchanged
- M6-A domain semantics must not change
- No "Frist" terminology in UI labels (INV-M6A-18)
- `human_review_required=true` and `legal_validity_assessed=false` must be visible

## Decision

**We will implement a server-rendered HTML UI using FastAPI's Jinja2 template support (Variant A).**

New `/ui/` prefixed routes will call the existing Application Services and render HTML templates via Jinja2. The existing `/api/v1/` JSON API remains completely unchanged.

### Key Architectural Decisions

1. **New route prefix `/ui/`** — clear separation from `/api/v1/` JSON API
2. **No new application logic** — UI routes call the same `EventService`, `CaseService`, `DocumentService` as the JSON API
3. **Progressive enhancement** — core workflow works with pure HTML forms; optional JavaScript (~100 lines) adds client-side polish
4. **Strict CSP** — `Content-Security-Policy: default-src 'self'` enforced via middleware
5. **Template auto-escaping** — Jinja2's default HTML escaping prevents XSS from document text
6. **Single new dependency** — `jinja2>=3.1.0` in pyproject.toml (~300KB, maintained by Pallets, 12M+ DL/day)
7. **PRG pattern** — POST → Redirect → GET prevents double submission
8. **Host validation middleware** — rejects non-127.0.0.1 Host headers (DNS rebinding protection)

### Integration Pattern

```
Browser (127.0.0.1:8000)
  │
  ├── GET /ui/cases        → CaseService.list_cases()      → cases.html
  ├── GET /ui/cases/{id}    → CaseService.get_case()        → case_detail.html
  ├── POST /ui/.../confirm  → EventService.confirm()        → redirect
  ├── POST /ui/.../preview  → EventService.calculate()      → calculation_result.html
  ├── GET /ui/.../history   → EventService.get_history()    → confirmation_history.html
  │
  └── (JSON API unchanged)
      GET /api/v1/cases     → same services, JSON output
```

### File Impact

**New files:**
- `src/private_legal_navigator/api/ui_routes.py` (~350 lines)
- `src/private_legal_navigator/templates/` (~8 files, ~620 lines)
- `src/private_legal_navigator/static/css/app.css` (~150 lines)
- `src/private_legal_navigator/static/js/enhance.js` (~100 lines, optional)

**Modified files:**
- `src/private_legal_navigator/app.py` — template configuration, middleware
- `pyproject.toml` — add `jinja2>=3.1.0`

**Unchanged:** All domain, application, infrastructure, and existing API files.

## Variants Evaluated

### Variant A — Server-Rendered HTML (Jinja2) — **SELECTED**

| Criterion | Assessment |
|-----------|-----------|
| Local install | ✅ pip only, no system deps |
| CSP compatibility | ✅ `default-src 'self'` trivially enforceable |
| XSS protection | ✅ Jinja2 autoescaping structural |
| Testability | ✅ same pytest + httpx infrastructure |
| Accessibility | ✅ native HTML forms, no JS required |
| Node.js | ✅ NOT required |
| New dependencies | ✅ 1 (`jinja2`) |
| Security surface | ✅ Lowest |

### Variant B — Static HTML + Vanilla JS

| Criterion | Assessment |
|-----------|-----------|
| Local install | ✅ pip only, zero new deps |
| CSP compatibility | ❌ `'unsafe-inline'` or fragile hashes needed |
| XSS protection | ⚠️ Manual — developer discipline |
| Testability | ⚠️ JS logic needs separate Playwright/jsdom infra |
| Accessibility | ⚠️ Manual focus management required |
| Node.js | ✅ NOT required |
| New dependencies | ✅ 0 |
| Security surface | ⚠️ Higher (manual XSS protection) |

**Rejected:** CSP weakness. "Zero new deps" advantage lost when weighed against JS quality and security risks.

### Variant C — Node.js SPA

| Criterion | Assessment |
|-----------|-----------|
| Local install | ❌ Requires Node.js installation on Windows |
| CSP compatibility | ❌ CSS-in-JS needs `'unsafe-inline'` |
| XSS protection | ⚠️ Framework-dependent |
| Testability | ❌ Separate Jest/Vitest + Playwright infra |
| Accessibility | ⚠️ Virtual DOM breaks native focus |
| Node.js | ❌ Required |
| New dependencies | ❌ 50–500 npm packages |
| Security surface | ❌ Highest (two runtimes) |

**Rejected (ARCH_FAIL):** Violates "No Node.js" constraint. Dramatic over-engineering for a 6-step linear confirmation workflow.

## Consequences

### Positive
- User can complete full M6-A workflow in browser without CLI
- JSON API preserved for programmatic access or future frontends
- CSP enforcement is trivial — strictest possible policy
- XSS protection via Jinja2 autoescaping (structural, not manual)
- Accessibility benefits from semantic HTML and native browser navigation
- Existing test infrastructure reused — `pytest` + `httpx` + `ASGITransport`
- Zero changes to domain, application, or infrastructure layers
- Zero changes to existing API routes or schemas
- Progressive enhancement path: start HTML-only, add JS polish later

### Negative
- One new pip dependency (Jinja2) — mitigated by extreme stability record
- Full-page reloads between steps — mitigated by localhost latency (<5ms)
- Templates add new artifact type — mitigated by standard Python packaging

### Neutral
- New `/ui/` URL namespace alongside `/api/v1/`
- Templates directory in source tree
- Optional static CSS/JS files

## Security Implications

See security-agent threat model (20 threats, SECURITY_PASS_WITH_NOTES). Key mitigations:
1. Jinja2 autoescaping prevents XSS from document text
2. Strict CSP blocks all external resources and inline scripts
3. Host header validation prevents DNS rebinding
4. Cache-Control: no-store prevents browser caching of sensitive data
5. No external resources loaded (CSP-enforced)

## Explicit Boundary to M6-B

The following MUST NOT appear in M6-UI:
- Rule profile selection (BGB, ZPO, VwZG, VwVfG)
- Weekend/holiday adjustment controls
- Delivery fiction selection
- Bundesland selection for Feiertagsgesetze
- Month/year duration arithmetic UI
- Any "Frist" terminology in labels or buttons

The `adjustments` dict renders as a static fact card showing all adjustments as "Nicht angewendet" — this does not change between M6-A and M6-B.

## References

- ADR-001: Lokaler modularer Monolith mit FastAPI + SQLite
- ADR-002: Confirmed Reference Events and Calendar Arithmetic (Variant B)
- M6-A Spec: `specs/006a-reference-events-calendar-arithmetic/spec.md`
- M6-A API Contract: `specs/006a-reference-events-calendar-arithmetic/contracts/api.md`
- Security Threat Model: `specs/006ui-local-confirmation-workspace/checklists/security.md`
- Compliance Audit: 70 UI requirements across 13 sections

---

*ADR-003 authored: 2026-07-17. Next review: before M6-UI implementation begins.*
