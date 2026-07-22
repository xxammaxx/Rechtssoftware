# PrivateLegalNavigator

Lokale, datenschutzorientierte Unterstützung bei eigenen rechtlichen und
behördlichen Angelegenheiten.

## Status

**M6-UI — Lokaler Release Candidate (v0.1.0-rc)** — abgeschlossen.

Aktuell implementiert:
- Case-Management: Fall anlegen, auflisten, Details abrufen (M1)
- Dokument-Upload (PDF) mit MIME-Type-Prüfung und Größenlimit (20 MB) (M2)
- Sichere lokale Dateiablage (UUID-basierte Pfade, Path-Traversal-Schutz) (M2)
- Automatische PDF-Textextraktion (pymupdf, vollständig lokal) (M3)
- Textabruf pro Dokument über API (M3)
- Regelbasierte Dokumentklassifikation (Bescheid, Rechnung, Mahnung, etc.) (M4)
- Deterministische Fristkandidaten-Erkennung aus extrahiertem Text (M5)
- Reference Events: Bezugsereignis-Kandidaten aus M5-Daten erkennen (M6-A)
- Reference Events: Bezugsdatum explizit bestätigen oder ablehnen (M6-A)
- Calendar Arithmetic: Unverbindliche Berechnungsvorschau (Tage/Wochen) (M6-A)
- Privacy-Logging mit automatisierter Redaction aller sensiblen Felder (M6-A)
- M6-UI: Browser-Oberfläche für Fallnavigation, Dokumentenansicht, Kandidaten-Workspace (M6-UI Slice 1)
- M6-UI: Bestätigungs-Workflow (Confirm/Reject/Manual) mit CSRF und Idempotenz (M6-UI Slice 2)
- M6-UI: Correct, Revoke, vollständige Bestätigungshistorie (M6-UI Slice 3)
- M6-UI: Calculation Preview mit Trace und Server-seitiger Revalidierung (M6-UI Slice 4, read-only)
- Sanitisierte Exception Boundary (keine Stacktraces in HTTP-Antworten) (M6-A)
- Dokument-Download und -Auflistung pro Fall
- Lokale FastAPI-Anwendung auf 127.0.0.1:8000
- SQLite-Persistenz mit automatischer Schema-Initialisierung
- Health-Check-Endpunkt

## Explizite Grenzen

Diese Software bietet **keine** Rechtsberatung. Sie trifft **keine**
automatischen Rechtsentscheidungen. Jede rechtlich relevante Ausgabe
erfordert menschliche Prüfung.

Noch **nicht** implementiert:
- M6-B (Feiertags-, Wochenend-, Zustellungsregeln)
- OCR (optische Texterkennung für gescannte Dokumente)
- Verbindliche Rechtsfristberechnung (alle Berechnungen sind unverbindliche Vorschauen)
- Rechtsbewertung
- Handlungsempfehlungen
- Entwurfserstellung / Schreiben
- Authentifizierung / Mehrbenutzer
- Verschlüsselung

**M6-UI Status (Juli 2026):**
- ✅ Slice 1 (Case/Document/Workspace Views) — implementiert
- ✅ Slice 2 (Confirm, Reject, Manual Confirm + CSRF + Idempotency) — implementiert
- ✅ Slice 3 (Correct, Revoke, History) — implementiert
- ✅ Slice 4 (Calculation Preview + Trace) — implementiert

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
| GET | `/api/v1/cases/{case_id}/documents/{doc_id}/deadline-candidates/{cand_id}/reference-events` | Bezugsereignis-Kandidaten abrufen (M6-A) |
| POST | `.../reference-events/confirm` | Bezugsereignis bestätigen/ablehnen (M6-A) |
| POST | `.../calculation-preview` | Unverbindliche Berechnungsvorschau (M6-A) |
| GET | `.../reference-events/history` | Bestätigungshistorie abrufen (M6-A) |

Vollständige API-Dokumentation: [contracts/api.md](specs/001-greenfield-case-core/contracts/api.md)

> **M6-A-Hinweis:** Die Berechnungsvorschau ist ausdrücklich **unverbindlich**.
> Sie berechnet keine rechtlich gültige Frist. Jede Berechnung erfordert
> vorherige explizite menschliche Bestätigung des Bezugsdatums.
> Das Ergebnis enthält `human_review_required=true` und
> `legal_validity_assessed=false`. Siehe [M6-A-Spec](specs/006a-reference-events-calendar-arithmetic/spec.md).

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
├── api/             → FastAPI-Routen, Schemas, Fehler
│   └── ui_routes.py → M6-UI HTML-Routen (lesend + schreibend)
├── presentation/
│   └── templates/   → Jinja2-HTML-Vorlagen (M6-UI)
└── static/          → CSS, JS (lokal, kein CDN)

tests/
├── unit/            → Domain, Service (mocked)
├── integration/     → SQLite-Repository (temp DB)
│   └── test_m6ui_slice4_calculation_preview.py → Preview-spezifische Tests
├── e2e/             → Playwright-Browser-Tests
│   └── fixtures/    → axe.min.js (lokal)
└── api/             → FastAPI-Endpunkte (ASGI-Transport)

specs/               → Spec-Kit-Artefakte
docs/                → Architektur, ADRs, Security
```
