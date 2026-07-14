# PrivateLegalNavigator

Lokale, datenschutzorientierte Unterstützung bei eigenen rechtlichen und
behördlichen Angelegenheiten.

## Status

**M5 — Deterministische Fristkandidaten-Erkennung** — abgeschlossen.

Aktuell implementiert:
- Case-Management: Fall anlegen, auflisten, Details abrufen (M1)
- Dokument-Upload (PDF) mit MIME-Type-Prüfung und Größenlimit (20 MB) (M2)
- Sichere lokale Dateiablage (UUID-basierte Pfade, Path-Traversal-Schutz) (M2)
- Automatische PDF-Textextraktion (pymupdf, vollständig lokal) (M3)
- Textabruf pro Dokument über API (M3)
- Regelbasierte Dokumentklassifikation (Bescheid, Rechnung, Mahnung, etc.) (M4)
- Deterministische Fristkandidaten-Erkennung aus extrahiertem Text (M5)
- Dokument-Download und -Auflistung pro Fall
- Lokale FastAPI-Anwendung auf 127.0.0.1:8000
- SQLite-Persistenz mit automatischer Schema-Initialisierung
- Health-Check-Endpunkt

## Explizite Grenzen

Diese Software bietet **keine** Rechtsberatung. Sie trifft **keine**
automatischen Rechtsentscheidungen. Jede rechtlich relevante Ausgabe
erfordert menschliche Prüfung.

Noch **nicht** implementiert:
- OCR (optische Texterkennung für gescannte Dokumente)
- Verbindliche Rechtsfristberechnung (M5 erkennt nur Textstellen)
- Rechtsbewertung
- Handlungsempfehlungen
- Entwurfserstellung / Schreiben
- Frontend
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

Vollständige API-Dokumentation: [contracts/api.md](specs/001-greenfield-case-core/contracts/api.md)

> **M5-Hinweis:** Der Deadline-Candidates-Endpunkt erkennt ausschließlich
> mögliche Frist- und Terminangaben im Text. Er berechnet keine verbindliche
> Rechtsfrist und ersetzt keine anwaltliche oder behördliche Prüfung.
> Siehe [M5-Spec](specs/005-deadline-candidates/spec.md).

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
