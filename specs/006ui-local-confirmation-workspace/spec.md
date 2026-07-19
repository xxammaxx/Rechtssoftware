# Spec — M6-UI Lokaler Confirmation-Workspace

## Feature
M6-UI — Lokale Browseroberflaeche fuer den M6-A Confirmation-Workflow

## Overview

M6-A stellt stabile JSON-API-Endpunkte fuer Reference-Event-Bestaetigung und Kalenderarithmetik bereit. M6-UI macht diese Faehigkeiten ueber eine vollstaendig lokale, sichere und barrierefreie Browseroberflaeche nutzbar — ohne Kommandozeile, ohne manuelle API-Aufrufe.

Der UI-Slice implementiert ausschliesslich die Darstellung und Bedienung der bereits vorhandenen M6-A-Domain-Semantik. Keine neue fachliche Entscheidung. Keine Rechtsregellogik. Keine Fristberechnung.

**Kernprinzip:**
```
UI displays state.
UI does not invent state.
UI requests explicit user action.
UI does not infer legal validity.
```

## Product Invariants (inherited from M6-A)

| ID | Invariant |
|----|-----------|
| INV-M6A-01 | Ein unbestaetigtes Bezugsdatum DARF keine Berechnung ausloesen. |
| INV-M6A-02 | Ein automatisch erkannter Datumskandidat DARF nicht automatisch als rechtlich massgeblich gelten. |
| INV-M6A-03 | Die Bestaetigung MUSS eine explizite Nutzeraktion sein. |
| INV-M6A-11 | Jede Ausgabe MUSS `human_review_required=true` enthalten. |
| INV-M6A-12 | Jede Ausgabe MUSS `legal_validity_assessed=false` enthalten. |
| INV-M6A-18 | Ergebnisse duerfen nicht als verbindliche Fristen bezeichnet werden. |
| INV-M6A-19 | Das System ist ausschliesslich fuer die Nutzung durch eine einzelne natuerliche Person ausgelegt. |

## UI-Specific Invariants

| ID | Invariant |
|----|-----------|
| INV-UI-01 | Alle UI-Ressourcen, Skripte, Styles, Fonts und Tests sind lokal verfuegbar. Keine externen Runtime-Requests. |
| INV-UI-02 | Keine Bestaetigung, Berechnung oder Folgemassnahme ohne bewusste Nutzeraktion. |
| INV-UI-03 | Die UI bewertet keine rechtliche Gueltigkeit. |
| INV-UI-04 | Jede zustandsveraendernde Aktion revalidiert Fall, Dokument, Kandidat, Confirmation und aktuellen Status serverseitig. |
| INV-UI-05 | Jeder zustandsveraendernde Browser-Request benoetigt gueltigen CSRF- und Origin-Nachweis. |
| INV-UI-06 | Wiederholte oder parallele Form-Submits erzeugen keine doppelten fachlichen Zustaende. |
| INV-UI-07 | UI-Routen greifen ausschliesslich ueber Application-Vertraege auf Fachfunktionen zu. Kein direkter Repository-Zugriff. |
| INV-UI-08 | Alle angezeigten fachlichen Zustaende stammen aus Application- oder Domain-Daten. Keine erfundenen Zustaende. |
| INV-UI-09 | Keine sensitiven Inhalte in Logs, URLs oder technischen Fehlerseiten. |
| INV-UI-10 | Systemtexte unterscheiden klar zwischen erkanntem Dokumentinhalt und rechtlicher Bewertung. |
| INV-UI-11 | Der vollstaendige Kernablauf ist per Tastatur und Screenreader bedienbar. |
| INV-UI-12 | Alle Kernaktionen funktionieren ohne JavaScript. |
| INV-UI-13 | Jede HTML-Antwort erhaelt den definierten Security-Header-Satz. |
| INV-UI-14 | Keine CDN-, Analytics-, Font-, Script- oder Stylesheet-Abhaengigkeit. |
| INV-UI-15 | Eine Rechenvorschau ist nur mit einer aktuell gueltigen Bestaetigung moeglich. |

---

## User Stories

### US1 — Fall- und Dokumentnavigation (P1)
Als Nutzer moechte ich vorhandene Faelle und deren Dokumente in der Browseroberflaeche sehen und auswaehlen.

