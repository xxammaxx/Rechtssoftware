# Plan — M6-UI Local Confirmation Workspace

## Overview

This plan maps the M6-UI specification to an implementation strategy. No implementation occurs in this run — this is a specification artifact for the future build.

## Architecture Decision

**Variant A: Server-Rendered HTML (FastAPI + Jinja2)** — see ADR-003 for full rationale.

## Affected Layers (implementation phase)

| Layer | Changes | Type |
|-------|---------|------|
| **API** | New `/ui/` routes (`ui_routes.py`), Jinja2 template rendering | New file |
| **Templates** | ~8 Jinja2 HTML templates in `templates/` directory | New directory |
| **Static** | `static/css/app.css`, `static/js/enhance.js` (optional) | New directory |
| **Config** | Template directory configuration in `app.py` | Modify `app.py` |
| **Domain** | No changes | — |
| **Application** | No changes | — |
| **Infrastructure** | No changes | — |

## No Changes To

| Area | Rationale |
|------|-----------|
| M6-A API endpoints | JSON API untouched — UI calls same services |
| Domain layer | Calendar, Case, Document entities unchanged |
| Application services | EventService, CaseService, etc. unchanged |
| Infrastructure | SQLite repos, file storage, calendar arithmetic unchanged |
| Existing tests | 379 tests must continue to pass |
| pyproject.toml | Add only `jinja2>=3.1.0` to dependencies |

## Dependency Graph (implementation phase)

```
Browser (127.0.0.1:8000)
  │
  ▼ GET /ui/cases, POST /ui/.../confirm
FastAPI /ui/ routes (NEW)
  │
  ▼ Uses app.state.* services
Application Services (EXISTING)
  │
  ▼ Domain entities (EXISTING)
  │
  ▼ SQLite repos (EXISTING)
```

## Implementation Order (future build)

1. **Add Jinja2 dependency** — `pyproject.toml`
2. **Configure templates** — `Jinja2Templates` in `app.py`
3. **Create base template** — `templates/base.html` (layout, CSP meta, nav)
4. **Add security middleware** — CSP, Cache-Control, Referrer-Policy headers
5. **Build UI routes** — Case navigation, document selection
6. **Build workflow routes** — Deadline candidates, reference events, confirmation
7. **Build result routes** — Calculation preview, history
8. **Add static assets** — CSS for styling, optional JS for enhancement
9. **Write tests** — Unit, integration, and browser E2E tests
10. **Accessibility audit** — Keyboard navigation, screen reader, contrast

## Planned Files (future build)

```
src/private_legal_navigator/
├── api/
│   └── ui_routes.py              (~350 lines, 8 route handlers)
├── templates/
│   ├── base.html                 (~60 lines)
│   ├── case_list.html            (~50 lines)
│   ├── case_detail.html          (~70 lines)
│   ├── deadline_workspace.html   (~180 lines)
│   ├── calculation_result.html   (~100 lines)
│   ├── confirmation_history.html (~70 lines)
│   └── error.html                (~30 lines)
├── static/
│   ├── css/
│   │   └── app.css               (~150 lines)
│   └── js/
│       └── enhance.js            (~100 lines, optional)
```

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| XSS from PDF text rendering | Medium | HIGH | Jinja2 autoescaping structural protection; CSP defense-in-depth |
| User confuses preview with binding deadline | Medium | HIGH | Mandatory warnings, terminology discipline, visible disclaimers |
| DNS rebinding attack | Low | HIGH | Host header validation; 127.0.0.1 binding; no external resources |
| Missing CSP | Certain (before impl) | HIGH | CSP middleware required before release |
| Confirmation gate bypass in UI | Low | HIGH | Service-layer enforcement (ADR-002); UI button disable is defense-in-depth |
| Browser caching of sensitive pages | High | MEDIUM | Cache-Control: no-store on case pages |
| Accessibility failure | Medium | MEDIUM | WCAG 2.1 AA checklist; keyboard test; screen reader audit |
| Inline script CSP violation | Low | MEDIUM | No inline scripts by design; CSP blocks by default |

## Dependencies Out of Scope

- No `python-dateutil` (no month arithmetic)
- No `holidays` library (no Feiertagsregeln)
- No `workalendar` (no business day support)
- No npm/pip frontend build tools
- No authentication libraries (single-user only)
