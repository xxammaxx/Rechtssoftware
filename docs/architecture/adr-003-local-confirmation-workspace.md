# ADR-003 — Local Confirmation Workspace UI (M6-UI)

## Status

Accepted (Slice 1 + Slice 2 + Slice 4 implemented; Slice 3 pending)

## Context

M6-A delivered JSON API endpoints for reference event confirmation and calendar arithmetic previews via `ReferenceEventService` and `CalculationService`. The system has a stable four-layer architecture (API → Application → Domain → Infrastructure).

The M6-UI milestone requires a minimal browser UI for the existing M6-A confirmation gate workflow:

```
Case selection → Document selection → Zeitangaben-Kandidaten
→ Bezugsereignisse → Confirmation (accept/reject/manual/revoke)
→ Rechenvorschau → History
```

Hard constraints from project constitution and M6-A spec:
- Fully local processing (no cloud, no CDN, no external runtime requests)
- No automated legal decisions, no binding deadline calculation
- Human review structurally enforced (INV-M6A-03, INV-M6A-11, INV-M6A-12)
- Windows compatibility without additional system dependencies
- Existing tests must continue to pass unchanged
- M6-A domain semantics must not change
- System labels must distinguish between detected document text and legal assessment

## Decision

**Variant A: Server-Rendered HTML UI using FastAPI + Jinja2 templates.**

New `/ui/` prefixed routes call existing Application Services and render HTML. The existing `/api/v1/` JSON API is unchanged.

### Key Architectural Decisions

1. **New route prefix `/ui/`** — clear namespace separation from `/api/v1/`
2. **No new application logic** — UI routes call the same `ReferenceEventService`, `CalculationService`, `CaseService`, `DocumentService` as the JSON API
3. **Application-layer orchestration** — a dedicated `LocalConfirmationWorkspaceService` (application layer) will be defined during implementation to coordinate existing M6-A services and produce UI-specific read models. It MUST NOT duplicate business logic or access infrastructure repositories directly.
4. **Progressive enhancement** — core workflow functions with pure HTML forms + PRG pattern; optional JavaScript (~100 lines) adds client-side UX polish
5. **Strict CSP as HTTP header only** — `Content-Security-Policy` delivered via response header, never via `<meta>` tag
6. **Template auto-escaping** — Jinja2's default HTML escaping prevents XSS from document text
7. **Single new product dependency** — `jinja2>=3.1.0` in pyproject.toml
8. **CSRF protection** — cryptographically random token, hidden form field, constant-time comparison, token rotation, Origin header validation, Referer fallback
9. **Idempotency** — action-specific idempotency keys for all state-changing POST operations, bound to expected prior state
10. **Configurable host validation** — allowed hosts derived from Settings, not hard-coded

### Integration Pattern

```
Browser (127.0.0.1:{port})
  │
  ├── GET  /ui/cases              → CaseService                    → cases.html
  ├── GET  /ui/cases/{id}         → CaseService + DocumentService  → case_detail.html
  ├── GET  /ui/.../workspace      → DeadlineService + ReferenceEventService → workspace.html
  ├── POST /ui/.../confirm        → ReferenceEventService.confirm_with_idempotency() → redirect
  ├── POST /ui/.../reject         → ReferenceEventService.reject_with_idempotency() → redirect
   ├── POST /ui/.../manual-confirm → ReferenceEventService.confirm_with_idempotency() → redirect
   ├── [planned: Slice 3] POST /ui/.../correct → ReferenceEventService.correct() → redirect
   ├── [planned: Slice 3] POST /ui/.../revoke  → ReferenceEventService.revoke() → redirect
   ├── [Slice 4] POST /ui/.../preview → LocalConfirmationWorkspaceService.calculate_preview() → preview.html
   ├── [Slice 4] GET  /ui/.../preview → LocalConfirmationWorkspaceService.get_preview_view() → preview.html
   ├── [planned: Slice 3] GET  /ui/.../history → ReferenceEventService.get_history() → history.html
  │
  └── (JSON API unchanged)
      GET /api/v1/cases            → same services, JSON output
```

### Application-Layer Decision

**Variante A: Dedicated UI Workspace Service**

A new application service `LocalConfirmationWorkspaceService` will be introduced during implementation. It:

- Orchestrates existing `ReferenceEventService`, `CalculationService`, `CaseService`, and any other required application services
- Produces UI-specific read models (view models) without exposing domain entities directly to templates
- Performs server-side revalidation of case, document, candidate, and confirmation context before any operation
- Does NOT know about HTML, templates, HTTP requests, or response headers
- Does NOT access infrastructure repositories directly

This keeps the UI clean and testable, and the Application Layer remains the sole authority for business logic coordination.

**Invalidated alternative:** Direct repository access from UI routes (violates INV-UI-07).

## Variants Evaluated

### Variant A — Server-Rendered HTML (Jinja2) — **SELECTED**

