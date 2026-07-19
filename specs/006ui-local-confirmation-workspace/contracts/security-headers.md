# Security Headers Contract — M6-UI

## Overview

All M6-UI HTML responses must include security headers. This contract defines the mandatory header configuration.

## Mandatory Headers

### Content-Security-Policy

```
Content-Security-Policy: default-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'; img-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; font-src 'self'; object-src 'none'
```

**Delivery:** HTTP response header ONLY. No `<meta http-equiv="Content-Security-Policy">` elements in HTML.

**Directive rationale:**

| Directive | Value | Rationale |
|-----------|-------|-----------|
| `default-src` | `'none'` | Deny-by-default: only explicitly allowed sources |
| `base-uri` | `'none'` | Prevent `<base>` tag injection |
| `form-action` | `'self'` | Forms only submit to same origin |
| `frame-ancestors` | `'none'` | Prevent clickjacking (complemented by `X-Frame-Options: DENY`) |
| `img-src` | `'self'` | Only local images |
| `style-src` | `'self'` | Only local stylesheets (no inline styles via `<style>`) |
| `script-src` | `'self'` | Only local scripts (no inline scripts, no `eval`) |
| `connect-src` | `'self'` | Only same-origin XHR/fetch requests |
| `font-src` | `'self'` | Only locally served font files |
| `object-src` | `'none'` | Block all plugins (Flash, Java, etc.) |

**Prohibited values (no exceptions without documented necessity and security review):**
- `'unsafe-inline'`
- `'unsafe-eval'`
- `*` (wildcard)
- `data:`
- `https:` (allows any HTTPS origin)
- `http:` (allows any HTTP origin)

**If `data:` URIs are needed for inline decorative SVG icons:** This must be justified in a separate ADR amendment and explicitly approved. The default specification does NOT include `data:`.

### X-Content-Type-Options

```
X-Content-Type-Options: nosniff
```

Prevents MIME type sniffing. Applied globally.

### X-Frame-Options

```
X-Frame-Options: DENY
```

Prevents clickjacking. Redundant with CSP `frame-ancestors 'none'` but defense-in-depth for older browsers.

### Referrer-Policy

```
Referrer-Policy: no-referrer
```

Prevents UUID leakage via Referer header. Applied globally.

### Cache-Control

```
Cache-Control: no-store, max-age=0
```

Applied to all case-related UI routes (`/ui/cases/*`). Prevents sensitive legal data in browser cache.

### Cross-Origin-Opener-Policy

```
Cross-Origin-Opener-Policy: same-origin
```

Ensures the browsing context is isolated to same-origin documents.

### Cross-Origin-Resource-Policy

```
Cross-Origin-Resource-Policy: same-origin
```

Prevents cross-origin embedding of resources.

### Permissions-Policy

```
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

Blocks browser feature access. Can be tightened during implementation if additional features are identified.

## Host Validation

### Configuration

Allowed hosts are derived from `Settings` configuration, NOT hardcoded. The `Settings` class provides:

```python
# config.py
class Settings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 8000
```

### Allowlist Generation

The allowed host header values are generated at startup:

```python
allowed_hosts: set[str] = {
    f"127.0.0.1:{port}",
    f"localhost:{port}",
    f"[::1]:{port}",
}
```

### Validation Middleware

- Extracts `Host` header from incoming request
- Exact string match against allowlist (port-inclusive)
- Mismatched Host returns HTTP 400 with generic error
- Does NOT trust `X-Forwarded-Host`, `Forwarded`, or similar proxy headers
- No wildcards, no pattern matching beyond exact host:port

### Distinction from CSRF

Host validation prevents request routing attacks (DNS rebinding). CSRF protection prevents cross-origin form submission. **Both are required — neither replaces the other.**

## Double Submit / Idempotency (Server-Side)

### Idempotency Key

Every state-changing POST action requires an idempotency key:

- Client-generated unique key per action attempt
- Submitted as hidden form field `idempotency_key`
- Server checks if key already processed (atomic check-and-set)
- If processed: return original result (idempotent replay, HTTP 200)
- If new: execute action, store key+result atomically
- Key binding: action type + resource IDs + expected prior state
- Short lifetime: keys expire after 24 hours
- Conflict response: HTTP 409 with "Bereits verarbeitet"

### Client-Side Double Submit

JavaScript button-disable-after-click is a UX enhancement only. It does NOT replace server-side idempotency. PRG (Post/Redirect/Get) pattern prevents back-button re-submission but does NOT prevent parallel submissions from multiple tabs.

## Implementation (app.py middleware stack)

```python
# Order matters:
# 1. Host validation (reject invalid hosts before processing)
# 2. Security headers (applied to all responses)
app.add_middleware(HostValidationMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
```

CSRF and idempotency are implemented as route-level dependencies/decorators, not global middleware, since they apply only to POST routes.

## Testing Requirements

- [ ] All `/ui/*` GET responses include full CSP header
- [ ] CSP header does NOT contain `'unsafe-inline'` or `'unsafe-eval'`
- [ ] No CSP meta tag in HTML source
- [ ] Non-matching Host header returns 400
- [ ] `127.0.0.1:{port}` is accepted
- [ ] `localhost:{port}` is accepted
- [ ] `[::1]:{port}` is accepted
- [ ] `evil.com` returns 400
- [ ] Wrong port returns 400
- [ ] Case pages include `Cache-Control: no-store`
- [ ] `X-Content-Type-Options: nosniff` on all responses
- [ ] `Referrer-Policy: no-referrer` on all responses
- [ ] `Cross-Origin-Opener-Policy: same-origin` on all responses
- [ ] `Cross-Origin-Resource-Policy: same-origin` on all responses
- [ ] `X-Frame-Options: DENY` on all responses
- [ ] CSRF token present in all POST form templates
- [ ] CSRF token missing → 403
- [ ] CSRF token invalid → 403
- [ ] Origin mismatch → 403
- [ ] Idempotency key replay → 409
- [ ] Double submit with same idempotency key → 200 (original result, no duplicate action)
