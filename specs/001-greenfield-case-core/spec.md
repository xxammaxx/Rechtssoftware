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

## Funktionale Anforderungen (FR)

| ID | Anforderung | Evidence (Code/Test) |
|----|------------|---------------------|
| FR-001 | Health-Endpunkt liefert `{"status":"ok"}` | `app.py:94-96`, `test_cases_api.py:40-45` |
| FR-002 | Fall mit Titel über API anlegen | `routes.py:45-52`, `test_cases_api.py:51-63` |
| FR-003 | Servergenerierte UUID als Case-ID | `domain/case.py:41`, `test_domain_case.py:51-55` |
| FR-004 | Titel wird getrimmt | `domain/case.py:42`, `test_domain_case.py:24-27` |
| FR-005 | Leerer oder Whitespace-Titel wird abgelehnt | `domain/case.py:50-51`, `test_domain_case.py:29-37` |
| FR-006 | Maximale Titellänge 200 Zeichen | `domain/case.py:52-54`, `test_domain_case.py:39-49` |
| FR-007 | Neuer Fall erhält Status "open" | `domain/case.py:43`, `test_domain_case.py:72-76` |
| FR-008 | UTC-timezone-aware Zeitstempel | `domain/case.py:40`, `test_domain_case.py:57-61` |
| FR-009 | Alle Fälle als Liste mit Count abrufbar | `routes.py:55-64`, `test_cases_api.py:85-101` |
| FR-010 | Deterministische Sortierung nach created_at DESC | `sqlite_case_repository.py:75`, `test_sqlite_repository.py:75-86` |
| FR-011 | Falldetail per UUID abrufen | `routes.py:67-76`, `test_cases_api.py:107-118` |
| FR-012 | Unbekannte UUID liefert 404 mit Fehlerobjekt | `routes.py:74-75`, `test_cases_api.py:120-127` |
| FR-013 | Stabiles maschinenlesbares Fehlerformat | `errors.py:7-17`, `test_cases_api.py:126-127` |
| FR-014 | Konfigurierbares Datenverzeichnis (PLN_DATA_DIR) | `config.py:19-20`, manuell geprüft |
| FR-015 | Idempotente Schema-Initialisierung | `database.py:7-13`, `test_sqlite_repository.py:56-58` |
| FR-016 | Backend bindet ausschließlich an 127.0.0.1 | `config.py:21`, manuell geprüft |
| FR-017 | Keine Falldaten in Anwendungslogs | `errors.py` (nur Envelope), Security-Sweep |
| FR-018 | Keine externen Laufzeitrequests | `grep`-Sweep: 0 externe URLs in `src/` |
| FR-019 | Ausschließlich synthetische Testdaten | Präfix "SYNTHETISCH –" in allen Tests |
| FR-020 | Isolierte temporäre Testdatenbanken | `tmp_path`-Fixture in allen Tests |

## Erfolgskriterien (SC)

| ID | Kriterium | Evidence |
|----|----------|----------|
| SC-001 | Lokale Installation ausführbar | `python -m private_legal_navigator` startet |
| SC-002 | Healthcheck antwortet mit 200 | `GET /health` → `{"status":"ok"}` |
| SC-003 | Fall kann über API angelegt werden | `POST /api/v1/cases` → 201 + Case-Daten |
| SC-004 | Angelegter Fall erscheint in Fallliste | `GET /api/v1/cases` → count ≥ 1 |
| SC-005 | Falldetail kann abgerufen werden | `GET /api/v1/cases/{id}` → 200 + vollständige Daten |
| SC-006 | Unbekannte UUID liefert Fehlerobjekt | `GET /api/v1/cases/000...000` → 404 + `{"error":{...}}` |
| SC-007 | Leerer Titel wird abgelehnt | `POST` mit `""` → 422 |
| SC-008 | Persistenz über Neustart | Stopp/Start mit gleichem `PLN_DATA_DIR` → Daten erhalten |
| SC-009 | Alle Tests grün | 81 Tests passed (M1-M4), 35 M1-spezifisch |
| SC-010 | Coverage ≥ 90 % | Aktuell 96 % (M1-Kernmodule 100 %) |
| SC-011 | Ruff und Mypy ohne Fehler | Ruff: "All checks passed!", Mypy: "Success" |
| SC-012 | Keine echten Daten im Repository | 0 Treffer für nicht-synthetische Falldaten |
| SC-013 | Keine Remote-Laufzeitabhängigkeit | 0 externe URLs, 0 HTTP-Clients in `src/` |

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
