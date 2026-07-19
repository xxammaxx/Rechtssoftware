# Testing Checklist — M6-UI

## Test Strategy Overview

| Layer | Type | Framework | Scope |
|-------|------|-----------|-------|
| Unit | View models | pytest | View model mapping, warning display, text truncation |
| Unit | Templates | pytest + httpx | Template rendering, escaping, security metadata |
| Unit | Security | pytest | Token logic, host validation, header generation |
| Integration | UI Routes | pytest + httpx | Full route → service → template pipeline |
| Integration | Security | pytest + httpx | Headers, CSP, Host validation, CSRF, idempotency |
| E2E | Browser | Playwright | Complete user workflows |
| Accessibility | Auto + manual | axe-core (vendored), NVDA | WCAG 2.1 AA criteria |

## Unit Test Cases

### View Models (test_ui_view_models.py)

- [ ] `CaseListView` correctly maps from `CaseService` output
- [ ] `CaseDetailView` includes document list with correct metadata
- [ ] `DeadlineWorkspaceView` maps candidates with correct type labels
- [ ] `ReferenceEventCard` marks current status correctly
- [ ] `CalculationPreviewView` includes all mandatory warnings
- [ ] `HistoryView` sorts entries by timestamp descending
- [ ] Warning codes mapped to correct German messages (neutral terminology)
- [ ] Error codes mapped to correct German messages (neutral terminology)
- [ ] Event types mapped to correct German labels
- [ ] Confirmation methods mapped to correct German labels
- [ ] Source types mapped to correct German labels
- [ ] Evidence text truncated with ellipsis at display limit
- [ ] No "Frist", "Fristende", "Fristberechnung" in system-generated labels
- [ ] Action mapping: UI action → domain source_type → confirmation_method

### Templates (test_ui_templates.py)

- [ ] `case_list.html` renders case titles (verify HTML escaping)
- [ ] `case_list.html` shows "Keine Faelle vorhanden" when empty
- [ ] `case_detail.html` shows "Keine Dokumente" when empty
- [ ] `workspace.html` renders candidate types with neutral labels
- [ ] `workspace.html` shows human_review_required
- [ ] `workspace.html` includes CSRF hidden field in all forms
- [ ] `workspace.html` includes idempotency_key hidden field in all POST forms
- [ ] `preview_result.html` shows "Unverbindliche Rechenvorschau" (NOT "Fristende")
- [ ] `preview_result.html` includes all adjustment rows
- [ ] `preview_result.html` shows human_review_required=true
- [ ] `preview_result.html` shows legal_validity_assessed=false
- [ ] `preview_result.html` shows "Rechtliche Gueltigkeit nicht bewertet"
- [ ] `confirmation_history.html` shows supersession chain
- [ ] `error.html` shows user-friendly message without IDs
- [ ] No `| safe` filter on user-provided data
- [ ] No CSP meta tag in any HTML template
- [ ] Semantic heading hierarchy in all templates
- [ ] `<label>` elements on all form controls

### XSS Prevention

- [ ] PDF text with `<script>alert(1)</script>` rendered as escaped text
- [ ] Filename with `<img src=x onerror=alert(1)>` rendered as escaped text
- [ ] Evidence text with HTML entities rendered as escaped text
- [ ] No `innerHTML` usage in progressive enhancement JS

### Security Unit Tests (test_ui_security.py)

- [ ] CSRF token generation produces unique tokens
- [ ] CSRF token validation: valid → success
- [ ] CSRF token validation: invalid → failure
- [ ] CSRF token validation: constant-time comparison
- [ ] CSRF token: context binding prevents cross-context use
- [ ] Idempotency key: generation
- [ ] Idempotency key: replay detection
- [ ] Idempotency key: expiry logic
- [ ] Host allowlist: generates correct set from Settings
- [ ] Host allowlist: includes port
- [ ] Security header string: no 'unsafe-inline'
- [ ] Security header string: no 'unsafe-eval'
- [ ] Security header string: no wildcard
- [ ] Origin validation: same-origin accepted
- [ ] Origin validation: cross-origin rejected

## Integration Test Cases (test_ui_routes.py)

### Case Navigation

- [ ] `GET /ui/` redirects to `/ui/cases`
- [ ] `GET /ui/cases` returns 200 with case list HTML
- [ ] `GET /ui/cases` with no cases returns 200 with empty state
- [ ] `GET /ui/cases/{id}` returns 200 with case detail
- [ ] `GET /ui/cases/{id}` with unknown ID returns 404 error page

### Document View

- [ ] `GET /ui/cases/{id}/documents/{did}` returns 200
- [ ] Document with text shows text preview
- [ ] Document without text shows "Kein Text extrahierbar"

### Workspace

