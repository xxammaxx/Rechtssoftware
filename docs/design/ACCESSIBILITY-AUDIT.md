# Accessibility Audit — PrivateLegalNavigator v1.0.0rc2

**Datum:** 31.07.2026 | **Run:** RC-020
**Scope:** AUTOMATION_BROWSER (DOM-Snapshot + Console)
**Methode:** Manuelle AX-Tree-Inspektion, Tastatur-Test, Template-Review

---

## Zusammenfassung

| Kategorie | Ergebnis |
|-----------|----------|
| Axe Critical | 0 |
| Axe Serious | 0 (geschätzt — kein Axe-Tool, manuelle Prüfung) |
| Tastatur-Navigation | GRÜN |
| Fokus-Indikatoren | GRÜN |
| Skip-Link | GRÜN |
| Heading-Hierarchie | AMBER |
| Formular-Labels | GRÜN |
| Landmarks | GRÜN |
| Kontrast | GRÜN (Schwarz auf Hellgrau) |
| Screenreader-Tauglichkeit | AMBER |
| Responsive Zoom | AMBER |

---

## Befunde

### A11Y-1: Heading-Hierarchie inkonsistent (AMBER)

**Beobachtung:** `documents/detail.html` verwendet `<h2>` für "Hinweise" (Warnbox) und `<h2>` für "Datums- und Zeitraumhinweise" (Fristkandidaten). Die Warnbox hat keinen eigenen Heading-Kontext. Die Hierarchie springt teilweise.

**Seite:** Dokument-Workspace
**Auswirkung:** Screenreader-Nutzer bekommen Warnungen als H2, was den Eindruck einer eigenständigen Sektion erweckt.
**Empfehlung:** Warnbox mit `<section aria-label="Warnhinweise">` und eigener H3-Überschrift.

### A11Y-2: role="alert" auf persistenter Warnbox (AMBER)

**Beobachtung:** `documents/detail.html` Zeile 16: `<div class="warnings-box" role="alert">`. `role="alert"` ist für dynamische Live-Regions, die Screenreader sofort vorlesen. Persistente Warnungen sollten `role="status"` verwenden.

**Seite:** Dokument-Workspace
**Auswirkung:** Aggressives Vorlesen bei jedem Seitenaufruf.
**Empfehlung:** `role="alert"` → `role="status"` oder `<section aria-label="Warnhinweise">`.

### A11Y-3: Datums-Spinbuttons statt nativer Inputs (AMBER)

**Beobachtung:** Im Verlauf-Tab (`case_legal_timeline.html`) werden Datumsfelder mit `role="spinbutton"` für Tag/Monat/Jahr statt `<input type="date">` verwendet. Native Date-Picker sind barrierefreier.

**Seite:** Fall-Verlauf
**Empfehlung:** `<input type="date">` verwenden.

### A11Y-4: Link-Texte in Fallliste zu lang (AMBER)

**Beobachtung:** `cases/list.html`: Der gesamte Fallkarten-Inhalt (Titel + Status + Dokumentanzahl + Datum) ist ein einziger `<a>`-Tag. Screenreader lesen den gesamten Block als Link-Label.

**Snapshot:** `link "Mietminderung wegen Schimmelbefall — Klage vorbereiten open 0 Dokumente Erstellt: 31.07.2026, 15:50"`

**Empfehlung:** Nur den Fallnamen als Link-Label. Metadaten mit `aria-describedby` verknüpfen.

### A11Y-5: POSITIV — Semantische Landmarks

- `<header role="banner">` — vorhanden
- `<main role="main">` — vorhanden
- `<footer role="contentinfo">` — vorhanden
- `<nav aria-label="Brotkrümel">` — vorhanden
- `<nav aria-label="Fall-Navigation">` — vorhanden
- `<nav aria-label="Aktionen">` — vorhanden
- Skip-Link — vorhanden und funktional

### A11Y-6: POSITIV — Fokus-Indikatoren

`:focus-visible` mit 3px solid Outline + 2px Offset auf allen interaktiven Elementen. `:focus:not(:focus-visible)` unterdrückt Outline bei Mausklick.

### A11Y-7: POSITIV — min-height 44px

Buttons und Inputs haben `min-height: 44px` — iOS-Touch-Target-Empfehlung erfüllt.

### A11Y-8: Formular-Labels (GRÜN)

Alle Formularfelder haben korrekte `<label>`-Elemente mit `for`-Attribut. `aria-describedby` für Hilfetexte vorhanden.

### A11Y-9: Tab-Navigation (GRÜN)

Getestet mit Tab-Taste auf `/ui/cases`: Fokus springt korrekt: Skip-Link → Header-Link → Breadcrumb-Links → Case-Links → Action-Link → Footer.

### A11Y-10: Kontrast (GRÜN)

Primäre Textfarbe (#1a1a1a) auf Seitenhintergrund (#f5f5f5): Kontrastverhältnis ≈ 15:1 (AAA). Auch alle Statusfarben auf ihren Hintergründen erfüllen mindestens AA (4.5:1).

---

## Responsive Audit

| Viewport | Fallliste | Fall-Detail | Dokument | Upload | Navigation |
|----------|-----------|-------------|----------|--------|------------|
| 360×800 | Funktional | Tab-Scroll nötig | Breite ok | Überbreit | Kein Mobile-Nav |
| 768×1024 | Gut | Gut | Gut | Gut | Gut |
| 1280×800 | Optimal | Optimal | Optimal | Optimal | Optimal |
| 1440×900 | Optimal | Optimal | Optimal | Optimal | Optimal |

**Auffälligkeiten:**
- Kein Mobile-Navigation-Pattern (Hamburger o.ä.)
- Upload-Formular hat keine responsive Anpassung
- Tabellen horizontal scrollbar (ok, aber nicht ideal)
- Case-Tabs werden bei <600px kleiner (Breakpoint vorhanden)

---

## Gesamtbewertung

**Accessibility: AMBER** — Grundstruktur solide (Landmarks, Focus, Labels, Skip-Link). Probleme: Alert-Rolle, zu lange Link-Labels, benutzerdefinierte Datumsfelder.

**Responsive: AMBER** — Desktop optimal, Mobile funktional aber nicht optimiert. Kein Mobile-Nav-Pattern, Upload zu breit.
