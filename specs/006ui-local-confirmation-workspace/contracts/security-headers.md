# Security Headers Contract — M6-UI

## Overview

All M6-UI HTML responses must include security headers. This contract defines the mandatory header configuration.

## Mandatory Headers

### Content-Security-Policy

```
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; font-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'
```

**Implementation:** FastAPI middleware applied globally to all `/ui/*` routes.

**Verification:**
- No `'unsafe-inline'` in any directive
- No `'unsafe-eval'` in any directive
- All resources served from same origin
- No external URLs in `src` or `href` attributes

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

### Permissions-Policy (optional)

```
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

Blocks browser feature access. Applied globally.

## Host Validation

All requests must include `Host` header matching one of:
- `127.0.0.1:8000`
- `localhost:8000`

Mismatched Host returns HTTP 400 with generic error. Implemented as middleware.

## Implementation (app.py middleware stack)

```python
# Order matters — Host validation first, then security headers
app.add_middleware(HostValidationMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
```

## Testing

- Test that all `/ui/*` responses include CSP header
- Test that non-matching Host returns 400
- Test that case pages include `Cache-Control: no-store`
- Test that CSP does not contain `'unsafe-inline'`
- Test that zero external URLs appear in HTML source
