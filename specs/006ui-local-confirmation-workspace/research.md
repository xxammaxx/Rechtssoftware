# Research — M6-UI Architecture and Technology Foundation

## Research Summary

**Date:** 2026-07-17
**Sources:** FastAPI official docs, Starlette docs, Jinja2 docs, project codebase

## Key Findings

### 1. Current Stack Capability

| Component | Version | Status |
|-----------|---------|--------|
| FastAPI | 0.139.0 | Installed |
| Starlette | 1.3.1 | Installed (FastAPI dependency) |
| Uvicorn | 0.51.0 | Installed |
| Jinja2 | — | **NOT installed** |
| python-multipart | 0.0.32 | Installed (needed for forms) |
| httpx | 0.28.1 | Installed (dev, used for testing) |

### 2. Required Changes for UI

**One new dependency:** `jinja2>=3.1.0` in `pyproject.toml`

Jinja2 is an optional FastAPI dependency. The project uses `fastapi>=0.115.0` without the `[standard]` extra, so Jinja2 must be declared explicitly. Package size: ~300KB. Maintained by Pallets (same org as Flask, Werkzeug, Click). Zero breaking changes in the 3.x line since 2019.

### 3. Architecture Decision: Variant A — Server-Rendered HTML

**Selected:** FastAPI + Jinja2Templates + StaticFiles + Progressive Enhancement

**Rationale (condensed):**
- **Zero new system dependencies** — Python-only, no Node.js
- **Strictest CSP possible** — `default-src 'self'` without exceptions
- **Structural XSS protection** — Jinja2 autoescaping for all `.html` templates
- **Full testability** — same `httpx` + `ASGITransport` test infrastructure
- **Native accessibility** — standard HTML forms are keyboard-accessible by default
- **Progressive enhancement** — core workflow works without JavaScript
- **One new pip package** — Jinja2 (battle-tested, 12M+ downloads/day)

**Rejected variants:**
- **Variant B (Static HTML + Vanilla JS):** CSP weakened (inline scripts need `'unsafe-inline'`), manual XSS protection, separate JS test infrastructure needed
- **Variant C (Node.js SPA):** Violates "No Node.js" constraint, 50-500 new npm dependencies, separate build step, over-engineering for linear workflow

### 4. XSS Protection Strategy

Jinja2 autoescaping is enabled by default for `.html` files. The `{{ variable }}` syntax escapes HTML entities automatically:
- `<` → `&lt;`
- `>` → `&gt;`
- `&` → `&amp;`
- `"` → `&quot;`

PDF text containing `<script>alert(1)</script>` will render as literal text, not execute. **The `| safe` filter must NEVER be used for document text, evidence text, or user input.**

### 5. CSP Baseline

```
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; font-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'
```

Applied via FastAPI middleware. No inline scripts needed — all CSS in linked `.css` files, all JS in linked `.js` files.

### 6. Form Handling

- `python-multipart` already installed — supports `application/x-www-form-urlencoded` form submissions
- Pattern: `RedirectResponse(url=..., status_code=303)` after POST (PRG pattern prevents double-submit)
- Server-side validation with error re-rendering in template

### 7. Integration Pattern

New `/ui/` routes call existing `request.app.state.*` services — same Application Services as the JSON API. No logic duplication. The confirmation gate (ADR-002) is enforced in the service layer, not the UI.

## Sources

| # | Source | Topic |
|---|--------|-------|
| 1 | fastapi.tiangolo.com/advanced/templates/ | Jinja2Templates in FastAPI |
| 2 | fastapi.tiangolo.com/tutorial/static-files/ | StaticFiles mounting |
| 3 | fastapi.tiangolo.com/tutorial/middleware/ | Middleware (CSP headers) |
| 4 | fastapi.tiangolo.com/tutorial/request-forms/ | Form data handling |
| 5 | jinja.palletsprojects.com/en/stable/api/ | Jinja2 autoescaping |
| 6 | starlette.io/staticfiles/ | Starlette StaticFiles |
| 7 | C:\Rechtssoftware\pyproject.toml | Current dependencies |
| 8 | C:\Rechtssoftware\src\private_legal_navigator\app.py | App factory pattern |