**Acceptance Criteria:**
- Liste aller Faelle wird auf Startseite angezeigt
- Keine Faelle: Hinweis "Keine Faelle vorhanden"
- Fallauswahl fuehrt zur Detailansicht mit Dokumentliste
- Keine Dokumente im Fall: Hinweis "Keine Dokumente im Fall"
- Dokumentauswahl fuehrt zur Zeitangaben-Ansicht

### US2 — Zeitangaben-Kandidaten anzeigen (P1)
Als Nutzer moechte ich die aus dem Dokumenttext erkannten Datums- und Zeitraumhinweise sehen.

**Acceptance Criteria:**
- Deadline Candidates werden mit Typ, Textausschnitt und Position angezeigt
- RELATIVE_PERIOD-Kandidaten sind als solche gekennzeichnet ("relative Zeitangabe")
- Human-Review-Hinweis ist sichtbar
- Keine Kandidaten: Hinweis "Keine Datums- oder Zeitraumhinweise erkannt"
- Dokument ohne Text: Hinweis "Kein Text extrahierbar"

### US3 — Bezugsereignisse pruefen (P1)
Als Nutzer moechte ich zu einer relativen Zeitangabe moegliche Bezugsereignisse sehen.

**Acceptance Criteria:**
- Reference-Event-Kandidaten werden mit Eventtyp, vorgeschlagenem Datum, Evidence-Text dargestellt
- Jeder Kandidat ist eindeutig als UNCONFIRMED markiert
- Kein Bezugsereignis ist vorausgewaehlt
- Mehrere Bezugsereignisse werden mit entsprechender Warnung angezeigt

### US4 — Bezugsdatum bestaetigen (P1)
Als Nutzer moechte ich ein Bezugsdatum explizit bestaetigen, ablehnen oder manuell eingeben.

**Acceptance Criteria:**
- Bestaetigen-Button fuer auto-detected candidates
- Ablehnen-Button fuer Kandidaten
- Manuelles Datumseingabefeld mit Eventtyp-Auswahl
- Nach Bestaetigung: Statuswechsel auf CONFIRMED sichtbar
- Nach Ablehnung: Statuswechsel auf REJECTED sichtbar
- Manuelle Eingabe: Warnung bei fehlender Evidenzangabe
- Keine automatische Bestaetigung bei Seitenaufruf

### US5 — Rechenvorschau (P1)
Als Nutzer moechte ich eine unverbindliche Rechenvorschau auf Basis des bestaetigten Bezugsdatums sehen.

**Acceptance Criteria:**
- Vorschau-Button nur aktiv, wenn Status = CONFIRMED
- Button deaktiviert bei UNCONFIRMED, REJECTED, REVOKED
- Ergebnis zeigt: bestaetigtes Datum, Dauer, Operation, berechnetes Datum
- Rechenweg als Schrittliste sichtbar
- Pflichtwarnungen: CALCULATION_PREVIEW_ONLY, NO_WEEKEND/HOLIDAY_ADJUSTMENT, HUMAN_REVIEW_REQUIRED
- Ueberschrift: "Unverbindliche Rechenvorschau" (nicht "Fristende")
- `human_review_required=true` sichtbar
- `legal_validity_assessed=false` sichtbar

### US6 — Bestaetigungshistorie (P2)
Als Nutzer moechte ich die vollstaendige Bestaetigungshistorie eines Kandidaten einsehen.

**Acceptance Criteria:**
- Tabelle mit allen Bestaetigungen (CONFIRMED, SUPERSEDED, REVOKED, REJECTED)
- Zeitstempel, Status, bestaetigtes Datum, Methode sichtbar
- Supersession-Chain erkennbar
- Aktueller Status deutlich markiert

### US7 — Bestaetigung korrigieren oder widerrufen (P2)
Als Nutzer moechte ich eine Bestaetigung aendern oder widerrufen koennen.

**Acceptance Criteria:**
- Widerrufen-Button mit Bestaetigungsdialog
- Nach Widerruf: Status REVOKED, keine Berechnung moeglich
- Korrektur erzeugt neuen CONFIRMED-Eintrag, alter → SUPERSEDED
- Beide Eintraege in History sichtbar

---

## Action-Semantik-Tabelle

Die UI muss sauber zwischen UI-Aktion, Application Command und Domain SourceType trennen. Es werden ausschliesslich vorhandene Domain-Enum-Werte verwendet.

