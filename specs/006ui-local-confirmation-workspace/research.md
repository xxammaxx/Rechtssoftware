# Research — M6-UI Architecture and Security Foundation

## Research Summary

**Date:** 2026-07-19 (hardened)
**Sources:** FastAPI official docs, Starlette docs, Jinja2 docs, OWASP CSRF Guidance, MDN CSP Reference, WCAG 2.1, project codebase

## Key Findings

### 1. Current Stack Capability

| Component | Version | Status |
|-----------|---------|--------|
| FastAPI | 0.139.0 | Installed |
| Starlette | 1.3.1 | Installed (FastAPI dependency) |
| Uvicorn | 0.51.0 | Installed |
| Jinja2 | — | **NOT installed** (to be added) |
| python-multipart | 0.0.32 | Installed (needed for forms) |
| httpx | 0.28.1 | Installed (dev, used for testing) |

### 2. Required Changes for UI

**One new product dependency:** `jinja2>=3.1.0` in `pyproject.toml`

Jinja2 is an optional FastAPI dependency. The project uses `fastapi>=0.115.0` without the `[standard]` extra, so Jinja2 must be declared explicitly. Package size: ~300KB. Maintained by Pallets (same org as Flask, Werkzeug, Click). Zero breaking changes in the 3.x line since 2019.

**Dev dependencies (for testing only, not product):**
- `playwright` — browser E2E testing
- `pytest-playwright` — pytest integration

### 3. Architecture Decision: Variant A — Server-Rendered HTML

**Selected:** FastAPI + Jinja2Templates + StaticFiles + Progressive Enhancement

**Rationale:**
- **Zero new system dependencies** — Python-only, no Node.js
- **Strictest CSP possible** — `default-src 'self'` without exceptions
- **Structural XSS protection** — Jinja2 autoescaping for all `.html` templates
- **Full testability** — same `httpx` + `ASGITransport` test infrastructure
- **Native accessibility** — standard HTML forms are keyboard-accessible by default
- **Progressive enhancement** — core workflow works without JavaScript
- **One new pip package** — Jinja2 (battle-tested, 12M+ downloads/day)

**Rejected variants:**
- **Variant B (Static HTML + Vanilla JS):** CSP weakened (inline scripts need `'unsafe-inline'`), manual XSS protection
- **Variant C (Node.js SPA):** Violates "No Node.js" constraint, over-engineering

### 4. XSS Protection Strategy

Jinja2 autoescaping is enabled by default for `.html` files. The `{{ variable }}` syntax escapes HTML entities automatically:
- `<` → `&lt;`
- `>` → `&gt;`
- `&` → `&amp;`
- `"` → `&quot;`

**The `| safe` filter must NEVER be used for document text, evidence text, or user input.**

### 5. CSRF Protection — Browser Model Analysis

**Source:** OWASP CSRF Prevention Cheat Sheet, MDN Web Security, Same-Origin Policy specification
**Date:** 2026-07-19

Even on localhost, state-changing POST requests require CSRF protection when accessed via browser:

- **Same-Origin Policy** prevents cross-origin reads but does NOT prevent cross-origin form submissions. A malicious page on a different origin CAN submit a form to `http://127.0.0.1:8000/ui/.../confirm`.
- **SameSite cookies** (Lax/Strict) mitigate CSRF for cookie-based sessions, but M6-UI intentionally avoids server-side sessions. Without session cookies, SameSite provides no protection.
- **Origin header** provides first-line defense: browsers send `Origin: null` for some cross-origin requests but send the actual origin for same-origin requests.

**Selected CSRF Model: Signed Token Pattern**

```
1. Server generates cryptographically random CSRF token
2. Token is embedded in a signed context (HMAC) bound to the request session
3. Token is placed in hidden form field
4. On POST, server verifies: token presence, token validity, token context binding, Origin header
5. Constant-time comparison prevents timing attacks
6. Token rotation on use or on expiry
```

**Token context binding:** Token is bound to a short-lived, browser-specific context (e.g., HMAC-signed cookie or signed request parameter). This prevents cross-context token reuse without requiring server-side session storage.

### 6. CSP Baseline (HTTP Header Only)

```
Content-Security-Policy:
  default-src 'none';
  base-uri 'none';
  form-action 'self';
  frame-ancestors 'none';
  img-src 'self';
  style-src 'self';
  script-src 'self';
  connect-src 'self';
  font-src 'self';
  object-src 'none'
```

**Source:** MDN Content-Security-Policy reference, CSP Level 2/3 specification
**Date:** 2026-07-19

**Directive rationale:**
- `default-src 'none'` — deny-by-default posture
- `base-uri 'none'` — prevent base tag injection
- `form-action 'self'` — forms may only submit to same origin
- `frame-ancestors 'none'` — prevent clickjacking
- `img-src 'self'` — only local images
- `style-src 'self'` — only local stylesheets
- `script-src 'self'` — only local scripts
- `connect-src 'self'` — only same-origin XHR/fetch
- `font-src 'self'` — only local fonts
- `object-src 'none'` — block plugins

