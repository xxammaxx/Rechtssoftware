# Tasks — M6-UI Local Confirmation Workspace

## Task Structure

Tasks are small, testable, and ordered by dependency. **No implementation in this specification run** — these tasks are for the future build phase.

## Task List

### T1 — Truth Mirror Update
- **Goal:** Update README and ADR-002 status to reflect M6-A completion
- **Files:** `README.md`, `docs/architecture/adr-002-confirmed-reference-events.md`
- **Tests:** Baseline unchanged (379 passed)
- **Dependencies:** None

### T2 — Add Jinja2 Dependency
- **Goal:** Declare `jinja2>=3.1.0` in pyproject.toml
- **Files:** `pyproject.toml`
- **Tests:** `pip check` passes; `pip install -e .` succeeds
- **Dependencies:** T1

### T3 — Configure Template Engine
- **Goal:** Initialize `Jinja2Templates` in app factory
- **Files:** `app.py`
- **Tests:** Template directory is reachable; app starts with template engine
- **Dependencies:** T2

### T4 — Security Headers Middleware
- **Goal:** Add CSP, Cache-Control, Referrer-Policy, and Host validation middleware
- **Files:** `app.py` (middleware stack)
- **Tests:** Response headers contain CSP; non-127.0.0.1 Host returns 400; Cache-Control: no-store on case routes
- **Dependencies:** T3

### T5 — Base Template and Static Assets
- **Goal:** Create base HTML layout, CSS, and optional JS enhancement
- **Files:** `templates/base.html`, `static/css/app.css`, `static/js/enhance.js`
- **Tests:** Base template renders; static files accessible; no external resources in HTML
- **Dependencies:** T4

### T6 — Case Navigation UI
- **Goal:** Case list and case detail pages
- **Files:** `ui_routes.py` (case routes), `templates/case_list.html`, `templates/case_detail.html`
- **Tests:** Case list shows cases; empty state shows hint; case detail shows documents; 404 handled
- **Dependencies:** T5

### T7 — Document Selection UI
- **Goal:** Document list within case, document text preview
- **Files:** `ui_routes.py` (document routes)
- **Tests:** Document list renders; text preview renders; no-text document shows hint; 404 handled
- **Dependencies:** T6

### T8 — Deadline Candidate View
- **Goal:** Display deadline candidates from document text analysis
- **Files:** `ui_routes.py` (deadline routes), `templates/deadline_workspace.html`
- **Tests:** Candidates rendered with type and excerpt; RELATIVE_PERIOD marked; empty candidates shows hint; human_review_required visible
- **Dependencies:** T7

### T9 — Reference Event View
- **Goal:** Display reference event candidates for selected RELATIVE_PERIOD deadline
- **Files:** `ui_routes.py` (reference event routes), template extensions
- **Tests:** Events rendered with status UNCONFIRMED; evidence text displayed; MULTIPLE_REFERENCE_EVENTS warning visible; no auto-selection
- **Dependencies:** T8

### T10 — Confirmation Actions
- **Goal:** Confirm, reject, and manual entry forms with server-side handling
- **Files:** `ui_routes.py` (confirm routes), template extensions
- **Tests:** Confirm sets CONFIRMED; Reject sets REJECTED; Manual entry creates confirmation; invalid date shows error; double-submit prevented; redirect-after-POST works
- **Dependencies:** T9

### T11 — Calculation Preview
- **Goal:** Request and display calculation preview with full trace
- **Files:** `ui_routes.py` (preview routes), `templates/calculation_result.html`
- **Tests:** Preview rendered with correct date; calculation steps visible; all warnings visible; button disabled when UNCONFIRMED/REJECTED/REVOKED; human_review_required visible; legal_validity_assessed=false visible; "Berechnungsvorschau" label used (not "Fristende")
- **Dependencies:** T10

### T12 — Confirmation History
- **Goal:** Display full confirmation history with supersession chain
- **Files:** `ui_routes.py` (history route), `templates/confirmation_history.html`
- **Tests:** History table renders; status badges correct; timestamps visible; supersession chain clear; current status marked
- **Dependencies:** T10

### T13 — Revoke and Correction
- **Goal:** Revoke with confirmation dialog; correction creates new confirmation
- **Files:** `ui_routes.py` (revoke/correct routes), template extensions
- **Tests:** Revoke shows dialog; after revoke, status REVOKED; calculation blocked after revoke; correction creates new CONFIRMED, old → SUPERSEDED
- **Dependencies:** T12