| UI-Aktion | Application Command | Source Type | Confirmation Method | Resultierender Status |
|-----------|-------------------|-------------|---------------------|----------------------|
| Bestaetigen | ReferenceEventService.confirm() | auto_detected | auto_suggested | confirmed |
| Manuell setzen | ReferenceEventService.confirm() | user_manual | manually_entered | confirmed |
| Korrigieren | ReferenceEventService.confirm() | user_corrected | corrected | confirmed |
| Ablehnen | ReferenceEventService.reject() | auto_detected | auto_suggested | rejected |
| Widerrufen | ReferenceEventService.revoke() | (erbt von widerrufenem Eintrag) | (erbt) | revoked |

**Wichtig:** Der Wert `action="manual"` existiert nicht in den Domain-Enums. Manuelle Eingabe ist eine UI-Interaktion, die fachlich ueber `ReferenceEventService.confirm()` mit `source_type=SourceType.USER_MANUAL` und `confirmation_method=ConfirmationMethod.MANUALLY_ENTERED` abgebildet wird.

---

## UI-Zustandsmodell

| State | Beschreibung | Sichtbarer Inhalt | Erlaubte Aktionen | Blockierte Aktionen |
|-------|-------------|------------------|-------------------|-------------------|
| `IDLE` | Startseite | Fallliste | Fall auswaehlen | — |
| `CASE_SELECTED` | Fall gewaehlt | Falldetails, Dokumentliste | Dokument auswaehlen, zurueck | — |
| `DOCUMENT_SELECTED` | Dokument gewaehlt | Dokumentinfo, Textvorschau | Kandidaten laden, zurueck | Bezugsereignisse (ohne Kandidaten) |
| `CANDIDATES_AVAILABLE` | Kandidaten geladen | Kandidatenliste, Warnungen | Relativen Kandidaten auswaehlen | Berechnung (kein Kandidat gewaehlt) |
| `RELATIVE_SELECTED` | Kandidat gewaehlt | Kandidatendetails, Dauer | Bezugsereignisse laden | Berechnung (keine Events) |
| `REFERENCE_EVENTS_AVAILABLE` | Events geladen | Eventliste, Status UNCONFIRMED | Bestaetigen, Ablehnen, Manuell | Berechnung (unbestaetigt) |
| `CONFIRMED` | Bezugsdatum bestaetigt | Status, bestaetigtes Datum, Methode | Rechenvorschau, Korrigieren, Widerrufen | — |
| `REJECTED` | Bezugsereignis abgelehnt | Status, Warnung | Anderes Event waehlen | Berechnung, Bestaetigung |
| `REVOKED` | Bestaetigung widerrufen | Status, Warnung, vorherige Werte | — | Berechnung, Bestaetigung |
| `SUPERSEDED` | Ueberholt durch neue Bestaetigung | Status, Verweis auf aktuelle | Bestaetigungshistorie | Berechnung, Bestaetigung |
| `PREVIEW_AVAILABLE` | Vorschau geladen | Rechenvorschau, Rechenweg, Warnungen | Historie, Korrigieren, Widerrufen | — |
| `ERROR` | Fehler | Fehlermeldung, Rueckkehrlink | Zurueck, Neu laden | Abhaengig vom Kontext |

**Anmerkung:** Loading-States (z. B. "Ladeindikator") werden bei vollstaendig servergerenderten Formularen nicht als separate UI-Zustaende modelliert. Submit-Zustaende werden als progressive enhancement betrachtet. Der Browser-indigene Ladezustand reicht fuer PRG-basierte Server-Rendering-Flows aus.

---

## Funktionale Anforderungen

