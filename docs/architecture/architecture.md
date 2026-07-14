# Architektur — PrivateLegalNavigator

## Zielbild

```
┌────────────────────────────┐
│  Client / späteres UI      │
└──────────┬─────────────────┘
           │ HTTP (127.0.0.1)
┌──────────▼─────────────────┐
│  FastAPI API-Schicht       │
│  - Routen (/api/v1/cases)  │
│  - Pydantic-Schemas        │
│  - Fehlerbehandlung        │
└──────────┬─────────────────┘
           │
┌──────────▼─────────────────┐
  │  Application Services      │
  │  - CaseService             │
  │  - DocumentService         │
  │  - DeadlineService (M5)    │
  │  - Repository Port (ABC)   │
  │  - DeadlineExtractor (ABC) │
  └──────────┬─────────────────┘
            │
  ┌──────────▼─────────────────┐
  │  Domain Model              │
  │  - Case Entity             │
  │  - Document Entity         │
  │  - ClassificationResult    │
  │  - DeadlineCandidate (M5)  │
  │  - CaseStatus (StrEnum)    │
  │  - Fachliche Invarianten   │
  └──────────┬─────────────────┘
           │
┌──────────▼─────────────────┐
│  Infrastructure            │
│  - SqliteCaseRepository    │
│  - database.py (Schema)    │
└──────────┬─────────────────┘
           │
┌──────────▼─────────────────┐
│  SQLite-Datenbank          │
│  (konfigurierbares Verz.)  │
└────────────────────────────┘
```

## Komponenten

### API (FastAPI)
- Routen in `api/routes.py`
- Request/Response-Schemas in `api/schemas.py`
- Fehlerbehandlung in `api/errors.py`
- App Factory in `app.py`
- Dependency Injection über `app.state` + FastAPI `Depends`

### Application
- `CaseService`: Orchestriert Use Cases (create, get, list)
- `CaseRepository` (ABC): Port für Persistenz
- Keine direkte SQL-Abhängigkeit

### Domain
- `Case`: Entität mit UUID, Titel, Status, Zeitstempeln
- `CaseStatus`: StrEnum (`open` in M1)
- Validierung: Titel 1–200 Zeichen, getrimmt, nicht leer

### Infrastructure
- `database.py`: `get_connection()` mit PRAGMA foreign_keys, `initialize_schema()`
- `SqliteCaseRepository`: Implementiert `CaseRepository` mit parametrisierten Queries
- SQLite-Verbindung pro Operation (kein globaler State)

## Datenfluss

1. `POST /api/v1/cases` → `CreateCaseRequest` (Pydantic) → `CaseService.create_case()` → `Case(title=...)` → `repository.save(case)` → SQLite
2. `GET /api/v1/cases` → `CaseService.list_cases()` → `repository.list_all()` → SQLite → `CaseListResponse`
3. `GET /api/v1/cases/{id}` → `CaseService.get_case(uuid)` → `repository.get_by_id(uuid)` → SQLite → `CaseResponse` oder 404

## Fehlerfluss

- Validierungsfehler → 422 (FastAPI/Pydantic)
- Nicht gefunden → 404 mit `{"error": {"code": "CASE_NOT_FOUND", ...}}`
- Datenbankfehler → 500 mit `{"error": {"code": "DATABASE_ERROR", ...}}`
- Keine Stacktraces, keine SQL, keine Dateipfade in Antworten

## Sicherheitsgrenzen

- Bindung: `127.0.0.1` (kein Netzwerkzugriff von außen)
- Keine CORS-Konfiguration (kein Cross-Origin-Zugriff)
- Keine externen Requests im Code
- Parametrisierte SQL-Queries (kein Injection-Risiko)
- Kein Request-Body-Logging
- Keine `.env`-Datei, keine Secrets

## Teststrategie

| Schicht | Testtyp | Technik |
|---------|---------|---------|
| Domain | Unit | Direkte Instanziierung |
| Repository | Integration | Temporäre SQLite-DB |
| Service | Unit | Mocked Repository |
| API | Integration | ASGI-Transport (httpx) |

## Erweiterbarkeit

- Neue API-Endpunkte → Neue Routen im `api/`-Layer
- Neue Domänen-Entitäten → Neue Module in `domain/`
- Neue Persistenz → Neuer Adapter für `CaseRepository`-Port
- Frontend → Nutzt bestehende `/api/v1/`-Endpunkte
