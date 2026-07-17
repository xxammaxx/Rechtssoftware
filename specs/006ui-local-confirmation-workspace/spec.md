# Spec — M6-UI Lokaler Confirmation-Gate-Workspace

## Feature
M6-UI — Lokale Browseroberfläche für den M6-A Confirmation-Gate-Workflow

## Overview

M6-A stellt stabile JSON-API-Endpunkte für Reference-Event-Bestätigung und Kalenderarithmetik bereit. M6-UI macht diese Fähigkeiten über eine vollständig lokale, sichere und barrierearme Browseroberfläche nutzbar — ohne Kommandozeile, ohne manuelle API-Aufrufe.

Der UI-Slice implementiert ausschließlich die Darstellung und Bedienung der bereits vorhandenen M6-A-Semantik. Keine neue fachliche Entscheidung. Keine Rechtsregellogik.

**Kernprinzip:**
```
UI displays state.
UI does not invent state.
UI requests explicit user action.
UI does not infer legal validity.
```

## Architecture Decision

**Variant A — Server-Rendered HTML mit Jinja2** (siehe ADR-003)

FastAPI + Jinja2Templates + StaticFiles + HTML-Formulare + progressive JS-Erweiterung. Neue `/ui/`-Routen rufen bestehende Application Services auf und rendern HTML. Bestehende `/api/v1/`-Routen bleiben unverändert.

## Product Invariants (inherited from M6-A)

| ID | Invariant |
|----|-----------|
| INV-M6A-01 | Ein unbestätigtes Bezugsdatum DARF keine Berechnung auslösen. |
| INV-M6A-02 | Ein automatisch erkannter Datumskandidat DARF nicht automatisch als rechtlich maßgeblich gelten. |
| INV-M6A-03 | Die Bestätigung MUSS eine explizite Nutzeraktion sein. |
| INV-M6A-11 | Jede Ausgabe MUSS `human_review_required=true` enthalten. |
| INV-M6A-12 | Jede Ausgabe MUSS `legal_validity_assessed=false` enthalten. |
| INV-M6A-18 | Ergebnisse dürfen nicht als verbindliche Fristen bezeichnet werden. |
| INV-M6A-19 | Das System ist ausschließlich für die Nutzung durch eine einzelne natürliche Person ausgelegt. |

## UI-Specific Invariants

| ID | Invariant |
|----|-----------|
| INV-UI-01 | Die UI DARF keine Berechnung ohne bestätigtes Bezugsdatum ermöglichen. |
| INV-UI-02 | Die UI DARF keine rechtliche Gültigkeit durch Farben oder Symbole suggerieren. |
| INV-UI-03 | Pflichtwarnungen MÜSSEN immer sichtbar sein (nicht in Collapsed Sections, nicht nur Tooltips, nicht nur Farbe). |
| INV-UI-04 | Die UI DARF KEINE externen Ressourcen laden (keine CDN, keine externen Fonts, keine externen Skripte). |
| INV-UI-05 | Alle dynamischen Inhalte MÜSSEN XSS-sicher gerendert werden (Autoescaping, kein innerHTML). |
| INV-UI-06 | Bestätigung MUSS eine bewusste Button-Aktion sein — kein Autoconfirm, kein Enter ohne Fokus. |
| INV-UI-07 | Die UI DARF `human_review_required` und `legal_validity_assessed=false` auf jeder Ergebnisseite anzeigen. |
| INV-UI-08 | Die UI DARF KEINE Daten in Browser-Storage (localStorage, sessionStorage, IndexedDB) persistent speichern. |
| INV-UI-09 | Der Workflow MUSS vollständig per Tastatur bedienbar sein. |

---

## User Stories

### US1 — Fall- und Dokumentnavigation (P1)
Als Nutzer möchte ich vorhandene Fälle und deren Dokumente in der Browseroberfläche sehen und auswählen.

**Acceptance Criteria:**
- Liste aller Fälle wird auf Startseite angezeigt
- Keine Fälle: Hinweis "Keine Fälle vorhanden"
- Fallauswahl führt zur Detailansicht mit Dokumentliste
- Keine Dokumente im Fall: Hinweis "Keine Dokumente im Fall"
- Dokumentauswahl führt zur Deadline-Candidate-Ansicht

