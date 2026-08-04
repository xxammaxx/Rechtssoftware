# Usability Findings — PrivateLegalNavigator v1.0.0rc2

**Date:** 2026-07-31
**Source:** Live browser interaction + RC-017 screenshots

## Critical (0)

No critical usability issues found. All core user paths are reachable and functional.

## High (2)

### H1: No main navigation — sections are disconnected
- **Evidence:** Case detail, legal sources, legal situation, timeline, and evidence pack are only reachable via specific breadcrumb links or back-navigation. No persistent nav bar or tab system.
- **Impact:** Users cannot discover legal sources, timeline, or evidence pack from the case view without knowing the URL structure or following breadcrumb trails.
- **Severity:** High
- **Recommendation:** Add a case-level tab bar (Übersicht | Dokumente | Rechtslage | Verlauf | Evidence)

### H2: Empty states lack onboarding guidance
- **Evidence:** Legal sources status page shows "0 Snapshots, 0 Instrumente, 0 Normen" without explaining how to get data. Timeline and evidence pack show empty headings without first-use instructions.
- **Impact:** First-time users see empty pages with no indication of what to do next.
- **Severity:** High
- **Recommendation:** Add contextual empty-state messages with calls-to-action (e.g., "Noch keine Rechtsquellen importiert. Synchronisation starten →")

## Medium (5)

### M1: Case list offers no filtering or search
- **Evidence:** Single case shown as list item. No search, filter, or sort controls.
- **Impact:** Only relevant with many cases, but the pattern should be established early.
- **Recommendation:** Add simple search/filter as case count grows.

### M2: Document upload uses native file picker only
- **Evidence:** "PDF-Datei" button + "Keine ausgewählt" text. No drag-and-drop zone.
- **Impact:** Functional but less intuitive than drag-and-drop.
- **Recommendation:** Add a drop zone visual affordance around the upload area.

### M3: No visual distinction between navigation and content areas
- **Evidence:** Breadcrumbs and back-links are the primary navigation. No sidebar, no tab bar, no section header navigation.
- **Impact:** Users rely on browser back button.
- **Recommendation:** Add consistent case-level navigation component.

### M4: Evidence pack has no export/print capability
- **Evidence:** Evidence pack renders as HTML page. No print stylesheet, PDF download, or copy button.
- **Impact:** Users cannot easily share or archive the evidence pack.
- **Recommendation:** Add print stylesheet as minimal step; PDF export as enhancement.

### M5: No responsive design visible
- **Evidence:** All pages use static width layout. No mobile/tablet adaptations observed.
- **Impact:** Application is desktop-only in current state.
- **Recommendation:** Add responsive breakpoints (see responsive design requirements).

## Low (3)

### L1: Document type "sonstiges" is not descriptive
- **Evidence:** All uploaded documents show type "sonstiges" (miscellaneous).
- **Recommendation:** Add document type selector or auto-classification.

### L2: No dark mode
- **Evidence:** Light theme only.
- **Recommendation:** Add dark mode toggle (nice-to-have).

### L3: No keyboard shortcut hints
- **Evidence:** Skip link exists but no other keyboard shortcuts documented.
- **Recommendation:** Add shortcut reference page or tooltip hints.

## Notes (Positive Observations)

- **Trust signals are excellent** — Privacy badges, legal disclaimers, and source provenance are consistently and prominently displayed.
- **Warning hierarchy is clear** — Alert boxes with structured lists for multi-part warnings.
- **History/audit trail is thorough** — Full timestamped table of all confirmation actions.
- **Skip link present** — Accessibility baseline is established.
- **No console errors** — Clean JavaScript execution across all tested pages.