| ID | Anforderung |
|----|-------------|
| FR-UI-001 | Die UI MUSS eine Fallliste anzeigen (via Application Service). |
| FR-UI-002 | Die UI MUSS Falldetails mit Dokumentliste anzeigen. |
| FR-UI-003 | Die UI MUSS Zeitangaben-Kandidaten anzeigen. |
| FR-UI-004 | Die UI MUSS RELATIVE_PERIOD-Kandidaten identifizieren und Bezugsereignisse laden. |
| FR-UI-005 | Die UI MUSS Bestaetigung, Ablehnung und manuelle Eingabe unterstuetzen. |
| FR-UI-006 | Die UI MUSS den Bestaetigungsstatus nach jeder Aktion aktualisieren. |
| FR-UI-007 | Die UI MUSS eine Rechenvorschau anfordern koennen. |
| FR-UI-008 | Die UI MUSS den vollstaendigen Rechenweg darstellen. |
| FR-UI-009 | Die UI MUSS Pflichtwarnungen sichtbar auf der Ergebnisseite anzeigen. |
| FR-UI-010 | Die UI MUSS die Bestaetigungshistorie abrufen und darstellen. |
| FR-UI-011 | Die UI MUSS Widerruf mit Bestaetigungsdialog unterstuetzen. |
| FR-UI-012 | Die UI MUSS Berechnungsaktionen bei UNCONFIRMED/REJECTED/REVOKED blockieren. |
| FR-UI-013 | Die UI MUSS alle API-Fehler (400, 403, 404, 409, 422, 500) benutzerfreundlich anzeigen. |
| FR-UI-014 | Die UI DARF keine sensitiven IDs in Fehlermeldungen anzeigen. |
| FR-UI-015 | Die UI MUSS das CSP-konforme Security-Header-Set ausliefern (via HTTP-Header, nicht Meta-Tag). |
| FR-UI-016 | Die UI MUSS Cache-Control: no-store fuer fallbezogene Seiten setzen. |
| FR-UI-017 | Die UI MUSS Referrer-Policy: no-referrer setzen. |
| FR-UI-018 | Die UI MUSS die Host-Header-Validierung durchfuehren (konfigurierbar aus Settings). |
| FR-UI-019 | Die UI MUSS CSRF-Schutz fuer alle zustandsveraendernden POST-Requests bereitstellen. |
| FR-UI-020 | Die UI MUSS Idempotenz-Schluessel fuer alle zustandsveraendernden Aktionen verarbeiten. |

---

## Preview-Vertrag (Server-seitige Revalidierung)

Der serverseitige Preview-Flow muss folgende Schritte durchlaufen:

1. Confirmation laden (via `confirmation_id`)
2. Zugehoerigkeit zu Fall, Dokument und Kandidat pruefen (Cross-Case/Cross-Document-Schutz)
3. Aktuellen Confirmation-Status pruefen (nur CONFIRMED ist zulaessig)
4. Ausgewaehlten Kandidaten erneut aus kanonischer Quelle laden
5. Dauer (amount, unit) aus der kanonischen Candidate-Quelle bestimmen — NICHT aus Hidden Fields uebernehmen
6. Erst danach den Preview-Use-Case ausfuehren

Manipulierte IDs oder inkonsistente Kombinationen fuehren zu einem definierten 4xx-Status oder einer generischen Fehlerseite.

---

## Negativpfade

| ID | Szenario | Erwartetes Verhalten |
|----|----------|---------------------|
| NP-01 | Kein Fall vorhanden | Hinweis "Keine Faelle vorhanden." |
| NP-02 | Kein Dokument im Fall | Hinweis "Keine Dokumente im Fall." |
| NP-03 | Dokument ohne extrahierten Text | Hinweis "Kein Text aus Dokument extrahierbar." |
| NP-04 | Keine Datums-/Zeitraumhinweise | Hinweis "Keine Datums- oder Zeitraumhinweise erkannt." |
| NP-05 | Kein RELATIVE_PERIOD-Kandidat | Alle Kandidaten sind EXPLICIT_DATE oder QUALITATIVE — Hinweis |
| NP-06 | Kein Bezugsereignis | Hinweis "Keine Bezugsereignisse gefunden." |
| NP-07 | Ungueltige manuelle Datumseingabe | Validierungsfehler mit Hinweis auf Format (YYYY-MM-DD) |
| NP-08 | Datum ausserhalb 1900–2099 | Validierungsfehler |
| NP-09 | Berechnung ohne Bestaetigung | Button deaktiviert, Warnung |
| NP-10 | Berechnung nach Widerruf | Button deaktiviert, Statusanzeige |
| NP-11 | Doppelte Formularuebermittlung | Server-seitige Idempotenz verhindert Doppelverarbeitung; client-seitige Button-Deaktivierung als UX-Ergaenzung |
| NP-12 | CSRF-Token fehlt/ungueltig | 403 mit generischer Fehlerseite |
| NP-13 | Cross-Origin POST | Origin-Pruefung schlaegt fehl → 403 |
| NP-14 | Falscher Host-Header | 400 mit generischer Fehlermeldung |
| NP-15 | API 404 | "Nicht gefunden" mit Kontext |
| NP-16 | API 409 (Replay/Konflikt) | Hinweis "Bereits verarbeitet oder Statuskonflikt" |
| NP-17 | API 500 | Generische Fehlermeldung, kein Stacktrace |

