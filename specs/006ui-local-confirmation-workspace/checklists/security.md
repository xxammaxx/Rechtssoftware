# Security Checklist — M6-UI

Based on the Security Agent's threat model (SECURITY_PASS_WITH_NOTES, 20 threats, 10 non-negotiable requirements).

## Non-Negotiable Security Requirements

- [ ] **R1:** Never use innerHTML, dangerouslySetInnerHTML, v-html, insertAdjacentHTML, document.write, or eval
- [ ] **R2:** Serve UI from same FastAPI process (same origin) — no separate dev server
- [ ] **R3:** Implement strict CSP header (`default-src 'self'` etc.)
- [ ] **R4:** Validate Host header on every request (127.0.0.1:8000 / localhost:8000)
- [ ] **R5:** Implement all security headers (CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy)
- [ ] **R6:** Zero external resources — bundle all CSS, JS, fonts, icons locally
- [ ] **R7:** Set Cache-Control: no-store on case/document/confirmation pages
- [ ] **R8:** Escape all user-provided data in templates (Jinja2 autoescaping)
- [ ] **R9:** Static file path traversal protection (absolute paths, check_dir, no directory listing)
- [ ] **R10:** Disable submit buttons after click; implement PRG pattern for forms

## Threat Coverage

| Threat | Mitigation | Verified |
|--------|-----------|----------|
| THREAT-01: XSS via PDF text | Jinja2 autoescaping + CSP | [ ] |
| THREAT-02: HTML injection in user fields | Jinja2 autoescaping | [ ] |
| THREAT-03: Unsafe innerHTML | textContent only, linter rule | [ ] |
| THREAT-04: CSRF | Same-origin + SameSite cookies N/A | [ ] |
| THREAT-05: CORS misconfig | Same-origin serving (no CORS needed) | [ ] |
| THREAT-06: DNS rebinding | Host header validation | [ ] |
| THREAT-07: Host header manipulation | Exact match validation | [ ] |
| THREAT-08: UUIDs in URLs | Referrer-Policy: no-referrer | [ ] |
| THREAT-12: Missing CSP | CSP middleware | [ ] |
| THREAT-13: Static file path traversal | Absolute paths, tests | [ ] |
| THREAT-16: Double submit | PRG pattern + button disable | [ ] |
| THREAT-19: External resources | CSP + bundle verification | [ ] |
| THREAT-20: Browser caching | Cache-Control: no-store | [ ] |

## Security Test Coverage

- [ ] CSP header present and correct
- [ ] No inline scripts in HTML
- [ ] No external resources in HTML source
- [ ] Host header validation (correct + incorrect)
- [ ] Cache-Control headers on case pages
- [ ] Referrer-Policy header
- [ ] X-Content-Type-Options header
- [ ] No sensitive IDs in error responses
- [ ] XSS test: PDF with `<script>alert(1)</script>` renders as text
- [ ] Static file path traversal blocked
- [ ] Double submit: second click does not create duplicate