| Criterion | Assessment |
|-----------|-----------|
| Local install | pip only, no system deps |
| CSP compatibility | `default-src 'self'` trivially enforceable |
| XSS protection | Jinja2 autoescaping structural |
| Testability | same pytest + httpx infrastructure |
| Accessibility | native HTML forms, no JS required for core |
| Node.js | NOT required |
| New dependencies | 1 (`jinja2`) |
| Security surface | Lowest |

### Variant B — Static HTML + Vanilla JS

| Criterion | Assessment |
|-----------|-----------|
| CSP compatibility | `'unsafe-inline'` or fragile hashes needed |
| XSS protection | Manual — developer discipline |
| Testability | Separate JS test infra needed |
| Node.js | NOT required |
| New dependencies | 0 |
| Security surface | Higher (manual XSS protection) |

**Rejected:** CSP weakness and higher XSS risk.

### Variant C — Node.js SPA

- Violates "No Node.js" constraint
- 50–500 new npm packages
- Over-engineering for linear confirmation workflow

**Rejected (ARCH_FAIL).**

## Consequences

### Positive
- User completes full M6-A workflow in browser without CLI
- JSON API preserved for programmatic access
- CSP enforcement is trivial — strictest possible policy
- XSS protection via Jinja2 autoescaping (structural)
- Accessibility benefits from semantic HTML and native browser navigation
- Zero changes to domain, application, or infrastructure layers (except optional new workspace service)
- Zero changes to existing API routes or schemas

### Negative
- One new pip dependency (Jinja2)
- Full-page reloads between steps — acceptable at localhost latency
- Templates add new artifact type to maintain

## Security Requirements (Non-Negotiable)

1. CSRF token on every state-changing form (hidden field, constant-time comparison, rotation)
2. Origin header validation on every POST
3. CSP as HTTP response header only (no meta tags)
4. Host header validation derived from Settings configuration
5. Idempotency keys for all state-changing operations
6. Double-submit protection (server-side atomicity, not just client-side button disable)
7. All security headers per `contracts/security-headers.md`
8. No sensitive data in URLs, query strings, or logs
9. Privacy-safe error handling (no stack traces, no internal IDs in browser)

## UI Invariants

See `spec.md` for complete invariant list. Key structural invariants:

| ID | Invariant |
|----|-----------|
| INV-UI-01 | Local-only: all resources, scripts, styles, fonts are local |
| INV-UI-02 | Human Review: no confirmation, calculation, or action without explicit user action |
| INV-UI-03 | No Legal Decision: the UI does not assess legal validity |
| INV-UI-04 | Revalidation: every state-changing action revalidates server-side |
| INV-UI-05 | CSRF: every POST requires valid CSRF token and Origin proof |
| INV-UI-06 | Idempotency: repeated/parallel submits do not create duplicate state transitions |
| INV-UI-07 | No Direct Infrastructure Access: UI routes use only Application contracts |
| INV-UI-08 | No Invented State: all displayed states come from Application or Domain data |
| INV-UI-09 | Privacy: no sensitive content in logs, URLs, or technical error pages |
| INV-UI-10 | Neutral Language: system labels distinguish detected text from legal assessment |
| INV-UI-11 | Accessible Core Flow: full core workflow operable via keyboard and screen reader |
| INV-UI-12 | Progressive Enhancement: all core actions function without JavaScript |
| INV-UI-13 | Security Headers: every HTML response carries the defined security header set |
| INV-UI-14 | No Remote Assets: no CDN, analytics, font, script, or stylesheet dependency |
| INV-UI-15 | Confirmation Gate: calculation preview only with a currently valid confirmation |

## Explicit Boundary to M6-B

The following MUST NOT appear in M6-UI:
- Rule profile selection (BGB, ZPO, VwZG, VwVfG)
- Weekend/holiday adjustment controls
- Delivery fiction selection
- Bundesland selection for Feiertagsgesetze
- Month/year duration arithmetic UI
- Any claim of binding legal deadline computation

## References

- ADR-001: Lokaler modularer Monolith mit FastAPI + SQLite
- ADR-002: Confirmed Reference Events and Calendar Arithmetic (Variant B)
- M6-A Domain: `src/private_legal_navigator/domain/reference_event.py`
- M6-A Application Port: `src/private_legal_navigator/application/calendar_arithmetic.py`
- M6-A Application Service: `src/private_legal_navigator/application/reference_event_service.py`
- M6-A Application Repository Port: `src/private_legal_navigator/application/reference_event_repository.py`
- M6-A Infrastructure: `src/private_legal_navigator/infrastructure/deterministic_calendar_arithmetic.py`
- M6-A API: `src/private_legal_navigator/api/reference_event_routes.py`
- App Factory: `src/private_legal_navigator/app.py`

---

*ADR-003 authored: 2026-07-17. Hardened: 2026-07-19. Next review: before M6-UI implementation begins.*