---

## CSRF-Schutz (Spezifikation)

### Mechanismus
- Kryptografisch zufaelliges CSRF-Token pro Request/Context
- Token wird als Hidden-Form-Field uebermittelt
- Serverseitiger Vergleich in konstanter Zeit
- Token-Rotation nach Verwendung oder nach definierter Lebensdauer
- Keine Tokens in URLs oder Logs

### Zusaetzliche Pruefungen
- Origin-Header-Prüfung auf allen POST-Routen
- Referer-Fallback nur wenn Origin nicht vorhanden
- Ablehnung bei fehlendem, ungueltigem oder wiederverwendetem Token

### Testfaelle (verpflichtend)
- Gueltiges Token → Erfolg
- Fehlendes Token → 403
- Falsches Token → 403
- Token aus anderem Kontext → 403
- Cross-Origin-POST → 403
- Fehlender Origin und ungueltiger Referer → 403
- Token-Replay gemaess Policy → 403 oder 409

---

## Host-Header-Validierung

- Erlaubte Hosts werden aus der Settings-Konfiguration abgeleitet (nicht hartcodiert)
- Konfigurierbarer Port wird beruecksichtigt
- Unterstuetzt: `127.0.0.1`, `localhost`, ggf. `[::1]`
- Exakte Portpruefung (keine Wildcards)
- Kein Vertrauen in Forwarded-Headers (keine Proxy-Unterstuetzung ohne separate Entscheidung)
- Unterscheidung: Bind-Adresse ≠ erlaubter Host-Header ≠ Browser-Origin ≠ CSRF-Origin
- Host-Validierung ersetzt KEINEN CSRF-Schutz (getrennte Sicherheitsschichten)

---

## Erfolgskriterien

| ID | Kriterium |
|----|-----------|
| SC-01 | Der vollstaendige Confirmation-Workflow ist ohne Kommandozeile im Browser durchfuehrbar. |
| SC-02 | Alle 379+ bestehenden Tests bestehen unveraendert. |
| SC-03 | Keine externen Netzwerkrequests waehrend des Betriebs. |
| SC-04 | Alle Pflichtwarnungen sind auf der Ergebnisseite sichtbar (nicht versteckt). |
| SC-05 | Der Workflow ist vollstaendig per Tastatur bedienbar. |
| SC-06 | Der Workflow funktioniert ohne JavaScript. |
| SC-07 | Keine XSS ueber Dokumenttext oder Nutzereingaben. |
| SC-08 | Testabdeckung ≥ 90%. |
| SC-09 | Ruff: 0 Fehler. Mypy: 0 Fehler. |
| SC-10 | Accessibility: axe-core ohne Critical- oder Serious-Verstoesse. |

---

## Bewusst nicht unterstuetzt (M6-UI)

- Rechtsverbindliche Fristberechnung
- Automatische Bestaetigung ohne Nutzeraktion
- Multi-User oder Authentifizierung
- Export/Import von Berechnungsergebnissen
- Rechtliche Pruefung von Bezugsereignissen
- Beruecksichtigung von Feiertagen
- Beruecksichtigung von Wochenenden
- Rechtsregeln (Zustellfiktion, Bekanntgabefiktion)
- Mobile-first Layout (Desktop-first)
- Monate/Jahre als Zeiteinheit
- Server-seitige Sessions (token-basierter CSRF-Kontext)
- Automatische Kommunikation mit Behoerden oder Dritten
- Cloud-Speicher oder externe Backups
- PDF-Generierung von Berechnungsergebnissen

---

## Abgrenzung zu M6-B

M6-UI implementiert ausschliesslich die M6-A-Semantik:
- Reine Kalenderarithmetik (Tage/Wochen)
- Keine Feiertags- oder Wochenendverschiebung
- Keine Rechtsregeln (Zustellfiktion, Bekanntgabefiktion)
- Keine Fristberechnung im Rechtssinne
- Alle adjustments sind statisch auf "Nicht angewendet"

Die UI stellt adjustments als statische Faktentabelle dar. Dies aendert sich zwischen M6-A und M6-B nicht — nur die Werte in der Tabelle aendern sich.
