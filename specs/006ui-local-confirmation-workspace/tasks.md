# Tasks — M6-UI Local Confirmation Workspace

## Task Structure

Tasks are small, testable, and ordered by dependency.

**Status (2026-07-22):** Slice 1 (T1–T7), Slice 2 (T8–T10 + partial T14), and Slice 4 (T11) are **implemented and verified**.
Slice 3+ (T12, T13, T15–T23) are **pending**.

## Task List

### Phase 1 — Foundation

#### T1 — Add Jinja2 Dependency
- **Goal:** Declare `jinja2>=3.1.0` in pyproject.toml
- **Files:** `pyproject.toml`
- **Tests:** `pip check` passes; `pip install -e .` succeeds
- **Dependencies:** None

#### T2 — Configure Template Engine
- **Goal:** Initialize `Jinja2Templates` in app factory; mount StaticFiles
- **Files:** `app.py`
- **Tests:** Template directory reachable; app starts with template engine
- **Dependencies:** T1

#### T3 — Security Headers Middleware
- **Goal:** Add CSP (HTTP header only), Cache-Control, Referrer-Policy, Cross-Origin headers, Permissions-Policy, and Host validation middleware
- **Files:** `app.py` (middleware stack), `config.py` (allowed hosts)
- **Tests:** Response headers contain CSP; non-matching Host returns 400; Cache-Control: no-store on case routes; all mandatory headers present
- **Dependencies:** T2

#### T4 — Base Template and Static Assets
- **Goal:** Create base HTML layout, CSS, and progressive enhancement JS
- **Files:** `templates/base.html`, `static/css/app.css`, `static/js/enhance.js`
- **Tests:** Base template renders; static files accessible; no external resources in HTML; no CSP meta tag in HTML
- **Dependencies:** T3

### Phase 2 — Read-only Workspace

#### T5 — Case Navigation UI
- **Goal:** Case list and case detail pages
- **Files:** `api/ui_routes.py` (case routes), `templates/case_list.html`, `templates/case_detail.html`
- **Tests:** Case list shows cases; empty state shows hint; case detail shows documents; 404 handled
- **Dependencies:** T4

#### T6 — Document View UI
- **Goal:** Document detail with text preview
- **Files:** `api/ui_routes.py` (document routes)
- **Tests:** Document info renders; text preview renders; no-text document shows hint; 404 handled
- **Dependencies:** T5

#### T7 — Workspace View
- **Goal:** Display Zeitangaben-Kandidaten and Bezugsereignisse
- **Files:** `api/ui_routes.py` (workspace GET routes), `templates/workspace.html`
- **Tests:** Candidates rendered with type and excerpt; RELATIVE_PERIOD marked; neutral terminology; reference events rendered; human_review_required visible
- **Dependencies:** T6

### Phase 3 — Interactive Confirmation

#### T8 — CSRF Token Infrastructure
- **Goal:** CSRF token generation, validation, rotation; Origin header checking
- **Files:** `api/csrf.py` (new), `api/ui_routes.py` (integration)
- **Tests:** Token generation; token validation; constant-time comparison; Origin validation; Referer fallback; missing/invalid/wrong-context/replay tokens rejected
- **Dependencies:** T3

#### T9 — Idempotency Infrastructure
- **Goal:** Idempotency key generation, validation, storage
- **Files:** `api/idempotency.py` (new), `api/ui_routes.py` (integration)
- **Tests:** Key generation; duplicate submission returns original result; parallel submission safe; key expiry; atomic check-and-set
- **Dependencies:** T3

#### T10 — Confirmation Actions
- **Goal:** Confirm, reject, manual entry, correct POST handlers with CSRF + idempotency
- **Files:** `api/ui_routes.py` (confirmation POST routes)
- **Tests:** Confirm sets CONFIRMED; Reject sets REJECTED; Manual entry creates confirmation; Correction supersedes; CSRF required; Idempotency required; PRG redirect; invalid date shows error; server-side revalidation
- **Dependencies:** T7, T8, T9

#### T11 — Calculation Preview ✅
- **Goal:** Preview GET/POST with server-side revalidation
- **Files:** `api/ui_routes.py` (preview routes), `templates/candidates/preview.html`, `application/local_confirmation_workspace_service.py`
- **Tests:** 703 tests (90.31% coverage): Preview rendered with correct date; calculation steps visible; all warnings visible; button disabled when not CONFIRMED; human_review_required visible; legal_validity_assessed=false visible; neutral terminology; cross-resource membership check; candidate reloaded from canonical source; read-only evidence (zero DB writes); repeat POST produces identical results; stale expected state → 409; Axe 0 critical/serious; Playwright E2E with real browser + screenshots
- **Verification:** coverage 90.31%, Axe 0 critical/0 serious, Security: LOW RISK (12/12 passed), Playwright: browser screenshots (6), Restart smoke: PASS, Query-banner fix (9d438b4): effective
- **Dependencies:** T10 (implemented 2026-07-22)

#### T12 — Confirmation History
- **Goal:** Display confirmation history with supersession chain
- **Files:** `api/ui_routes.py` (history route), `templates/confirmation_history.html`
- **Tests:** History table renders; status badges correct; timestamps visible; supersession chain clear; current status marked
- **Dependencies:** T10

