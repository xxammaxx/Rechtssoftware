# PrivateLegalNavigator

Lokale, datenschutzorientierte Unterstützung bei eigenen rechtlichen und
behördlichen Angelegenheiten.

## Status

**M6-A — Bestätigte Bezugsereignisse und Kalenderarithmetik** — abgeschlossen.

Aktuell implementiert:
- Case-Management: Fall anlegen, auflisten, Details abrufen (M1)
- Dokument-Upload (PDF) mit MIME-Type-Prüfung und Größenlimit (20 MB) (M2)
- Sichere lokale Dateiablage (UUID-basierte Pfade, Path-Traversal-Schutz) (M2)
- Automatische PDF-Textextraktion (pymupdf, vollständig lokal) (M3)
- Textabruf pro Dokument über API (M3)
- Regelbasierte Dokumentklassifikation (Bescheid, Rechnung, Mahnung, etc.) (M4)
- Deterministische Fristkandidaten-Erkennung aus extrahiertem Text (M5)
- Reference-Event-Kandidaten aus Dokumenttext (M6-A)
- Explizite Bestätigung, Ablehnung und manuelle Datumseingabe (M6-A)
- Reine Tages-/Wochen-Kalenderarithmetik (M6-A)
- Unverbindliche Berechnungsvorschau mit vollständigem Rechenweg (M6-A)
- Bestätigungshistorie mit Supersession-Chain (M6-A)
- Privacy-Logging-Filter und Exception-Boundary (M6-A)
- Dokument-Download und -Auflistung pro Fall
- Lokale FastAPI-Anwendung auf 127.0.0.1:8000
- SQLite-Persistenz mit automatischer Schema-Initialisierung
- Health-Check-Endpunkt

## Explizite Grenzen

Diese Software bietet **keine** Rechtsberatung. Sie trifft **keine**
automatischen Rechtsentscheidungen. Jede rechtlich relevante Ausgabe
erfordert menschliche Prüfung.

Noch **nicht** implementiert:
- Frontend (M6-UI in Spezifikation, siehe #6)
- OCR (optische Texterkennung für gescannte Dokumente)
- Verbindliche Rechtsfristberechnung (M6-B geplant)
- Rechtsbewertung
- Handlungsempfehlungen
- Entwurfserstellung / Schreiben
- Authentifizierung / Mehrbenutzer
- Verschlüsselung

## Architektur

Modularer Monolith mit vier Schichten:

```
Client / HTTP → FastAPI (127.0.0.1:8000) → Application Services → Domain → SQLite
```

Siehe [ADR-001](docs/architecture/adr-001-local-modular-monolith.md) und
[Architekturübersicht](docs/architecture/architecture.md).

## Setup (Windows)

```bash
# Voraussetzungen: Python 3.11+, Git

# Repository klonen
git clone https://github.com/xxammaxx/Rechtssoftware.git
cd Rechtssoftware

# Virtuelle Umgebung erstellen
py -3.11 -m venv .venv

# Abhängigkeiten installieren
.venv/Scripts/python.exe -m pip install -e ".[dev]"
```

## Start

```bash
.venv/Scripts/python.exe -m private_legal_navigator
```

Standardmäßig unter http://127.0.0.1:8000 erreichbar.

Konfiguration über Umgebungsvariablen:
- `PLN_DATA_DIR` — Datenverzeichnis für SQLite (Default: `~/.private-legal-navigator`)
- `PLN_HOST` — Host-Bindung (Default: `127.0.0.1`)
- `PLN_PORT` — Port (Default: `8000`)

## Tests

```bash
.venv/Scripts/python.exe -m pytest --cov=src/private_legal_navigator --cov-fail-under=90
.venv/Scripts/python.exe -m ruff check src tests
.venv/Scripts/python.exe -m mypy src
```

## API

| Methode | Pfad | Beschreibung |
|---------|------|-------------|
| GET | `/health` | Health-Check |
| POST | `/api/v1/cases` | Fall anlegen |
| GET | `/api/v1/cases` | Alle Fälle auflisten |
| GET | `/api/v1/cases/{case_id}` | Einzelnen Fall abrufen |
| POST | `/api/v1/cases/{case_id}/documents` | PDF-Dokument zu Fall hochladen |
| GET | `/api/v1/cases/{case_id}/documents` | Dokumente eines Falls auflisten |
| GET | `/api/v1/cases/{case_id}/documents/{doc_id}` | Dokument herunterladen |
| GET | `/api/v1/cases/{case_id}/documents/{doc_id}/text` | Extrahierten Text abrufen |
| POST | `/api/v1/cases/{case_id}/documents/{doc_id}/deadline-candidates` | Fristkandidaten erkennen (M5) |
| GET | `/api/v1/cases/{case_id}/documents/{doc_id}/deadline-candidates/{idx}/reference-events` | Bezugsereignisse abrufen (M6-A) |
| POST | `/api/v1/cases/{case_id}/documents/{doc_id}/deadline-candidates/{idx}/reference-events/confirm` | Bezugsdatum bestätigen/ablehnen (M6-A) |
| POST | `/api/v1/cases/{case_id}/documents/{doc_id}/deadline-candidates/{idx}/calculation-preview` | Berechnungsvorschau (M6-A) |
| GET | `/api/v1/cases/{case_id}/documents/{doc_id}/deadline-candidates/{idx}/reference-events/history` | Bestätigungshistorie (M6-A) |

Vollständige API-Dokumentation: [contracts/api.md](specs/001-greenfield-case-core/contracts/api.md)

> **M6-A-Hinweis:** Reference-Event- und Calculation-Preview-Endpunkte
> liefern eine unverbindliche Berechnungsvorschau auf Basis bestätigter Bezugsdaten.
> Sie berechnen keine verbindliche Rechtsfrist, wenden keine Feiertags- oder
> Wochenendregeln an und ersetzen keine anwaltliche oder behördliche Prüfung.
> Jede Ausgabe enthält `human_review_required=true` und `legal_validity_assessed=false`.
> Siehe [M6-A-Spec](specs/006a-reference-events-calendar-arithmetic/spec.md).

## Datenschutz

- Alle Daten bleiben lokal
- Keine Cloud-Verarbeitung, keine Telemetrie
- Backend bindet nur an 127.0.0.1
- Keine Falldaten in Logs
- Keine externen Laufzeitrequests

## Projektstruktur

```
src/private_legal_navigator/
├── domain/          → Case-Entität, Status, Invarianten
├── application/     → Use Cases, Repository-Port
├── infrastructure/  → SQLite-Connection, Repository-Impl
└── api/             → FastAPI-Routen, Schemas, Fehler

tests/
├── unit/            → Domain, Service (mocked)
├── integration/     → SQLite-Repository (temp DB)
└── api/             → FastAPI-Endpunkte (ASGI-Transport)

specs/               → Spec-Kit-Artefakte
docs/                → Architektur, ADRs, Security
```
