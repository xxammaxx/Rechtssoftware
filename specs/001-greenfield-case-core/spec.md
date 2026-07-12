# Spec — M1 Greenfield Foundation and Case Core

## Feature
M1 – Greenfield Foundation and Case Core

## Status
Draft

## User Stories

### User Story 1 – Fall anlegen (P1)
Als Nutzer möchte ich einen neuen lokalen Fall mit einem Titel anlegen, damit
spätere Dokumente und Bearbeitungsschritte einem eindeutigen Fall zugeordnet
werden können.

**Akzeptanzkriterien:**
- Ein Fall kann mit einem Titel über die API angelegt werden
- Der Titel wird getrimmt
- Ein leerer Titel wird abgelehnt
- Ein Titel über 200 Zeichen wird abgelehnt
- Der Fall erhält eine serverseitig generierte UUID als ID
- Der Fall erhält den Status "open"
- Zeitstempel sind timezone-aware UTC
- Antwort ist 201 Created

### User Story 2 – Fälle auflisten (P1)
Als Nutzer möchte ich alle lokal gespeicherten Fälle sehen, damit ich einen
bestehenden Fall auswählen kann.

**Akzeptanzkriterien:**
- Alle Fälle werden zurückgegeben
- Die Liste enthält eine Count-Angabe
- Die Sortierung ist deterministisch
- Eine leere Liste wird korrekt dargestellt

### User Story 3 – Falldetail abrufen (P1)
Als Nutzer möchte ich einen bestimmten Fall anhand seiner internen ID abrufen,
damit ich dessen Grunddaten prüfen kann.

**Akzeptanzkriterien:**
- Ein Fall kann über seine UUID abgerufen werden
- Eine unbekannte ID liefert 404 mit stabilem Fehlerformat
- Ein ungültiges UUID-Format wird angemessen behandelt

## Funktionale Anforderungen

Siehe `specs/001-greenfield-case-core/spec.md` Abschnitt "Functional Requirements".

## Nicht-Funktionale Anforderungen

- Backend bindet ausschließlich an 127.0.0.1
- Keine externen Laufzeitrequests
- Datenbank liegt in konfigurierbarem lokalen Verzeichnis
- Keine Falldaten in Logs
- Parametrisierte SQL-Abfragen
- Coverage ≥ 90%

## Abgrenzung

Dieses Feature umfasst **nicht**:
- Dokumentimport oder -verarbeitung
- OCR, PDF-Analyse
- Fristberechnung
- Rechtsbewertung
- Frontend
- Authentifizierung
- Mehrbenutzerfähigkeit
