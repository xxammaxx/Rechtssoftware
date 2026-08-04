# Design Governance — PrivateLegalNavigator v1.0.0rc2

**Date:** 2026-07-31

## Principles

1. **No external resources.** All CSS, fonts, icons must be self-contained. CSP: `style-src 'self'`.
2. **Progressive enhancement.** Core functionality works without JavaScript.
3. **Token-first.** All visual values must reference CSS custom properties, never hard-coded.
4. **Template partials over duplication.** Reusable UI patterns go in Jinja partials/includes.
5. **Mobile-first responsive.** Base styles for mobile, enhanced for desktop.

## Adding a New Component

1. Define tokens in `:root` if new values are needed.
2. Create CSS classes following existing BEM-like naming: `.component__element--modifier`.
3. Create a Jinja partial in `templates/` if the component contains HTML structure.
4. Add to `DESIGN-INVENTORY.md`.
5. Test across breakpoints (360px, 768px, 1280px, 1920px).
6. Verify focus, keyboard, and contrast.

## Modifying Existing Styles

1. Check `DESIGN-TOKENS.md` — does a token already exist for this?
2. If modifying a token value, search all usages in templates and CSS.
3. Never override tokens with hard-coded values in templates.
4. Run visual regression test after changes.

## Review Gates

- New CSS: Does it add a new color/font/spacing that duplicates an existing token?
- Template change: Does it break the `<main>` landmark or heading hierarchy?
- Component addition: Does it work at 360px? With keyboard only?
- Visual change: Screenshot diff reviewed and manually approved?

## Owner Decisions Required

- New color palette / rebrand
- New external dependency
- Framework introduction
- JavaScript requirement for core functionality
