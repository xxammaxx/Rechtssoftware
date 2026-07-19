# Plan — M6-UI Local Confirmation Workspace

## Overview

This plan maps the M6-UI specification to an implementation strategy. No implementation occurs in this specification run — this is a specification artifact for the future build.

## Architecture Decision

**Variant A: Server-Rendered HTML (FastAPI + Jinja2)** — see ADR-003 for full rationale.

**Application Layer Decision: Dedicated UI Workspace Service**

During implementation, a new application service `LocalConfirmationWorkspaceService` will be introduced to orchestrate existing M6-A services and produce UI-specific read models. It MUST NOT:
- Duplicate business logic from existing services
- Access infrastructure repositories directly
- Know about HTML, templates, or HTTP

## Affected Layers (implementation phase)

| Layer | Changes | Type |
|-------|---------|------|
| **API** | New `/ui/` routes (`ui_routes.py`), Jinja2 template rendering | New file |
| **Application** | Optional `LocalConfirmationWorkspaceService` orchestrating existing services | New file (optional) |
| **Templates** | ~8 Jinja2 HTML templates in `templates/` directory | New directory |
| **Static** | `static/css/app.css`, `static/js/enhance.js` (progressive enhancement) | New directory |
| **Config** | Template directory, allowed hosts, CSRF secret in `config.py` | Modify `config.py` |
| **Domain** | No changes | — |
| **Infrastructure** | No changes | — |

## No Changes To

| Area | Rationale |
|------|-----------|
| Domain layer (`reference_event.py`, etc.) | All entities and enums unchanged |
| Application ports (`calendar_arithmetic.py`, `reference_event_repository.py`) | Abstract interfaces unchanged |
| Application services (`reference_event_service.py`, `calculation_service.py`) | Existing services unchanged |
| Infrastructure implementations | SQLite repos, file storage, calendar arithmetic unchanged |
| Existing API routes (`/api/v1/*`) | JSON API untouched |
| Existing tests | Must continue to pass |
| `pyproject.toml` | Add only `jinja2>=3.1.0` to dependencies |

## Dependency Graph (implementation phase)

```
Browser (127.0.0.1:{configured_port})
  │
  ▼ GET /ui/cases, POST /ui/.../confirm
FastAPI /ui/ routes (NEW)
  │
  ▼ LocalConfirmationWorkspaceService (NEW, Application Layer)
  │   └─ Orchestrates: ReferenceEventService, CalculationService,
  │                    CaseService, DocumentService
  │
  ▼ Application Services (EXISTING)
  │
  ▼ Domain entities (EXISTING)
  │
  ▼ SQLite repos (EXISTING, via repository ports)
```

## Implementation Order (future build)

### Phase 1 — Foundation
1. **Add Jinja2 dependency** — `pyproject.toml`
2. **Configure templates** — `Jinja2Templates` in `app.py`
3. **Security middleware** — CSRF token generation, CSP headers, Host validation, Origin checking
4. **Base template** — `templates/base.html` (layout, navigation)

### Phase 2 — Read-only Workspace
5. **Case navigation routes** — Case list, case detail
6. **Document routes** — Document detail, text preview
7. **Workspace route** — Candidate display, reference event display
8. **Static assets** — CSS styling

### Phase 3 — Interactive Confirmation
9. **Confirmation routes** — POST handlers for confirm, reject, manual entry
10. **Preview route** — Calculation preview with revalidation
11. **History route** — Confirmation history display
12. **Revoke route** — Revocation with confirmation dialog

### Phase 4 — Hardening
13. **CSRF integration** — Token generation, validation, rotation
14. **Idempotency integration** — Idempotency keys for all state-changing POST
15. **Error handling** — All error states, generic error page
16. **Accessibility pass** — Labels, landmarks, focus management, live regions

### Phase 5 — Testing
17. **Unit tests** — View model mapping, token logic, terminology
18. **Integration tests** — All routes, headers, CSRF, idempotency
19. **Template tests** — Autoescaping, semantic structure, labels
20. **Browser E2E** — Playwright workflow tests
21. **Accessibility automation** — axe-core integration
22. **Manual NVDA test** — Windows screen reader verification

## Planned Files (future build)

```
src/private_legal_navigator/
├── api/
│   └── ui_routes.py              (~400 lines, 12 route handlers)
├── application/
│   └── local_confirmation_workspace_service.py  (~150 lines, optional)
├── templates/
│   ├── base.html                 (~60 lines)
│   ├── case_list.html            (~50 lines)
│   ├── case_detail.html          (~70 lines)
│   ├── workspace.html            (~200 lines)
│   ├── preview_result.html       (~100 lines)
│   ├── confirmation_history.html (~70 lines)
│   └── error.html                (~30 lines)
├── static/
│   ├── css/
│   │   └── app.css               (~150 lines)
│   └── js/
│       └── enhance.js            (~100 lines, optional progressive enhancement)
```

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| XSS from PDF text rendering | Medium | HIGH | Jinja2 autoescaping structural protection; CSP defense-in-depth |
| User misinterprets preview as binding deadline | Medium | HIGH | Mandatory warnings, neutral terminology, visible disclaimers |
| CSRF on localhost (DNS rebinding) | Low | HIGH | CSRF tokens + Origin validation + Host header validation |
| Double-submit creates duplicate state | Medium | HIGH | Server-side idempotency keys; client-side button disable is UX only |
| CSP too permissive or missing | Certain (before impl) | HIGH | CSP middleware required before release |
| Confirmation gate bypass via manipulated form data | Low | HIGH | Server-side revalidation (INV-UI-04); domain invariants as last line |
| Browser caching of sensitive pages | High | MEDIUM | Cache-Control: no-store on case/document/confirmation pages |
| Accessibility failure | Medium | MEDIUM | WCAG 2.1 AA checklist; keyboard test; NVDA manual audit |
| Host header attack | Low | HIGH | Configurable host validation from Settings |
| Test tool reproducibility | Medium | MEDIUM | Explicit dev dependencies; vendored axe-core; offline-first test design |

## Dependencies Out of Scope

- No `python-dateutil` (no month arithmetic)
- No `holidays` library (no Feiertagsregeln)
- No `workalendar` (no business day support)
- No npm/pip frontend build tools
- No authentication libraries (single-user only)
- No session middleware (token-based CSRF context)

## Test Tool Strategy

| Tool | Type | Dependency Class | Details |
|------|------|-----------------|---------|
| pytest + httpx | Python Unit/Integration | Existing dev dependency | All route, view model, and header tests |
| Jinja2 | Template rendering | Product dependency | `jinja2>=3.1.0` in pyproject.toml |
| Playwright | Browser E2E | Python dev dependency | `playwright` + `pytest-playwright` in dev extras |
| Playwright Browsers | Browser runtime | Dev/test prerequisite | `playwright install chromium` (one-time, offline after install) |
| axe-core | Accessibility automation | Vendored JS file | Locally vendored, version-pinned `axe.min.js` — no CDN |
| NVDA | Manual screen reader | Manual Windows gate | Not automated; checklist-based evidence documentation |

### Offline Reproducibility
After initial installation (`pip install -e ".[dev]"` + `playwright install chromium`), all test runs MUST work without external network access. axe-core is vendored locally. No CDN usage.
