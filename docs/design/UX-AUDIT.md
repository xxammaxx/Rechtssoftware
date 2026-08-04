# UX-Audit: PrivateLegalNavigator v1.0.0rc2

**Datum:** 31.07.2026
**Prüfumfang:** Vollständige Anwendung (9 Routen, 4 Tabs, alle Zustände)
**Methode:** Sichtbarer Browser, Accessibility-Tree-Analyse, Template-Review, Konsolencheck
**Ergebnis:** 15 Befunde (2 Kritisch, 5 Hoch, 5 Mittel, 3 Niedrig)

---

## Executive Summary

Die Anwendung ist funktional solide und architektonisch sauber. Die größten UX-Probleme liegen nicht in der Bedienbarkeit, sondern in der **semantischen Übersetzung**: technische Enum-Werte, englische Statuscodes und interne Warncodes werden ungefiltert an Nutzer weitergegeben. Dies untergräbt das Vertrauen nicht-technischer Anwender (Bürger ohne juristische Vorbildung) und erzeugt einen „Werkzeugkasten-Charakter" statt eines vertrauenswürdigen Produkts.

Die visuelle Hierarchie ist grundsätzlich funktional, aber die Informationsdichte ist unausgewogen: die Upload-Fläche dominiert die Fall-Detailseite, während kritische Warnhinweise mit technischen Codes im Dokument-Workspace den Nutzer überfordern. Eine sichtbare Hauptnavigation fehlt.

Keine JavaScript-Fehler, keine Accessibility-Blocker (Skip-Link, Fokus-Indikatoren, semantische Landmarks sind vorhanden). Die Tastaturbedienung funktioniert grundsätzlich.

---

## Kritische Befunde

### C1: Technische Enum-Werte im Frontend sichtbar (LEGAL_CALCULATION_NOT_PERFORMED)

**Beobachtung:** Im Dokument-Workspace erscheint die Warnung:
> LEGAL_CALCULATION_NOT_PERFORMED: Es wurde keine rechtliche Frist berechnet.

Der Code `LEGAL_CALCULATION_NOT_PERFORMED` ist ein interner Enum-Wert und sollte niemals im Frontend erscheinen. Gleiches gilt für `MULTIPLE_DEADLINE_CANDIDATES`.

**Betroffene Seite:** `/ui/cases/{id}/documents/{id}` (Dokument-Workspace)
**Template:** `documents/detail.html`, Zeile 21: `{{ warning.code }}`
**Auswirkung:** Verwirrt nicht-technische Nutzer. Vermittelt den Eindruck eines unfertigen Entwickler-Tools statt einer Bürgeranwendung.
**Schweregrad:** KRITISCH
**Empfehlung:** `warning.code` nicht rendern. Stattdessen menschenlesbare Überschriften pro Warnungstyp:
- LEGAL_CALCULATION_NOT_PERFORMED → „Keine automatische Fristberechnung möglich"
- MULTIPLE_DEADLINE_CANDIDATES → „Mehrere Fristkandidaten erkannt"

---

### C2: Status „open" in Englisch statt Deutsch

**Beobachtung:** Auf der Fallliste und der Fall-Detailseite wird der Status als `open` angezeigt.
**Betroffene Templates:** `cases/list.html` Zeile 31, `cases/detail.html`
**Auswirkung:** Inkonsistente Sprachverwendung. Deutsche Nutzer erwarten „Offen".
**Schweregrad:** KRITISCH
**Empfehlung:** Status-Mapping im ViewModel: `open → "Offen"`, `closed → "Abgeschlossen"`

---

## Hohe Befunde

### H1: Keine sichtbare Hauptnavigation zwischen Modulen

**Beobachtung:** Der Header enthält nur den Anwendungsnamen und das „Nur lokal"-Badge. Es gibt keinen Weg, von der Fallansicht zu den Rechtsquellen oder der Rechtssuche zu gelangen, ohne die URL zu kennen.
**Betroffene Seiten:** Alle
**Auswirkung:** Nutzer finden wichtige Funktionen (Rechtsquellensuche) nicht. Die Anwendung wirkt fragmentiert.
**Schweregrad:** HOCH
**Empfehlung:** Header-Navigation mit mindestens: „Fälle", „Rechtsquellen", „Suche"