### US2 — Fristkandidaten anzeigen (P1)
Als Nutzer möchte ich die aus dem Dokumenttext extrahierten Fristkandidaten sehen.

**Acceptance Criteria:**
- Deadline Candidates werden mit Typ, Textausschnitt und Offset angezeigt
- RELATIVE_PERIOD-Kandidaten sind als solche gekennzeichnet
- Human-Review-Hinweis ist sichtbar
- Keine Kandidaten: Hinweis "Keine Fristkandidaten erkannt"
- Dokument ohne Text: Hinweis "Kein Text extrahierbar"

### US3 — Reference Events prüfen (P1)
Als Nutzer möchte ich zu einem RELATIVE_PERIOD-Kandidaten mögliche Bezugsereignisse sehen.

**Acceptance Criteria:**
- Reference-Event-Kandidaten werden mit Eventtyp, vorgeschlagenem Datum, Evidence-Text dargestellt
- Jeder Kandidat ist eindeutig als UNCONFIRMED markiert
- Kein Bezugsereignis ist vorausgewählt
- Mehrere Bezugsereignisse werden mit MULTIPLE_REFERENCE_EVENTS-Warnung angezeigt

### US4 — Bezugsdatum bestätigen (P1)
Als Nutzer möchte ich ein Bezugsdatum explizit bestätigen, ablehnen oder manuell eingeben.

**Acceptance Criteria:**
- Bestätigen-Button für auto-detected candidates
- Ablehnen-Button für Kandidaten
- Manuelles Datumseingabefeld mit Eventtyp-Auswahl
- Nach Bestätigung: Statuswechsel auf CONFIRMED sichtbar
- Nach Ablehnung: Statuswechsel auf REJECTED sichtbar
- Manuelle Eingabe: MANUAL_ENTRY_WITHOUT_EVIDENCE-Warnung wenn ohne evidence_note
- Keine automatische Bestätigung bei Seitenaufruf

### US5 — Berechnungsvorschau (P1)
Als Nutzer möchte ich eine unverbindliche Berechnungsvorschau auf Basis des bestätigten Bezugsdatums sehen.

**Acceptance Criteria:**
- Berechnungsvorschau-Button nur aktiv, wenn Status = CONFIRMED
- Button deaktiviert bei UNCONFIRMED, REJECTED, REVOKED
- Ergebnis zeigt: bestätigtes Datum, Dauer, Operation, berechnetes Datum
- Rechenweg als Schrittliste sichtbar
- Pflichtwarnungen: CALCULATION_PREVIEW_ONLY, NO_WEEKEND/HOLIDAY_ADJUSTMENT, HUMAN_REVIEW_REQUIRED
- Titel: "Unverbindliche Berechnungsvorschau" (nicht "Fristende")
- `human_review_required=true` sichtbar
- `legal_validity_assessed=false` sichtbar

### US6 — Bestätigungshistorie (P2)
Als Nutzer möchte ich die vollständige Bestätigungshistorie eines Kandidaten einsehen.

**Acceptance Criteria:**
- Tabelle mit allen Bestätigungen (CONFIRMED, SUPERSEDED, REVOKED, REJECTED)
- Zeitstempel, Status, bestätigtes Datum, Methode sichtbar
- Supersession-Chain erkennbar
- Aktueller Status deutlich markiert

### US7 — Bestätigung korrigieren oder widerrufen (P2)
Als Nutzer möchte ich eine Bestätigung ändern oder widerrufen können.

**Acceptance Criteria:**
- Widerrufen-Button mit Bestätigungsdialog
- Nach Widerruf: Status REVOKED, keine Berechnung möglich
- Korrektur erzeugt neuen CONFIRMED-Eintrag, alter → SUPERSEDED
- Beide Einträge in History sichtbar

---

## UI-State-Modell

