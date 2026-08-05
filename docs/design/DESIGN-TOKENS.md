# Design Tokens — PrivateLegalNavigator v1.0.0rc2

**Date:** 2026-07-31
**Source:** Extracted from `app.css` (all tokens are CSS Custom Properties on `:root`)

## Color Tokens

| Group | Token | Value | Role |
|-------|-------|-------|------|
| Text | `--color-text-primary` | #1a1a1a | Body, headings |
| Text | `--color-text-secondary` | #555555 | Meta, hints, captions |
| Text | `--color-text-muted` | #666666 | Disabled, tertiary info |
| Text | `--color-text-inverse` | #ffffff | On dark backgrounds |
| Surface | `--color-bg-page` | #f5f5f5 | Page background |
| Surface | `--color-bg-surface` | #ffffff | Cards, form fields |
| Surface | `--color-bg-muted` | #f8f8f8 | Muted sections |
| Surface | `--color-bg-emphasis` | #eef2ff | Table row hover, highlights |
| Border | `--color-border-default` | #d4d4d4 | Standard borders |
| Border | `--color-border-light` | #e5e5e5 | Subtle borders |
| Border | `--color-border-emphasis` | #1a1a1a | Strong borders |
| Action | `--color-primary` | #1a1a1a | Primary buttons |
| Action | `--color-primary-hover` | #333333 | Button hover |
| Action | `--color-primary-text` | #ffffff | Text on primary |
| Focus | `--color-focus-ring` | #1a1a1a | Focus indicators |
| Status | `--color-status-unconfirmed` | #6b7280 | Gray status |
| Status | `--color-status-confirmed` | #2d6a4f | Green status |
| Status | `--color-status-rejected` | #78716c | Stone status |
| Status | `--color-status-revoked` | #92400e | Amber status |
| Status | `--color-status-superseded` | #9ca3af | Gray (obsolete) |
| Feedback | `--color-error-text/bg/border` | #991b1b/#fef2f2/#dc2626 | Error states |
| Feedback | `--color-warning-text/bg/border` | #92400e/#fffbeb/#d97706 | Warning states |
| Feedback | `--color-success-text/bg/border` | #166534/#f0fdf4/#22c55e | Success states |
| Feedback | `--color-info-text/bg/border` | #1e3a5f/#eef2ff/#818cf8 | Info states |

## Spacing Scale (4px base)

| Token | Size |
|-------|------|
| `--space-1` | 4px |
| `--space-2` | 8px |
| `--space-3` | 12px |
| `--space-4` | 16px |
| `--space-5` | 20px |
| `--space-6` | 24px |
| `--space-8` | 32px |
| `--space-10` | 40px |
| `--space-12` | 48px |

## Typography Scale

| Token | Size | Usage |
|-------|------|-------|
| `--text-xs` | 13px | Meta, hints, badges |
| `--text-sm` | 14px | Body small, labels |
| `--text-base` | 16px | Body, form fields |
| `--text-md` | 17px | Emphasized body |
| `--text-lg` | 20px | Section headings |
| `--text-xl` | 24px | Page subheadings |
| `--text-2xl` | 32px | Page titles |

Line heights: `--leading-tight` (1.25), `--leading-normal` (1.55), `--leading-relaxed` (1.65)

## Border & Shadow

| Token | Value |
|-------|-------|
| `--radius-sm` | 3px |
| `--radius-md` | 6px |
| `--radius-lg` | 8px |
| `--shadow-card` | 0 1px 3px rgba(0,0,0,0.08) |
| `--shadow-card-hover` | 0 4px 6px rgba(0,0,0,0.07) |

## Layout

| Token | Value |
|-------|-------|
| `--content-max-width` | 1200px |
| `--sidebar-min-width` | 300px |
