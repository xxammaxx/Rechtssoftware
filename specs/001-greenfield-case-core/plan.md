# Plan — M1 Greenfield Foundation and Case Core

## Ziel

Ein lokal ausführbares Python-Backend, das einen Fall anlegen, Fälle auflisten
und einen einzelnen Fall abrufen kann. Persistenz über lokale SQLite-Datenbank.

## Architekturansatz

**Modularer Monolith** mit FastAPI auf 127.0.0.1 und vier klar getrennten Schichten:

```
API (FastAPI) → Application (Services/Ports) → Domain (Entities) → Infrastructure (SQLite)
```

## Implementierungsstrategie

Red-Green-Refactor mit TDD:

1. Red Tests für Domain schreiben (fehlschlagend)
2. Domain-Layer implementieren (Tests werden grün)
3. Red Tests für SQLite-Repository schreiben
4. SQLite-Repository implementieren
5. Red Tests für Application Service schreiben
6. Application Service implementieren
7. Red Tests für API schreiben
8. FastAPI-Routen und App Factory implementieren
9. Integrationstests, Security-Sweep, Dokumentation

## Technologie-Stack

| Komponente | Technologie | Begründung |
|-----------|-------------|------------|
| API | FastAPI | Async, Pydantic-validierung, OpenAPI-Doku |
| Server | Uvicorn | ASGI, lokale Ausführung |
| Persistenz | sqlite3 (stdlib) | Transparent, geringe Abhängigkeit |
| Validierung | Pydantic (via FastAPI) | Typisiert, deklarativ |
| Tests | pytest + httpx | Bewährt, async-fähig |
| Linting | Ruff | Schnell, einheitlich |
| Typ-Prüfung | mypy | Statische Typsicherheit |

## Projektstruktur

```
src/private_legal_navigator/
├── domain/case.py              → Case-Entity, Validierung
├── application/
│   ├── case_repository.py      → Repository-Port (Protocol)
│   └── case_service.py         → Use Cases
├── infrastructure/
│   ├── database.py             → SQLite-Verbindung, Schema
│   └── sqlite_case_repository.py → Repository-Implementierung
├── api/
│   ├── schemas.py              → Pydantic-Modelle
│   ├── errors.py               → Fehlerklassen, Handler
│   └── routes.py               → FastAPI-Routen
├── config.py                   → Settings (PLN_DATA_DIR etc.)
├── app.py                      → App Factory
└── __main__.py                 → Entry Point
```

## Meilensteine

1. **Governance & Spec** — Constitution, Spec, Plan, Tasks, ADR (dieser Lauf)
2. **Domain & Persistenz** — Red Tests → Domain → Repository → Service
3. **API & Integration** — Red Tests → Routes → App Factory → Smoke Test
4. **Quality Gates** — Tests, Coverage, Linting, Typprüfung, Security
5. **Documentation & Commit** — Docs, Run Report, Feature-Commit

## Risiken

| Risiko | Mitigation |
|--------|------------|
| Python-Version nicht kompatibel | `py -3.11` verwenden, Minimum 3.11 |
| venv unter Windows/Git-Bash | `.venv/Scripts/python.exe` Pfad beachten |
| SQLite Threading | Verbindung pro Operation, kein globaler State |
| Datenbank im Repo | `data/` und `*.sqlite` in `.gitignore` |
