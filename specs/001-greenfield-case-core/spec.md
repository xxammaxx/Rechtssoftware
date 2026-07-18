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
- Die Sortierung ist deterministisch: `created_at DESC` (neueste zuerst)
- Eine leere Liste wird korrekt dargestellt

### User Story 3 – Falldetail abrufen (P1)
Als Nutzer möchte ich einen bestimmten Fall anhand seiner internen ID abrufen,
damit ich dessen Grunddaten prüfen kann.

**Akzeptanzkriterien:**
- Ein Fall kann über seine UUID abgerufen werden
- Eine unbekannte ID liefert 404 mit stabilem Fehlerformat
- Ein ungültiges UUID-Format wird mit 422 + VALIDATION_ERROR abgelehnt

## Funktionale Anforderungen

Die funktionalen Anforderungen sind vollständig in den User Stories (Abschnitt oben) mit detaillierten Akzeptanzkriterien spezifiziert.

## Nicht-Funktionale Anforderungen

- Backend bindet ausschließlich an 127.0.0.1
- Keine externen Laufzeitrequests
- Datenbank liegt in konfigurierbarem lokalen Verzeichnis
- Keine Falldaten in Logs (weder Request-Body noch Response-Body)
- Aktives Logging auf INFO-Level: HTTP-Methode, Pfad, Status-Code, Request-Dauer (ohne Falldaten/Payload)
- ERROR-Level-Logging für interne Fehler und Datenbankfehler
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

## Clarifications

### Session 2026-07-18

- Q: Sortierreihenfolge der Fall-Liste → A: created_at DESC (neueste zuerst)
- Q: HTTP-Status-Code bei Datenbankfehlern → A: 500 Internal Server Error
- Q: Zirkulärer Verweis in "Funktionale Anforderungen" → A: Durch Klarstellung ersetzt (User Stories sind die funktionalen Anforderungen)
- Q: Logging-Umfang und -Level → A: HTTP-Request-Logging (Methode, Pfad, Status, Dauer) auf INFO-Level + ERROR-Logging