---

### H2: Upload-Fläche dominiert die Fall-Detailseite

**Beobachtung:** Das Upload-Formular mit Fieldset, Legend, Dateiauswahl und Hinweistext nimmt etwa 40% der sichtbaren Fläche ein — selbst wenn bereits Dokumente vorhanden sind. Die Dokumentenliste erscheint darüber, aber die visuelle Gewichtung ist umgekehrt.
**Betroffene Seite:** `/ui/cases/{id}`
**Auswirkung:** Die Hauptaufgabe (Dokumente sichten und bearbeiten) wird visuell herabgestuft. Upload sollte sekundär sein.
**Schweregrad:** HOCH
**Empfehlung:** Upload in eine ausklappbare Sektion oder an das Ende der Seite verschieben. „Dokument hinzufügen"-Button mit Slide-out/Dropdown statt dauerhaftem Fieldset.

---

### H3: role="alert" für persistente Warnhinweise

**Beobachtung:** Im Dokument-Workspace werden Warnungen in einem Container mit `role="alert"` gerendert (`documents/detail.html` Zeile 16). `role="alert"` ist für live regions gedacht, die Screenreader sofort vorlesen. Persistente Hinweise gehören nicht in eine Alert-Rolle.
**Betroffene Seite:** `/ui/cases/{id}/documents/{id}`
**Auswirkung:** Screenreader-Nutzer bekommen die Warnungen aggressiv vorgelesen, auch wenn sie bereits bekannt sind.
**Schweregrad:** HOCH
**Empfehlung:** `role="alert"` durch `role="status"` oder eine semantisch korrekte `<section>` mit `aria-label` ersetzen.

---

### H4: Sehr lange Link-Texte in der Fallliste

**Beobachtung:** Jeder Fall in der Liste ist ein einziger langer Link, dessen Text aus Titel + Status + Dokumentanzahl + Datum besteht. Screenreader lesen den gesamten Text als einen Link-Label vor.
**Snapshot:** `link "Mietminderung wegen Schimmelbefall — Klage vorbereiten open 0 Dokumente Erstellt: 31.07.2026, 15:50"`
**Betroffene Seite:** `/ui/cases`
**Auswirkung:** Schlecht scanbar, Accessibility-Problem, kein visueller Fokus auf dem Fallnamen.
**Schweregrad:** HOCH
**Empfehlung:** Nur den Fallnamen als Link-Label verwenden. Metadaten visuell darunter/innerhalb, aber vom Link-Label getrennt (z.B. mit `aria-describedby`).

---

### H5: Plural-Fehler „Falle" statt „Fälle"

**Beobachtung:** Die Fallliste zeigt „2 Falle" statt „2 Fälle". Der Template-Code in `cases/list.html` Zeile 22 hängt bei `case_count != 1` ein „e" an „Fall" → „Falle" (bedeutet „Falle"/„Trap").
**Betroffene Seite:** `/ui/cases`
**Auswirkung:** Grammatikfehler, der die Professionalität untergräbt. „Falle" hat eine komplett andere Bedeutung.
**Schweregrad:** HOCH (weil Bedeutungsverschiebung)
**Empfehlung:** Korrekte Pluralbildung: `{% if view.case_count != 1 %}Fälle{% else %}Fall{% endif %}`

---

## Mittlere Befunde

### M1: Technische Statuswerte auf der Rechtsquellen-Seite

**Beobachtung:** Die Tabelle zeigt `CONSOLIDATED_NON_OFFICIAL` als Autoritätsstufe und `NOT_VERIFIED` als Integritätsstatus.
**Betroffene Seite:** `/ui/legal-sources`
**Auswirkung:** Wie C1 — technische Werte im Frontend.
**Schweregrad:** MITTEL
**Empfehlung:** Mapping auf deutsche, menschenlesbare Werte:
- CONSOLIDATED_NON_OFFICIAL → „Konsolidiert, nicht amtlich"
- NOT_VERIFIED → „Nicht geprüft"

---

### M2: Sehr lange Seitentitel durch Kombination von Fallname + Bereich

