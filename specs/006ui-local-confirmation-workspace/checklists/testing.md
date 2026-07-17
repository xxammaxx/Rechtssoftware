# Testing Checklist — M6-UI

## Test Strategy Overview

| Layer | Type | Framework | Scope |
|-------|------|-----------|-------|
| Unit | View models | pytest | View model mapping, warning display, text truncation |
| Unit | Templates | pytest + httpx | Template rendering, escaping, security metadata |
| Integration | UI Routes | pytest + httpx | Full route → service → template pipeline |
| Integration | Security | pytest + httpx | Headers, CSP, Host validation |
| E2E | Browser | Playwright | Complete user workflows |
| Accessibility | Manual + auto | axe-core, NVDA | WCAG 2.1 AA criteria |

## Unit Test Cases

### View Models (test_ui_view_models.py)

- [ ] `CaseListView` correctly maps from `CaseService.list_cases()` output
- [ ] `CaseDetailView` includes document list with correct metadata
- [ ] `DeadlineWorkspaceView` maps candidates with correct type labels
- [ ] `ReferenceEventsView` marks current status correctly
- [ ] `CalculationPreviewView` includes all mandatory warnings
- [ ] `HistoryView` sorts entries by timestamp descending
- [ ] Warning codes mapped to correct German messages
- [ ] Error codes mapped to correct German messages
- [ ] Event types mapped to correct German labels
- [ ] Confirmation methods mapped to correct German labels
- [ ] Source types mapped to correct German labels
- [ ] Evidence text truncated with ellipsis at 500 chars
- [ ] Filename not exceeding display width

### Templates (test_ui_templates.py)

- [ ] `case_list.html` renders case titles (verify HTML escaping)
- [ ] `case_list.html` shows "Keine Fälle vorhanden" when empty
- [ ] `case_detail.html` shows "Keine Dokumente" when empty
- [ ] `deadline_workspace.html` renders candidate types
- [ ] `deadline_workspace.html` shows human_review_required
- [ ] `calculation_result.html` shows "Berechnungsvorschau" (NOT "Fristende")
- [ ] `calculation_result.html` includes all adjustment rows
- [ ] `calculation_result.html` shows human_review_required=true
- [ ] `calculation_result.html` shows legal_validity_assessed=false
- [ ] `confirmation_history.html` shows supersession chain
- [ ] `error.html` shows user-friendly message without IDs
- [ ] No `| safe` filter on user-provided data

### XSS Prevention

- [ ] PDF text with `<script>alert(1)</script>` rendered as escaped text
- [ ] Filename with `<img src=x onerror=alert(1)>` rendered as escaped text
- [ ] Evidence_note with HTML entities rendered as escaped text
- [ ] No `innerHTML` usage in enhancement JS

## Integration Test Cases (test_ui_routes.py)

### Case Navigation

- [ ] `GET /ui/cases` returns 200 with case list HTML
- [ ] `GET /ui/cases` with no cases returns 200 with empty state
- [ ] `GET /ui/cases/{id}` returns 200 with case detail
- [ ] `GET /ui/cases/{id}` with unknown ID returns 404 error page

### Document View

- [ ] `GET /ui/cases/{id}/documents/{did}` returns 200 with document info
- [ ] Document with text shows text preview
- [ ] Document without text shows "Kein Text"

### Deadline Workspace

- [ ] `GET .../deadlines` returns 200 with candidate list
- [ ] `GET .../deadlines` with no candidates shows appropriate hint
- [ ] `POST .../deadlines` triggers analysis and redirects

### Reference Events

- [ ] `GET .../events` with relative candidate returns reference events
- [ ] `GET .../events` with non-relative candidate returns error page

### Confirmation

- [ ] `POST .../confirm` with valid data confirms and redirects
- [ ] `POST .../confirm` with invalid date returns error with re-rendered form
- [ ] `POST .../reject` rejects and redirects
- [ ] `POST .../manual` with valid date creates confirmation
- [ ] `POST .../manual` without evidence_note shows warning
- [ ] Double submit prevention: second POST while first pending

### Calculation Preview

- [ ] `POST .../preview` with confirmed event returns preview page
- [ ] `POST .../preview` without confirmation returns error
- [ ] Preview page contains all mandatory warnings

### History

- [ ] `GET .../history` returns history page with entries
- [ ] History shows supersession chain correctly

### Revoke

- [ ] `POST .../revoke` with valid confirmation_id revokes and redirects
- [ ] `POST .../revoke` with revoked confirmation returns error

### Security Headers

- [ ] All `/ui/*` responses include CSP header
- [ ] Case pages include `Cache-Control: no-store`
- [ ] All responses include `X-Content-Type-Options: nosniff`
- [ ] All responses include `Referrer-Policy: no-referrer`
- [ ] Request with `Host: evil.com` returns 400

### Error Handling

- [ ] 404 returns error page with "nicht gefunden"
- [ ] 500 returns error page without stack trace
- [ ] Error page does not contain UUIDs in visible text
- [ ] Validation error returns form with inline error messages

## Browser E2E Test Cases (test_e2e.py, Playwright)

- [ ] **E2E-01:** Full happy path (case → doc → candidate → confirm → preview → history)
- [ ] **E2E-02:** Manual date entry workflow
- [ ] **E2E-03:** Rejection workflow
- [ ] **E2E-04:** Correction / supersession workflow
- [ ] **E2E-05:** Revoke workflow
- [ ] **E2E-06:** Stale state (document deleted mid-workflow)
- [ ] **E2E-07:** Double submit prevention
- [ ] **E2E-08:** XSS via PDF text (script tag rendered as text)
- [ ] **E2E-09:** Zero external network requests (browser network audit)
- [ ] **E2E-10:** Keyboard-only navigation (Tab, Enter, Escape, arrow keys)
- [ ] **E2E-11:** Focus moves to error summary on validation failure
- [ ] **E2E-12:** Screen reader announces live region updates

## Accessibility Verification

- [ ] Keyboard navigation through full workflow
- [ ] Visible focus indicators on all interactive elements
- [ ] Labels on all form controls
- [ ] Fieldset/legend on radio button groups
- [ ] Error summary at top of form
- [ ] Semantic heading hierarchy
- [ ] Meaningful button text
- [ ] Contrast ratio ≥ 4.5:1
- [ ] `prefers-reduced-motion` respected
- [ ] Screen reader test (NVDA on Windows)