| State | Description | Visible Content | Allowed Actions | Prohibited Actions |
|-------|-------------|----------------|-----------------|-------------------|
| `IDLE` | Startseite | Fallliste | Fall auswählen | — |
| `LOADING_CASES` | Fälle werden geladen | Ladeindikator | — | Navigation, Aktionen |
| `CASE_SELECTED` | Fall gewählt | Falldetails, Dokumentliste | Dokument auswählen, zurück | Deadline-Analyse (kein Dokument) |
| `LOADING_DOCUMENTS` | Dokumente werden geladen | Ladeindikator | — | Navigation, Aktionen |
| `DOCUMENT_SELECTED` | Dokument gewählt | Dokumentinfo, Textvorschau | Deadline-Analyse starten, zurück | Reference Events (keine Analyse) |
| `ANALYSING_CANDIDATES` | Analyse läuft | Ladeindikator | — | Alle Aktionen |
| `CANDIDATES_AVAILABLE` | Kandidaten geladen | Kandidatenliste, Warnungen | RELATIVE_PERIOD auswählen | Berechnung (kein Kandidat gewählt) |
| `RELATIVE_CANDIDATE_SELECTED` | Kandidat gewählt | Kandidatendetails, Dauer | Reference Events laden | Berechnung (keine Events) |
| `LOADING_REFERENCE_EVENTS` | Events werden geladen | Ladeindikator | — | Alle Aktionen |
| `REFERENCE_EVENTS_AVAILABLE` | Events geladen | Eventliste, Status UNCONFIRMED | Bestätigen, Ablehnen, Manuell | Berechnung (unbestätigt) |
| `CONFIRMATION_PENDING` | Bestätigung läuft | Ladeindikator | — | Alle Aktionen |
| `CONFIRMED` | Bezugsdatum bestätigt | Status, bestätigtes Datum, Methode | Berechnungsvorschau, Korrigieren, Widerrufen | — |
| `REJECTED` | Bezugsereignis abgelehnt | Status, Warnung | Anderes Event wählen | Berechnung, Bestätigung |
| `REVOKED` | Bestätigung widerrufen | Status, Warnung, vorherige Werte | — | Berechnung, Bestätigung |
| `SUPERSEDED` | Überholt durch neue Bestätigung | Status, Verweis auf aktuelle | Bestätigungshistorie | Berechnung, Bestätigung |
| `CALCULATING_PREVIEW` | Berechnung läuft | Ladeindikator | — | Alle Aktionen |
| `PREVIEW_AVAILABLE` | Vorschau geladen | Berechnungsvorschau, Rechenweg, Warnungen | Historie, Korrigieren, Widerrufen | — |
| `ERROR` | Fehler | Fehlermeldung, Rückkehrlink | Zurück, Neu laden | Abhängig vom Kontext |
| `STALE_STATE` | State veraltet | Warnung, Aktualisieren-Button | Aktualisieren, Neu laden | Alle Mutationen |

---

## Funktionale Anforderungen

| ID | Anforderung |
|----|-------------|
| FR-UI-001 | Die UI MUSS eine Fallliste anzeigen (GET /api/v1/cases). |
| FR-UI-002 | Die UI MUSS Falldetails mit Dokumentliste anzeigen (GET /api/v1/cases/{id}, GET .../documents). |
| FR-UI-003 | Die UI MUSS Fristkandidaten analysieren können (POST .../deadline-candidates). |
| FR-UI-004 | Die UI MUSS RELATIVE_PERIOD-Kandidaten identifizieren und Reference Events laden (GET .../reference-events). |
| FR-UI-005 | Die UI MUSS Bestätigung, Ablehnung und manuelle Eingabe unterstützen (POST .../confirm). |
| FR-UI-006 | Die UI MUSS den Bestätigungsstatus nach jeder Aktion aktualisieren. |
| FR-UI-007 | Die UI MUSS eine Berechnungsvorschau anfordern können (POST .../calculation-preview). |
| FR-UI-008 | Die UI MUSS den vollständigen Rechenweg darstellen. |
| FR-UI-009 | Die UI MUSS Pflichtwarnungen sichtbar auf der Ergebnisseite anzeigen. |
| FR-UI-010 | Die UI MUSS die Bestätigungshistorie abrufen und darstellen (GET .../history). |
| FR-UI-011 | Die UI MUSS Widerruf mit Bestätigungsdialog unterstützen. |
| FR-UI-012 | Die UI MUSS Berechnungsaktionen bei UNCONFIRMED/REJECTED/REVOKED blockieren. |
| FR-UI-013 | Die UI MUSS alle API-Fehler (400, 404, 409, 422, 500) benutzerfreundlich anzeigen. |
| FR-UI-014 | Die UI DARF keine sensitiven IDs in Fehlermeldungen anzeigen. |
| FR-UI-015 | Die UI MUSS das CSP-konforme Security-Header-Set ausliefern. |
| FR-UI-016 | Die UI MUSS Cache-Control: no-store für fallbezogene Seiten setzen. |
| FR-UI-017 | Die UI MUSS Referrer-Policy: no-referrer setzen. |
| FR-UI-018 | Die UI MUSS die Host-Header-Validierung durchführen. |
| FR-UI-019 | Die UI MUSS bei manueller Eingabe MANUAL_ENTRY_WITHOUT_EVIDENCE anzeigen. |

