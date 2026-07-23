# Security Checklist — M6-UI

## Non-Negotiable Security Requirements

- [ ] **R1:** Never use innerHTML, dangerouslySetInnerHTML, v-html, insertAdjacentHTML, document.write, or eval
- [ ] **R2:** Serve UI from same FastAPI process (same origin) — no separate dev server
- [ ] **R3:** Implement strict CSP header (`default-src 'none'` etc.) — HTTP header only, no meta tag
- [ ] **R4:** Validate Host header on every request (configurable allowlist from Settings)
- [ ] **R5:** Implement all security headers (CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Cross-Origin-Opener-Policy, Cross-Origin-Resource-Policy, Permissions-Policy)
- [ ] **R6:** Zero external resources — bundle all CSS, JS, fonts, icons locally
- [ ] **R7:** Set Cache-Control: no-store on case/document/confirmation pages
- [ ] **R8:** Escape all user-provided data in templates (Jinja2 autoescaping)
- [ ] **R9:** Static file path traversal protection (absolute paths, check_dir, no directory listing)
- [ ] **R10:** Server-side idempotency (not just client-side button disable)
- [ ] **R11:** CSRF token on every state-changing POST (hidden field, constant-time comparison, rotation)
- [ ] **R12:** Origin header validation on every POST; Referer as fallback
- [ ] **R13:** No secrets, tokens, or internal IDs in URLs, query strings, or error responses
- [ ] **R14:** Server-side revalidation of case/document/candidate/confirmation context before every state-changing operation
- [ ] **R15:** No sensitive data in logs (privacy-safe logging)

## Threat Coverage

| Threat | Mitigation | Verified |
|--------|-----------|----------|
| THREAT-01: XSS via PDF text | Jinja2 autoescaping + CSP header | [ ] |
| THREAT-02: HTML injection in user fields | Jinja2 autoescaping | [ ] |
| THREAT-03: Unsafe innerHTML | textContent only; linter rule | [ ] |
| THREAT-04: CSRF (cross-origin form submit) | CSRF token + Origin validation + constant-time comparison | [ ] |
| THREAT-05: CSP bypass via meta tag | CSP header only; no `<meta>` CSP | [ ] |
| THREAT-06: DNS rebinding | Configurable Host header validation | [ ] |
| THREAT-07: Host header manipulation | Exact match against Settings-derived allowlist | [ ] |
| THREAT-08: UUIDs in URLs | Referrer-Policy: no-referrer | [ ] |
| THREAT-09: Form tampering (hidden field manipulation) | Server-side revalidation from canonical sources | [ ] |
| THREAT-10: Double submit (duplicate state) | Server-side idempotency keys | [ ] |
| THREAT-11: Token replay | CSRF token rotation; idempotency key expiry | [ ] |
| THREAT-12: Missing CSP | CSP middleware; test verification | [ ] |
| THREAT-13: Static file path traversal | Absolute paths; tests | [ ] |
| THREAT-14: Cross-resource ID manipulation | Server-side membership check (document belongs to case, etc.) | [ ] |
| THREAT-15: Status conflict bypass | Domain invariants as final defense | [ ] |
| THREAT-16: Parallel request race condition | Atomic check-and-set for idempotency | [ ] |
| THREAT-17: Information disclosure in errors | Generic error messages; no stack traces | [ ] |
| THREAT-18: Sensitive data in logs | Privacy-safe logging (no PII, no document content) | [ ] |
| THREAT-19: External resources | CSP + bundle verification | [ ] |
| THREAT-20: Browser caching | Cache-Control: no-store | [ ] |

## Security Test Coverage

- [ ] CSP header present and correct on all `/ui/*` responses
- [ ] No CSP meta tag in HTML source
- [ ] No inline scripts in HTML
- [ ] No external resources in HTML source
- [ ] Host header validation: correct host accepted
- [ ] Host header validation: wrong host → 400
- [ ] Host header validation: wrong port → 400
- [ ] CSRF: valid token + correct Origin → success
- [ ] CSRF: missing token → 403
- [ ] CSRF: invalid token → 403
- [ ] CSRF: token from different context → 403
- [ ] CSRF: cross-origin POST → 403
- [ ] CSRF: missing Origin + invalid Referer → 403
- [ ] CSRF: token replay → 403 or 409
- [ ] Idempotency: duplicate key → original result (no duplicate action)
- [ ] Idempotency: parallel submit → safe
- [ ] Idempotency: key expiry → works as defined
- [ ] Cache-Control headers on case pages
- [ ] Referrer-Policy, X-Content-Type-Options, X-Frame-Options on all responses
- [ ] Cross-Origin-Opener-Policy and Cross-Origin-Resource-Policy on all responses
- [ ] No sensitive IDs in error responses
- [ ] XSS test: PDF with `<script>alert(1)</script>` renders as text
- [ ] Static file path traversal blocked
- [ ] Server-side revalidation: cross-case document ID → 404
- [ ] Server-side revalidation: deleted document mid-workflow → stale state error
- [ ] No PII in log output during test runs