- [ ] `GET .../workspace` returns 200 with candidate list
- [ ] `GET .../workspace` with no candidates shows appropriate hint
- [ ] Reference events displayed with correct status

### Confirmation

- [ ] `POST .../workspace/confirm` with valid data + CSRF → redirects
- [ ] `POST .../workspace/confirm` without CSRF token → 403
- [ ] `POST .../workspace/confirm` with invalid CSRF token → 403
- [ ] `POST .../workspace/confirm` with wrong Origin → 403
- [ ] `POST .../workspace/confirm` with invalid date → error with re-rendered form
- [ ] `POST .../workspace/reject` → redirects
- [ ] `POST .../workspace/manual` → creates confirmation with user_manual source
- [ ] `POST .../workspace/correct` → supersedes previous, old → SUPERSEDED

### Calculation Preview

- [ ] `GET .../workspace/preview` with confirmed event → preview page
- [ ] `GET .../workspace/preview` without confirmation → error
- [ ] Preview page contains all mandatory warnings
- [ ] Cross-document confirmation ID → rejected
- [ ] Dauer from canonical candidate source (not trusting hidden fields)

### History

- [ ] `GET .../workspace/history` returns history page
- [ ] History shows supersession chain correctly

### Revoke

- [ ] `POST .../workspace/revoke` with valid confirmation_id → redirects
- [ ] `POST .../workspace/revoke` with idempotency replay → 409
- [ ] After revoke: calculation blocked

### Security Headers (all routes)

- [ ] All `/ui/*` responses include CSP header (HTTP header, not meta)
- [ ] CSP: no `'unsafe-inline'`
- [ ] CSP: no `'unsafe-eval'`
- [ ] Case pages include `Cache-Control: no-store`
- [ ] All responses include `X-Content-Type-Options: nosniff`
- [ ] All responses include `Referrer-Policy: no-referrer`
- [ ] All responses include `Cross-Origin-Opener-Policy: same-origin`
- [ ] All responses include `Cross-Origin-Resource-Policy: same-origin`
- [ ] All responses include `X-Frame-Options: DENY`
- [ ] Request with `Host: evil.com:8000` returns 400
- [ ] Request with `Host: 127.0.0.1:9999` (wrong port) returns 400

### Error Handling

- [ ] 404 returns error page with "nicht gefunden"
- [ ] 500 returns error page without stack trace
- [ ] Error page does not contain UUIDs in visible text
- [ ] 403 returns generic error (CSRF validation failure, no details)
- [ ] 409 returns "Bereits verarbeitet" message

### Double Submit

- [ ] Second identical POST with same idempotency_key → 200 (original result)
- [ ] No duplicate database entry created
- [ ] Client-side button disable as UX enhancement (verified separately)

## Browser E2E Test Cases (Playwright)

- [ ] **E2E-01:** Full happy path (case → doc → candidate → confirm → preview → history)
- [ ] **E2E-02:** Manual date entry workflow
- [ ] **E2E-03:** Rejection workflow
- [ ] **E2E-04:** Correction / supersession workflow
- [ ] **E2E-05:** Revoke workflow and blocked re-preview
- [ ] **E2E-06:** Stale state (document deleted mid-workflow via API)
- [ ] **E2E-07:** Double submit (same idempotency_key in parallel tabs)
- [ ] **E2E-08:** XSS via PDF text (script tag rendered as text)
- [ ] **E2E-09:** Zero external network requests (browser network audit)
- [ ] **E2E-10:** Keyboard-only navigation (Tab, Enter, Escape)
- [ ] **E2E-11:** Focus moves to error summary on validation failure
- [ ] **E2E-12:** PRG pattern works (refresh after POST doesn't resubmit)

## Accessibility Automation (axe-core)

- [ ] axe-core scan on case_list.html: zero Critical/Serious
- [ ] axe-core scan on case_detail.html: zero Critical/Serious
- [ ] axe-core scan on workspace.html: zero Critical/Serious
- [ ] axe-core scan on preview_result.html: zero Critical/Serious
- [ ] axe-core scan on confirmation_history.html: zero Critical/Serious
- [ ] axe-core scan on error.html: zero Critical/Serious
- [ ] axe-core vendored locally (no CDN)

## Manual Accessibility (NVDA on Windows)

- [ ] NVDA: full core workflow navigable
- [ ] NVDA: status changes announced
- [ ] NVDA: form labels and errors announced
- [ ] NVDA: warning messages announced
- [ ] 200% zoom: all content accessible without horizontal scroll
- [ ] Keyboard only: all actions reachable
- [ ] High-contrast mode: all content visible
- [ ] Evidence documented in test report

## Offline Reproducibility

- [ ] After `pip install -e ".[dev]"` + `playwright install chromium`: all tests pass without network
- [ ] axe-core loaded from local vendor path
- [ ] No external network requests during test run
