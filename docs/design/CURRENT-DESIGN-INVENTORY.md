# Current Design Inventory — PrivateLegalNavigator

**Stand:** 31.07.2026 | **Quelle:** `app.css` (1605 Zeilen) | **Methode:** CSS-Token-Extraktion + Template-Analyse

## Farbpalette

### Text & Hintergrund
| Token | Wert |
|-------|------|
| `--color-text-primary` | #1a1a1a |
| `--color-text-secondary` | #555555 |
| `--color-text-muted` | #666666 |
| `--color-text-inverse` | #ffffff |
| `--color-bg-page` | #f5f5f5 |
| `--color-bg-surface` | #ffffff |
| `--color-bg-muted` | #f8f8f8 |
| `--color-bg-emphasis` | #eef2ff |

### Interaktion
| Token | Wert |
|-------|------|
| `--color-primary` | #1a1a1a (Schwarz) |
| `--color-primary-hover` | #333333 |
| `--color-focus-ring` | #1a1a1a |
| `--color-border-default` | #d4d4d4 |
| `--color-border-emphasis` | #1a1a1a |

### Status-Farben
| Status | Text | Hintergrund | Border |
|--------|------|-------------|--------|
| Unbestätigt | #6b7280 | #f9fafb | #d1d5db |
| Bestätigt | #2d6a4f | #f0fdf6 | #86dbb7 |
| Abgelehnt | #78716c | #fafaf9 | #d6d3d1 |
| Widerrufen | #92400e | #fffbeb | #fcd34d |
| Ersetzt | #9ca3af | #f3f4f6 | #e5e7eb |

### Feedback
| Typ | Text | Hintergrund | Border |
|-----|------|-------------|--------|
| Fehler | #991b1b | #fef2f2 | #dc2626 |
| Warnung | #92400e | #fffbeb | #d97706 |
| Erfolg | #166534 | #f0fdf4 | #22c55e |
| Info | #1e3a5f | #eef2ff | #818cf8 |

## Typografie

- **Font:** Inter (System-Fallback)
- **Mono:** ui-monospace, Cascadia Code
- **Größen:** 13px – 32px (8 Stufen)
- **Gewichte:** 400, 500, 600, 700
- **Zeilenhöhen:** 1.25, 1.55, 1.65

## Komponenten-Katalog

### Layout
- `app-header` — 2px schwarzer Bottom-Border, flex
- `app-footer` — Sticky-Bottom, zentriert
- `main-container` — max-width 1200px, zentriert
- `skip-link` — position:absolute, top:-100%

### Navigation
- `breadcrumbs` — ›-getrennt, aria-current
- `case-tabs` — 2px Bottom-Border, aktiver Tab mit aria-current

### Typografie
- `page-title` — 32px, bold, letter-spacing -0.02em
- `page-subtitle` — 16px, max-width 65ch
- `section-title` — 20px, semibold

### Cards
- `card` — 1px Border, 6px Radius, Subtle-Shadow
- `card__header` — bg-muted, uppercase
- `card__body` — 16px Padding
- `card--status-*` — 5 Varianten mit farbiger Top-Border

### Formulare
- `form-field` — Label + Input + Hint
- `form-error-summary` — Rote Box mit Fehlerliste
- Inputs — 44px min-height, 24rem max-width
- `btn` — 5 Varianten (primary/secondary/danger/small/link), 44px min-height

### Datenanzeige
- `data-list` — Grid dt/dd
- `status-badge` — Mit ::before Dot, 5 Farbvarianten
- `diff-callout` — Vergleichsanzeige für Datumsdifferenzen
- `history-table` — Sticky-Header, Zebra-Striping

### Feedback
- `flash-banner` — Erfolg/Info mit role="status"
- `notice` — Info/Legal mit linker Border
- `warnings-box` — Mit role="alert"

## Leere Zustände

Definiert als `empty-state` Paragraph (kein Icon, zentriert als Text).

## Responsive

Ein Breakpoint: `@media (max-width: 600px)` — nur für Tab-Navigation.

## Auffälligkeiten

1. Keine Farbpalette jenseits von Grau/Schwarz — Designsystem ist monochromatisch
2. Keine Icons, keine Illustrationen
3. Keine Animationen außer Transition auf Hover/Focus
4. `role="alert"` auf `warnings-box` ist semantisch fragwürdig für persistente Inhalte
5. Keine `prefers-reduced-motion` Media Query (nur Transition, daher vertretbar)