### T14 — Error State Handling
- **Goal:** Graceful handling of all API error responses
- **Files:** `templates/error.html`, `ui_routes.py` error handlers
- **Tests:** 400 shows user-friendly message; 404 shows "not found" context; 500 shows generic error (no stack trace); no sensitive IDs in error display; stale state warning when document deleted mid-workflow
- **Dependencies:** T6-T13

### T15 — Accessibility Implementation
- **Goal:** WCAG 2.1 AA compliance for all UI pages
- **Files:** All templates, CSS
- **Tests:** Keyboard navigation through full workflow; visible focus indicators; label elements on all forms; fieldset/legend on radio groups; aria-live regions; error summary at top; semantic heading hierarchy; meaningful button text; prefers-reduced-motion support; 4.5:1 contrast ratio
- **Dependencies:** T5-T14

### T16 — Unit Tests (View Models and Templates)
- **Goal:** Test view model mapping, warning prioritization, text truncation, error mapping
- **Files:** `tests/unit/test_ui_view_models.py`, `tests/unit/test_ui_templates.py`
- **Tests:** View model correctly maps domain objects; warning codes mapped to German text; text truncation with ellipsis; error codes mapped to user messages; template renders without errors; HTML escaping verified; sensitive values not in hidden fields
- **Dependencies:** T15

### T17 — Integration Tests (UI Routes)
- **Goal:** Test full UI route → service → template rendering pipeline
- **Files:** `tests/integration/test_ui_routes.py`
- **Tests:** Each route returns 200 with correct HTML; form submissions redirect correctly; error states return proper HTML; CSP headers present on all responses; no-store headers on case pages; Host validation blocks wrong host
- **Dependencies:** T16

### T18 — Browser E2E Tests
- **Goal:** Full browser-based end-to-end tests with Playwright
- **Files:** `tests/e2e/`
- **Tests:**
  - E2E-01: Full happy path (case → doc → candidate → confirm → preview → history)
  - E2E-02: Manual date entry workflow
  - E2E-03: Rejection workflow
  - E2E-04: Correction and supersession workflow
  - E2E-05: Revoke workflow
  - E2E-06: Stale state (document deleted mid-workflow)
  - E2E-07: Double submit prevention
  - E2E-08: XSS prevention (PDF with script tag in text)
  - E2E-09: Zero external requests (network audit)
  - E2E-10: Keyboard-only navigation
  - E2E-11: Focus management on errors
- **Dependencies:** T17

### T19 — Security Tests
- **Goal:** Verify security headers, XSS protection, Host validation
- **Files:** `tests/unit/test_ui_security.py`
- **Tests:** CSP header present and correct; no inline scripts; no external resources in HTML; Host header validation; Cache-Control headers; Referrer-Policy header; X-Content-Type-Options header; no sensitive IDs in error responses
- **Dependencies:** T4, T17

### T20 — Documentation Update
- **Goal:** Update README, architecture docs, and M6-UI status
- **Files:** `README.md`, `docs/architecture/` updates
- **Tests:** N/A (structural change)
- **Dependencies:** T18, T19

### T21 — Independent Review
- **Goal:** Read-only review of all changes
- **Files:** Full diff
- **Tests:** Reviewer agent evaluates code quality, security, spec compliance
- **Dependencies:** T20

## Task Dependencies (Build Order)

```
T1 (Truth Mirror)
  └→ T2 (Jinja2 Dep)
      └→ T3 (Template Config)
          └→ T4 (Security Headers)
              └→ T5 (Base Template)
                  ├→ T6 (Case Nav)
                  │   └→ T7 (Doc Selection)
                  │       └→ T8 (Deadline Candidates)
                  │           └→ T9 (Reference Events)
                  │               ├→ T10 (Confirmation)
                  │               │   ├→ T11 (Calculation Preview)
                  │               │   └→ T12 (History)
                  │               │       └→ T13 (Revoke/Correct)
                  │               └→ T14 (Error States)
                  ├→ T15 (Accessibility)
                  ├→ T16 (Unit Tests)
                  ├→ T17 (Integration Tests)
                  │   └→ T18 (Browser E2E)
                  ├→ T19 (Security Tests)
                  └→ T20 (Documentation)
                      └→ T21 (Independent Review)
```