---

## Negativpfade

| ID | Szenario | Erwartetes Verhalten |
|----|----------|---------------------|
| NP-01 | Kein Fall vorhanden | Hinweis "Keine Fälle vorhanden. Laden Sie zuerst ein Dokument hoch." |
| NP-02 | Kein Dokument im Fall | Hinweis "Keine Dokumente im Fall." |
| NP-03 | Dokument ohne extrahierten Text | Hinweis "Kein Text aus Dokument extrahierbar." |
| NP-04 | Keine Deadline Candidates | Hinweis "Keine Fristkandidaten erkannt." |
| NP-05 | Kein RELATIVE_PERIOD-Kandidat | Alle Kandidaten sind EXPLICIT_DATE oder QUALITATIVE — Hinweis |
| NP-06 | Kein Reference Event | Hinweis "Keine Bezugsereignisse gefunden." |
| NP-07 | Ungültige manuelle Datumseingabe | Validierungsfehler mit Hinweis auf Format (YYYY-MM-DD) |
| NP-08 | Datum außerhalb 1900–2099 | Validierungsfehler |
| NP-09 | Berechnung ohne Bestätigung | Button deaktiviert, Warnung |
| NP-10 | Berechnung nach Widerruf | Button deaktiviert, Statusanzeige |
| NP-11 | Doppelte Formularübermittlung | Button nach erstem Klick deaktivieren, Ladeindikator |
| NP-12 | API 400 | Fehleranzeige mit API-Fehlermeldung |
| NP-13 | API 404 | "Nicht gefunden" mit Kontext |
| NP-14 | API 500 | Generische Fehlermeldung, kein Stacktrace |
| NP-15 | Dokument zwischen Analyse und Bestätigung gelöscht | API 404 → Stale-State-Warnung |
| NP-16 | Netzwerkunterbrechung (local) | Verbindungsfehler-Hinweis |
| NP-17 | Parallele Tabs | Aktueller Status wird bei jedem Seitenaufruf frisch vom Server geladen |

---

## Evidence-Darstellung

| Anforderung | Umsetzung |
|-------------|-----------|
| Maximale Ausschnittlänge | 2000 Zeichen (M6-A-Limit) |
| Ellipsis | "..." am Ende bei Kürzung |
| HTML-Escapes | Jinja2 Autoescaping (strukturell) |
| Zeilenumbrüche | `<pre>` oder `white-space: pre-wrap` |
| Hervorhebung | CSS-Klasse, kein innerHTML |
| Offset-Darstellung | Als Metadatum, nicht als Link |
| Keine Volltext-Duplizierung | Nur API-response evidence_text anzeigen |

---

## UX-Sicherheitsanforderungen

### Terminologie
- **Haupttitel Berechnungsseite:** "Unverbindliche Berechnungsvorschau"
- **NIEMALS:** "Fristende", "Endgültige Frist", "Rechtsgültiges Datum"
- **Zulässig:** "Rechnerisches Kandidatendatum", "Berechnungsvorschau"

### Farben
- Keine Ampellogik (Grün ≠ rechtlich richtig, Rot ≠ rechtlich falsch)
- Neutrale Farbpalette für Status-Badges
- Warnungen: Gelb/Hintergrund mit Text (Standard-Warnmuster)