**Prohibited:** `'unsafe-inline'`, `'unsafe-eval'`, `*`, `data:`, `https:` — no exceptions without documented necessity and security review.

**Delivery:** CSP is set exclusively via HTTP response header. NO `<meta http-equiv="Content-Security-Policy">` in HTML templates.

### 7. Additional Security Headers

All HTML responses must include:

| Header | Value | Rationale |
|--------|-------|-----------|
| `X-Content-Type-Options` | `nosniff` | Prevent MIME type sniffing |
| `Referrer-Policy` | `no-referrer` | Prevent UUID leakage via Referer |
| `Cache-Control` | `no-store` | On case/document/confirmation pages |
| `Cross-Origin-Opener-Policy` | `same-origin` | Process isolation |
| `Cross-Origin-Resource-Policy` | `same-origin` | Block cross-origin resource access |
| `X-Frame-Options` | `DENY` | Legacy clickjacking protection |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=()` | Block browser features |

### 8. Form Handling

- `python-multipart` already installed — supports `application/x-www-form-urlencoded` form submissions
- Pattern: `RedirectResponse(url=..., status_code=303)` after POST (PRG pattern)
- Server-side validation with error re-rendering in template
- CSRF token as hidden form field
- Idempotency key as hidden form field

### 9. Integration Pattern

New `/ui/` routes call existing `request.app.state.*` services — same Application Services as the JSON API. No logic duplication. The confirmation gate (ADR-002) is enforced in the service layer, not the UI.

**Note on `app.state`:** The current application uses `app.state.*` for dependency injection. The UI spec references this existing pattern. During implementation, existing DI conventions will be followed. UI routes will NOT introduce a parallel DI mechanism.

### 10. Host Validation and DNS Rebinding

**Source:** OWASP DNS Rebinding Prevention, Starlette middleware documentation
**Date:** 2026-07-19

**Threat:** A DNS rebinding attack can cause a browser to connect to localhost while believing it is connecting to an attacker-controlled domain, bypassing same-origin restrictions.

**Mitigation:** Host header validation middleware that:
1. Extracts the `Host` header from incoming requests
2. Compares against an allowlist derived from `Settings`
3. Includes port number in the comparison (exact match)
4. Supports `127.0.0.1`, `localhost`, and `[::1]` (configurable)
5. Returns 400 for mismatched hosts
6. Does NOT trust `X-Forwarded-Host` or similar proxy headers

**Distinction:** Host validation is separate from CSRF protection. Host validation prevents request routing attacks. CSRF protection prevents cross-origin form submission attacks. Both are required.

### 11. Idempotency Model

**Source:** IETF HTTP Idempotency-Key draft, Stripe API idempotency design
**Date:** 2026-07-19

For every state-changing POST operation:
1. Client generates a unique idempotency key per action attempt
2. Key is submitted as hidden form field
3. Server checks if key has been previously processed
4. If processed: return the original result (idempotent replay)
5. If not processed: execute the action, store the key+result
6. Key is bound to: action type, resource IDs, expected prior state
7. Short lifetime (e.g., 24 hours) prevents unbounded storage
8. Atomic: check-and-set in a single database transaction

Domain invariants (e.g., "cannot confirm an already confirmed event without superseding") remain the final defense.

## Sources

| # | Source | Topic |
|---|--------|-------|
| 1 | fastapi.tiangolo.com/advanced/templates/ | Jinja2Templates in FastAPI |
| 2 | fastapi.tiangolo.com/tutorial/static-files/ | StaticFiles mounting |
| 3 | fastapi.tiangolo.com/tutorial/middleware/ | Middleware (CSP headers) |
| 4 | fastapi.tiangolo.com/tutorial/request-forms/ | Form data handling |
| 5 | jinja.palletsprojects.com/en/stable/api/ | Jinja2 autoescaping |
| 6 | starlette.io/staticfiles/ | Starlette StaticFiles |
| 7 | cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html | CSRF prevention |
| 8 | developer.mozilla.org/en-US/docs/Web/HTTP/CSP | Content Security Policy |
| 9 | developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Origin | Origin header |
| 10 | developer.mozilla.org/en-US/docs/Web/Security/Same-origin_policy | Same-origin policy |
| 11 | developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie/SameSite | SameSite cookies |
| 12 | C:\Rechtssoftware\pyproject.toml | Current dependencies |
| 13 | C:\Rechtssoftware\src\private_legal_navigator\app.py | App factory and DI pattern |
| 14 | C:\Rechtssoftware\src\private_legal_navigator\config.py | Settings configuration |
| 15 | C:\Rechtssoftware\src\private_legal_navigator\domain\reference_event.py | Domain types |
| 16 | C:\Rechtssoftware\src\private_legal_navigator\application\reference_event_service.py | Application service |
| 17 | C:\Rechtssoftware\src\private_legal_navigator\application\calculation_service.py | Calculation service |
| 18 | C:\Rechtssoftware\src\private_legal_navigator\api\reference_event_routes.py | API routes |
