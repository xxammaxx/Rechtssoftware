# Design Inventory — PrivateLegalNavigator v1.0.0rc2

**Date:** 2026-07-31
**CSS File:** `src/private_legal_navigator/presentation/static/css/app.css` (1559 lines)
**Templates:** 15 Jinja2 templates in `presentation/templates/`

## Colors

| Token | Value | Usage |
|-------|-------|-------|
| --color-text-primary | #1a1a1a | Body text |
| --color-text-secondary | #555555 | Meta, hints |
| --color-text-muted | #666666 | Muted info |
| --color-bg-page | #f5f5f5 | Page background |
| --color-bg-surface | #ffffff | Card backgrounds |
| --color-bg-muted | #f8f8f8 | Muted sections |
| --color-primary | #1a1a1a | Primary buttons, focus |
| --color-focus-ring | #1a1a1a | Focus indicators |

Status colors: unconfirmed (gray), confirmed (green), rejected (stone), revoked (amber), superseded (gray)

## Typography

- Font stack: Inter → system-ui → sans-serif (no external fonts)
- Mono stack: Cascadia Code → Consolas → monospace
- Scale: 13px / 14px / 16px / 17px / 20px / 24px / 32px
- Weights: 400 / 500 / 600 / 700

## Components (existing in CSS)

| Component | Classes | Status |
|-----------|---------|--------|
| Skip Link | `.skip-link` | Implemented |
| Header | `.app-header`, `.app-header__inner`, `.app-header__home`, `.app-header__local-badge` | Implemented |
| Footer | `.app-footer` | Implemented |
| Breadcrumbs | `.breadcrumbs` | Implemented |
| Page Title | `.page-title`, `.page-subtitle`, `.section-title` | Implemented |
| Notice | `.notice`, `.notice--review`, `.notice--legal` | Implemented |
| Card | `.card`, `.card__header`, `.card__body`, `.card--status-*` | Implemented |
| Data List | `.data-list`, `.data-list--compact` | Implemented |
| Status Badge | `.status-badge`, `.status-*` (5 variants) | Implemented |
| Flash Banner | `.flash-banner--success`, `.flash-banner--info` | Implemented |
| Diff Callout | `.diff-callout`, `.diff-callout--match` | Implemented |
| Form Fields | `.form-field`, `.form-field--error`, `.form-error-summary` | Implemented |
| Buttons | `.btn`, `.btn--primary`, `.btn--secondary`, `.btn--danger`, `.btn--small`, `.btn--link` | Implemented |
| History Table | `.table-container`, `table`, `.history-status-cell--*` | Implemented |
| Workspace Grid | `.workspace-grid`, `.workspace-main`, `.workspace-sidebar` | Implemented |
| Item List/Card | `.item-list`, `.item-card`, `.item-card__title`, `.item-card__meta` | Implemented |
| Empty State | `.empty-state` | Implemented |
| Error Page | `.error-page`, `.error-page__code`, `.error-box` | Implemented |
| Evidence Text | `.evidence-text` | Implemented |
| Candidate Card | `.candidate-list`, `.candidate-card-item`, `.candidate-card-item__*` | Implemented |
| Warnings Box | `.warnings-box`, `.warning-item`, `.warning-code` | Implemented |
| Sync History | `.sync-history-section`, `.sync-history-table` | Implemented |

## Missing Components

| Component | Priority |
|-----------|----------|
| Case Tab Navigation | HIGH — no case-level nav exists |
| Drag-and-drop upload zone | MEDIUM |
| Loading spinner | MEDIUM |
| Dark mode toggle | LOW |
| Notification/Toast | LOW |

## Responsive Behavior

- Base: single column
- Tablet (≥600px): larger padding
- Desktop (≥960px): two-column workspace grid with sticky sidebar
- Mobile (≤600px): reduced font sizes, single-column data lists
- Print: hides navigation, strips colors
- Reduced motion: disables all transitions

## Accessibility Features

- Skip link ✓
- Focus indicators ✓ (3px outline with offset)
- prefers-reduced-motion ✓
- Semantic HTML (header, main, nav, footer) ✓
- Screen-reader utility (`.u-visually-hidden`) ✓
- Min 44px hit targets ✓
