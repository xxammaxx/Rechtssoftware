# Accessibility Checklist — M6-UI

Based on WCAG 2.1 AA criteria. All items must pass before release.

## Keyboard Navigation

**Expected tab order for workspace page:**
1. Navigation (breadcrumb)
2. Candidate list items
3. Selected candidate details panel
4. Reference event radio group / manual date input
5. Evidence note textarea
6. Action buttons (Confirm / Reject / Manual entry)
7. Preview button
8. History link
9. Warnings section (announced by screen reader)

- [ ] **A1:** All workflow steps navigable via Tab / Shift+Tab
- [ ] **A2:** Enter/Space activates focused buttons
- [ ] **A3:** Escape closes dialogs (revoke confirmation)
- [ ] **A4:** Tab order follows logical reading order
- [ ] **A5:** No keyboard traps (focus cannot leave an element)

## Focus Indicators

- [ ] **A6:** Visible focus indicator on all interactive elements
- [ ] **A7:** Focus indicator ≥ 2px solid outline
- [ ] **A8:** Focus indicator contrast ≥ 3:1 against adjacent background
- [ ] **A9:** Focus moves to error summary on validation failure

## Forms and Labels

- [ ] **A10:** `<label>` element for every form control
- [ ] **A11:** `<fieldset>` + `<legend>` for radio button groups
- [ ] **A12:** `aria-required="true"` on required fields
- [ ] **A13:** Error messages linked to fields via `aria-describedby`
- [ ] **A14:** Submit buttons have descriptive text (e.g., "Bezugsdatum bestaetigen", not "OK")

## Live Regions

- [ ] **A15:** `aria-live="polite"` for status updates
- [ ] **A16:** `aria-live="assertive"` for error messages
- [ ] **A17:** `aria-live` regions tested with NVDA

## Color and Contrast

- [ ] **A18:** No information conveyed by color alone (always text + color)
- [ ] **A19:** Normal text contrast ≥ 4.5:1
- [ ] **A20:** Large text contrast ≥ 3:1
- [ ] **A21:** No green = valid / red = invalid patterns without text labels

## Semantic Structure

- [ ] **A22:** Page has exactly one `<h1>`
- [ ] **A23:** Heading hierarchy is sequential (h1 → h2 → h3, no skips)
- [ ] **A24:** Page `<title>` reflects current workflow step
- [ ] **A25:** Lists use `<ul>`/`<ol>` with `<li>` (not divs)
- [ ] **A26:** Tables have `<caption>` and proper `<th>` headers

## Error Handling

- [ ] **A27:** Error summary at top of page on form validation failure
- [ ] **A28:** Error summary links to individual fields
- [ ] **A29:** Error messages are descriptive and specific
- [ ] **A30:** Focus moves to error summary after failed submission

## Motion and Animation

- [ ] **A31:** `prefers-reduced-motion` media query respected
- [ ] **A32:** No content flashes more than 3 times per second

## Screen Reader (NVDA)

- [ ] **A33:** All interactive elements have accessible names
- [ ] **A34:** Status badges have text alternatives
- [ ] **A35:** Warning messages are announced
- [ ] **A36:** Page title updates on navigation
- [ ] **A37:** NVDA tested on Windows with full workflow

## Zoom and Responsive

- [ ] **A38:** Page usable at 200% zoom without horizontal scrolling
- [ ] **A39:** Text spacing adjustable without loss of content
- [ ] **A40:** Content reflows for narrow viewports

## Permanently Visible Disclaimers

- [ ] "Rechtliche Gueltigkeit nicht bewertet" visible on every workspace and results page
- [ ] "Menschliche Pruefung erforderlich" visible on every workspace and results page
- [ ] Disclaimers not hidden in collapsed sections, tooltips, or color-only indicators
