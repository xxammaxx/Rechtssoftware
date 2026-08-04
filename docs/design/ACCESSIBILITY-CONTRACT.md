# Accessibility Contract — PrivateLegalNavigator v1.0.0rc2

**Date:** 2026-07-31
**Standard:** WCAG 2.2 Level AA target

## Current Compliance

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Skip to main content | PASS | `.skip-link` in base.html |
| Focus indicators | PASS | 3px outline with offset on `:focus-visible` |
| Semantic HTML landmarks | PASS | `<header role=banner>`, `<main>`, `<footer>`, `<nav>` |
| Heading hierarchy | PARTIAL | All pages have h1, but heading nesting varies |
| Form labels | PASS | All inputs have associated `<label>` |
| Error association | PASS | `.form-error-summary` with list + per-field errors |
| Color contrast (text) | LIKELY PASS | #1a1a1a on #ffffff = 17.3:1 |
| Color contrast (status) | NEEDS CHECK | Status colors on light backgrounds |
| Non-color indicators | PASS | Status badges include dot indicators, borders, and text |
| Keyboard navigation | PARTIAL | Tab order functional but no visible skip-to-section nav |
| Reduced motion | PASS | `prefers-reduced-motion: reduce` disables all transitions |
| Touch targets ≥44px | PASS | Buttons and form inputs have `min-height: 44px` |
| Print styles | PASS | Hides nav chrome, strips background colors |
| Screen reader text | PASS | `.u-visually-hidden` utility available |
| Language attribute | PASS | `<html lang="de">` |
| Viewport meta | PASS | `<meta name="viewport" content="width=device-width, initial-scale=1.0">` |
| No auto-playing content | PASS | No audio/video |

## Gaps

- No ARIA live regions for dynamic content
- No heading-level skip navigation within pages
- No dialog focus trapping (no modals currently exist)
- Status color contrast needs verification (green on light green, amber on light amber)
- No landmark labeling beyond role attributes
- Tables lack `scope` attributes on headers

## Accessibility Testing Approach

- Axe automated scan per page
- Manual keyboard-only navigation test
- Manual focus-order check
- Manual contrast verification
- Screen reader test (Orca on Linux)