#### T13 — Revoke
- **Goal:** Revoke with confirmation dialog; POST handler with CSRF + idempotency
- **Files:** `api/ui_routes.py` (revoke route)
- **Tests:** Revoke succeeds; after revoke status REVOKED; calculation blocked after revoke; requires CSRF + idempotency
- **Dependencies:** T12

### Phase 4 — Hardening

#### T14 — Error State Handling
- **Goal:** Graceful handling of all error responses
- **Files:** `templates/error.html`, `api/ui_routes.py` error handlers
- **Tests:** 400 shows user-friendly message; 403 shows generic CSRF error; 404 shows context; 409 shows conflict; 500 shows generic error (no stack trace); no sensitive IDs in error display; no PII in error responses
- **Dependencies:** T10-T13

#### T15 — Accessibility Implementation
- **Goal:** WCAG 2.1 AA compliance
- **Files:** All templates, CSS
- **Tests:** Keyboard navigation through full workflow; visible focus indicators; labels on all forms; fieldset/legend on radio groups; aria-live regions; error summary at top; semantic heading hierarchy; meaningful button text; prefers-reduced-motion; contrast ratio ≥ 4.5:1
- **Dependencies:** T4-T14

### Phase 5 — Testing

#### T16 — View Model Unit Tests
- **Goal:** Test view model mapping, warning messages, text truncation, error mapping
- **Files:** `tests/unit/test_ui_view_models.py`
- **Tests:** View model correctly maps domain objects; warning codes mapped to German text; text truncation with ellipsis; error codes mapped to user messages; neutral terminology in all labels; no legal terminology in system labels
- **Dependencies:** T7

#### T17 — Template Tests
- **Goal:** Test template rendering, escaping, semantic structure
- **Files:** `tests/unit/test_ui_templates.py`
- **Tests:** Template renders without errors; HTML escaping verified (script tags in text rendered as text); no `| safe` on user data; CSP not in meta tag; semantic heading order; labels on forms
- **Dependencies:** T15

#### T18 — CSRF and Security Unit Tests
- **Goal:** Test CSRF token logic, idempotency, host validation, header generation
- **Files:** `tests/unit/test_ui_security.py`
- **Tests:** Token generation/validation; constant-time comparison; idempotency key lifecycle; host allowlist generation; security header content; Origin validation
- **Dependencies:** T8, T9

#### T19 — Integration Tests
- **Goal:** Test full UI route pipeline with TestClient
- **Files:** `tests/integration/test_ui_routes.py`
- **Tests:** Each GET route returns 200 with correct HTML; form submissions redirect correctly; error states return proper HTML; CSP headers on all responses; no-store on case pages; Host validation blocks wrong host; CSRF positive and negative paths; Idempotency replay; Cross-case and cross-document ID protection; Status conflict handling
- **Dependencies:** T14, T18

#### T20 — Browser E2E Tests
- **Goal:** Full browser-based end-to-end tests with Playwright
- **Files:** `tests/e2e/test_m6ui_workflows.py`
- **Tests:**
  - E2E-01: Full happy path
  - E2E-02: Manual date entry
  - E2E-03: Rejection workflow
  - E2E-04: Correction and supersession
  - E2E-05: Revoke workflow
  - E2E-06: Stale state handling
  - E2E-07: Double submit (idempotency)
  - E2E-08: XSS prevention (script tag in document text)
  - E2E-09: Zero external requests (network audit)
  - E2E-10: Keyboard-only navigation
  - E2E-11: Focus management on errors
- **Dependencies:** T19

#### T21 — Accessibility Automation
- **Goal:** axe-core integration for automated accessibility checks
- **Files:** `tests/e2e/test_accessibility.py`, vendored `axe.min.js`
- **Tests:** axe-core scan on each page; zero Critical or Serious violations; keyboard navigation verification; focus order verification; visible focus indicator verification
- **Dependencies:** T20

#### T22 — Manual Accessibility Audit (NVDA)
- **Goal:** NVDA screen reader verification on Windows
- **Files:** Checklist-based evidence documentation
- **Tests:** Full core workflow via NVDA; status announcements; label association; error announcement; 200% zoom; high-contrast mode
- **Dependencies:** T21

#### T23 — Independent Review
- **Goal:** Read-only review of all changes
- **Files:** Full diff
- **Agent:** review-agent
- **Dependencies:** T22

## Dependency Graph (Build Order)

```
T1 (Jinja2 Dep)
  └→ T2 (Template Config)
      └→ T3 (Security Middleware)
          ├→ T4 (Base Template + Static)
          │   ├→ T5 (Case Nav)
          │   │   └→ T6 (Doc View)
          │   │       └→ T7 (Workspace View)
          │   │           ├→ T10 (Confirmation)
          │   │           │   ├→ T11 (Preview)
          │   │           │   ├→ T12 (History)
          │   │           │   │   └→ T13 (Revoke)
          │   │           │   └→ T14 (Error States)
          │   │           │       ├→ T15 (Accessibility)
          │   │           │       │   └→ T16-T17 (Unit Tests)
          │   │           │       │       └→ T19 (Integration)
          │   │           │       │           └→ T20-T21 (E2E + a11y)
          │   │           │       │               └→ T22 (NVDA)
          │   │           │       │                   └→ T23 (Review)
          │   │           │       └→ T18 (Security Unit Tests)
          ├→ T8 (CSRF Infra)  ←─┘
          └→ T9 (Idempotency) ←─┘
```