**Beobachtung:** Titel wie „Widerspruch gegen Einkommensteuerbescheid 2025 — Rechtsverlauf" werden als H1-Überschrift auf einer Zeile dargestellt. Bei langen Fallnamen und schmalen Viewports entstehen unschöne Umbrüche.
**Betroffene Seiten:** Alle Tab-Seiten
**Auswirkung:** Reduzierte Scanbarkeit. Der Fallname und der aktuelle Bereich konkurrieren um Aufmerksamkeit.
**Schweregrad:** MITTEL
**Empfehlung:** Fallname als kleineren, persistenten Kontext über der Bereichsüberschrift anzeigen. Bereichsname als H1, Fallname als Label/Subhead.

---

### M3: Inkosistente Sprache bei Dokumenttyp

**Beobachtung:** Der Dokumenttyp wird als „sonstiges" (klein geschrieben, generisch) angezeigt.
**Betroffene Seite:** Fall-Detailseite, Dokumentenkarte
**Auswirkung:** Wenig aussagekräftig für den Nutzer.
**Schweregrad:** MITTEL
**Empfehlung:** Dokumenttypen übersetzen und visuell als Badge darstellen (z.B. „Sonstiges Dokument", „Bescheid", „Schreiben")

---

### M4: Leere Evidence-Tab-Seite mit vielen „nicht implementiert"-Hinweisen

**Beobachtung:** Der Evidence-Tab enthält fünf leere Sektionen, jede mit dem Hinweis „in dieser Version noch nicht implementiert". Dies erzeugt den Eindruck eines unfertigen Produkts.
**Betroffene Seite:** `/ui/cases/{id}?tab=evidence`
**Auswirkung:** Vertrauensverlust. Besser: Nicht implementierte Features nicht anzeigen.
**Schweregrad:** MITTEL
**Empfehlung:** Entweder den Tab ausblenden, bis Features implementiert sind, oder eine einzelne, klare Platzhalter-Nachricht zeigen: „Die Evidence-Pack-Funktion wird in einer kommenden Version verfügbar sein."

---

### M5: Datumsfelder mit benutzerdefinierten Spinbuttons statt nativem date-Input

**Beobachtung:** Im Verlauf-Tab werden Datumsfelder mit `role="spinbutton"` für Tag/Monat/Jahr dargestellt, statt des nativen `<input type="date">`. Dies ist ein Accessibility-Problem, da native Date-Picker besser von Screenreadern und Tastatur unterstützt werden.
**Betroffene Seite:** `/ui/cases/{id}?tab=timeline`
**Auswirkung:** Eingeschränkte Tastaturbedienung und Screenreader-Kompatibilität.
**Schweregrad:** MITTEL
**Empfehlung:** Nativen `<input type="date">` verwenden oder zumindest korrekte ARIA-Attribute ergänzen.

---

## Niedrige Befunde

### N1: Footer mit Rechtshinweis auf jeder Seite nimmt Platz weg

**Beobachtung:** Der Footer mit dem Text „Lokale Anwendung — keine Cloud, keine Telemetrie. Rechtliche Gültigkeit nicht bewertet. Menschliche Prüfung erforderlich." erscheint auf jeder Seite.
**Betroffene Seiten:** Alle
**Auswirkung:** Der Hinweis ist wichtig, aber die dauerhafte Prominenz auf jeder Seite reduziert den nutzbaren Bildschirmplatz. Besser als einmaliger Hinweis beim ersten Start oder in einem Info-Bereich.
**Schweregrad:** NIEDRIG
**Empfehlung:** Footer kompakter gestalten. Datenschutz-Hinweis („Keine Cloud, keine Telemetrie") im Header-Badge belassen. Rechtlicher Hinweis in einer schmaleren Zeile.

---

### N2: Kein responsiver Breakpoint für sehr schmale Viewports getestet

**Beobachtung:** Die CSS hat nur einen Breakpoint (`@media (max-width: 600px)`) für die Tab-Navigation. Andere Komponenten (Upload-Formular, Tabellen) haben keine mobilen Anpassungen.
**Betroffene Seiten:** Alle
**Auswirkung:** Auf kleinen Bildschirmen (Smartphone) werden Formulare und Tabellen möglicherweise schwer bedienbar.
**Schweregrad:** NIEDRIG
**Empfehlung:** Responsive Anpassungen für Tabellen (horizontales Scrollen), Formulare (volle Breite) und Upload-Bereich.

---

### N3: Back-Links am Seitenende konkurrieren mit Breadcrumbs

**Beobachtung:** Am Ende vieler Seiten gibt es einen „← Zurück"-Link, obwohl Breadcrumbs am Seitenanfang bereits Navigation bieten.
**Betroffene Seiten:** Fall-Detail, Dokument-Workspace, Tab-Seiten
**Auswirkung:** Redundanz. Kann verwirren, da Breadcrumbs und Back-Links unterschiedliche Ziele haben können.
**Schweregrad:** NIEDRIG
**Empfehlung:** Back-Links entfernen, wenn Breadcrumbs vorhanden sind. Oder Back-Link im Breadcrumb integrieren.

---

## Übersichtstabelle

| ID | Titel | Schweregrad | Seite | Typ |
|----|-------|-------------|-------|-----|
| C1 | Technische Enum-Werte im Frontend | KRITISCH | Dokument-Workspace | Inhalt |
| C2 | Status „open" in Englisch | KRITISCH | Fallliste, Detail | Inhalt |
| H1 | Keine Hauptnavigation | HOCH | Alle | Navigation |
| H2 | Upload-Fläche dominiert Seite | HOCH | Fall-Detail | Layout |
| H3 | role="alert" falsch verwendet | HOCH | Dokument-Workspace | A11y |
| H4 | Zu lange Link-Texte | HOCH | Fallliste | A11y/Inhalt |
| H5 | „Falle" statt „Fälle" | HOCH | Fallliste | Inhalt |
| M1 | Technische Werte Rechtsquellen | MITTEL | Rechtsquellen | Inhalt |
| M2 | Lange Seitentitel | MITTEL | Alle Tabs | Layout |
| M3 | Dokumenttyp nicht übersetzt | MITTEL | Fall-Detail | Inhalt |
| M4 | Viele „nicht implementiert"-Hinweise | MITTEL | Evidence-Tab | Inhalt |
| M5 | Benutzerdefinierte Datumsfelder | MITTEL | Verlauf-Tab | A11y |
| N1 | Footer zu prominent | NIEDRIG | Alle | Layout |
| N2 | Fehlende responsive Anpassungen | NIEDRIG | Alle | Layout |
| N3 | Redundante Back-Links | NIEDRIG | Mehrere | Navigation |

---

## Zusammenfassung der Schweregrade

- **Kritisch:** 2 (technische Codes in UI, englische Status)
- **Hoch:** 5 (Navigation, Layout-Balance, A11y, Inhalt)
- **Mittel:** 5 (Konsistenz, Übersetzung, Platzhalter)
- **Niedrig:** 3 (Footer, Responsive, Redundanz)

---

## Was gut funktioniert

- Semantisches HTML mit Landmarks (`<header>`, `<main>`, `<footer>`, `<nav>`)
- Skip-Link vorhanden und funktional
- Fokus-Indikatoren (`:focus-visible`) korrekt implementiert
- Breadcrumbs durchgängig vorhanden
- Tab-Navigation mit `aria-current` für aktiven Tab
- CSRF-Schutz korrekt (blockiert unautorisierte POST-Requests)
- Keine JavaScript-Fehler im Konsolen-Log
- Konsistente Fehlerseiten mit menschenlesbaren Nachrichten
- Flash-Banner für Erfolgsmeldungen mit `role="status"`
- Keine externen Abhängigkeiten (CDN, Fonts) — gut für Datenschutz

---

## Positiv hervorzuheben

1. **Lokale Verarbeitung klar kommuniziert:** „Nur lokal"-Badge und Footer-Disclaimer schaffen Vertrauen
2. **Rechtliche Zurückhaltung:** „Rechtliche Gültigkeit nicht bewertet" wird konsequent wiederholt
3. **Progressive Enhancement:** Kernfunktionen ohne JavaScript nutzbar
4. **Fehlertoleranz:** Sanfte Fehlerbehandlung ohne Stack-Traces
5. **CSRF-Schutz:** Auch bei Formular-Replay korrekt