### Warnungen
- Immer sichtbar, nicht collapsed, nicht nur Tooltip
- CALCULATION_PREVIEW_ONLY oberhalb des berechneten Datums
- HUMAN_REVIEW_REQUIRED im Seitenkopf und neben jedem Ergebnis
- legal_validity_assessed=false als sichtbarer Hinweis

### Manuelle Eingabe
- Transparenzhinweis: "Dieses Datum wurde manuell eingegeben."
- MANUAL_ENTRY_WITHOUT_EVIDENCE-Warnung prominent

### Bestätigung
- Kein Autoconfirm
- Kein Enter ohne sichtbaren Fokus auf Bestätigungsbutton
- Keine vorausgewählten Radiobuttons
- Button-Text: "Bezugsdatum bestätigen" (nicht "OK")

---

## Accessibility-Kriterien (WCAG 2.1 AA)

- Tastaturbedienung aller Workflow-Schritte
- Sichtbare Fokusindikatoren (≥2px, Kontrast ≥3:1)
- Label-Elemente für alle Formularfelder
- Fieldset/Legend für Radiogruppen
- aria-live="polite" für Statusänderungen
- Fehlerzusammenfassung am Seitenanfang
- Keine reine Farbkommunikation
- Semantische Überschriftenhierarchie (h1→h2→h3)
- Aussagekräftige Button-Texte
- prefers-reduced-motion Unterstützung
- Kontrastverhältnis ≥4.5:1 (Normaltext)

---

## Erfolgskriterien

| ID | Kriterium |
|----|-----------|
| SC-UI-001 | Der vollständige M6-A-Workflow ist ohne Kommandozeile nutzbar. |
| SC-UI-002 | Kein Code-Path ermöglicht Berechnung ohne bestätigtes Bezugsdatum. |
| SC-UI-003 | Alle Pflichtwarnungen sind auf der Ergebnisseite sichtbar. |
| SC-UI-004 | Keine externen Netzwerk-Requests von UI-Seiten. |
| SC-UI-005 | Strikte CSP ist durchgesetzt (default-src 'self'). |
| SC-UI-006 | XSS aus PDF-Text ist strukturell verhindert (Autoescaping). |
| SC-UI-007 | Tastaturnavigation durch gesamten Workflow möglich. |
| SC-UI-008 | Bestehende 379 Tests bestehen unverändert. |
| SC-UI-009 | Keine neuen Abhängigkeiten außer Jinja2. |
| SC-UI-010 | UI-Terminologie enthält keine "Frist"-Begriffe in Labels/Titeln. |

---

## Bewusst nicht unterstützt

- Keine Rechtsfristberechnung
- Keine Feiertage, keine Wochenendverschiebung
- Keine Zustellungs-/Bekanntgabefiktion
- Keine Monats-/Jahresarithmetik
- Keine Rechtsbewertung
- Keine Handlungsempfehlungen
- Keine Dokumententwürfe
- Keine Authentifizierung / Mehrbenutzer
- Keine Cloud-Dienste / Telemetrie
- Kein Node.js-Buildsystem
- Keine externen Schriftarten oder CDN-Ressourcen
- Keine M6-B Legal-Rule-Profile

---

## Abgrenzung zu M6-B

| Aspekt | M6-UI | M6-B |
|--------|-------|------|
| Darstellung | M6-A-Semantik | Neue Rechtsregellogik |
| Berechnung | DAY/WEEK-Arithmetik | § 187/188/193 BGB, ZPO |
| Warnungen | Bestehende M6-A-Warncodes | Neue regelbezogene Warnungen |
| UI-Elemente | Bestätigung, Vorschau, Historie | Regelprofil-Auswahl, Feiertagskonfiguration |
| adjustments | Alle `false` | Werden teilweise `true` |

---

## Referenzen

- ADR-001: Lokaler modularer Monolith mit FastAPI + SQLite
- ADR-002: Confirmed Reference Events and Calendar Arithmetic (M6-A)
- ADR-003: Server-Rendered HTML UI for Confirmation Workspace (M6-UI)
- M6-A Spec: `specs/006a-reference-events-calendar-arithmetic/spec.md`
- M6-A API Contract: `specs/006a-reference-events-calendar-arithmetic/contracts/api.md`
- Constitution: `.specify/memory/constitution.md`
