# M7-A Reality Refresh — Ausgangszustand

**Datum:** 2026-07-22T00:00:00Z
**Branch:** feat/linux-git-installation
**Start-HEAD:** fafce2ce15c65756662eff92070f1c0bf44368fc
**Basis-HEAD (main):** 065072fe7857a91a8467461ec88cdeb103a54da3

## Repository

- **Remote:** https://github.com/xxammaxx/Rechtssoftware.git
- **Working Tree:** clean (keine staged/unstaged Änderungen)
- **git diff --check:** clean
- **git diff --stat:** empty

## Runtime

- **Python:** 3.14.6
- **Python-Mindestversion (pyproject):** >=3.11
- **Datenbank:** SQLite (WAL mode, foreign keys ON, row_factory=sqlite3.Row)
- **DB-Pfad:** `~/.private-legal-navigator/private_legal_navigator.db`
- **Server:** FastAPI + Uvicorn, bindet an 127.0.0.1:8000
- **Templates:** Jinja2
- **Dependency Injection:** app.state (keine DI-Bibliothek)

## Teststatistik

- **Tests gesammelt:** 703
- **Framework:** pytest 8.x, pytest-asyncio, pytest-cov, httpx
- **Coverage-Requirement:** >=90%
- **Typisierung:** mypy strict mode
- **Lint:** ruff (E, F, W, I, N, UP, B, C4, SIM)

## Architektur (vor M7-A)

### Schichten
```
api/         - FastAPI-Routen, UI-Routen, Schemas, Form-Helpers
application/ - Services, Repositories (Ports), ViewModels
domain/      - Case, Document, ReferenceEvent, Deadline, Classification
infrastructure/ - SQLite-Repos, PDF-Textractor, Classifier, FileStorage, CalendarArithmetic
middleware/   - CSRF, HostValidation, SecurityHeaders, SecurityDependencies
presentation/ - Jinja2-Vorlagen, static CSS/JS
```

### Existierende ADRs
1. **ADR-001** — Local Modular Monolith (FastAPI + SQLite, Schichten: API→App→Domain→Infra)
2. **ADR-002** — Confirmed Reference Events & Calendar Arithmetic (M6-A)
3. **ADR-003** — Local Confirmation Workspace (M6-UI, CSRF, Idempotency, PRG)

### Existierende Datenbank-Tabellen
- `cases` (case_id, title, status, created_at, updated_at)
- `documents` (document_id, case_id, filename, mime_type, file_size, storage_path, text_content, ...)
- `document_classifications` (document_id, classification_type, confidence, ...)
- `deadline_candidates` (per-document, on-demand analysis)
- `confirmed_reference_events` (confirmation_id, candidate_id, document_id, event_type, confirmed_date, supersedes, is_revoke, ...)
- `idempotency_records` (idempotency_key, operation_type, status, ...)

### Existierende Patterns (wiederverwenden für M7-A)
- **Confirm/Reject/Revoke/Correct Lifecycle** (ADR-002, ADR-003)
- **Idempotency** mit `idempotency_records` Tabelle
- **CSRF** über `CsrfTokenService` + Browser-Nonce-Cookie
- **POST-only** für zustandsändernde Aktionen + PRG (303 Redirect)
- **Expected-State Validation** bei Correct und Revoke
- **Safe Logging** via `safe_log_event` / `safe_log_failure`
- **Sanitised Error Boundaries** — keine Stacktraces in Responses

### Middleware Stack (in Reihenfolge)
1. HostValidationMiddleware
2. SecurityHeadersMiddleware

### Konfiguration
- `Settings` (frozen dataclass) mit `PLN_DATA_DIR`, `PLN_HOST`, `PLN_PORT`, `PLN_CSRF_SECRET`
- `PLN_DATA_DIR` default: `~/.private-legal-navigator` (XDG-kompatibel)
- Keine `.env`-Datei im Repository

## Was vor M7-A NICHT existiert

- Kein Rechtsquellenmodell
- Kein Quellen-Sync
- Kein XML-Parsing
- Kein HTTP-Client für externe Quellen
- Keine FTS5-Volltextsuche (SQLite FTS5 ist built-in verfügbar)
- Kein Rechtsverlauf (Case Legal Timeline)
- Keine Normverknüpfung (Case Legal Links)
- Kein Evidence Pack
- Kein CLI für Legal Operations
- Keine FTS5-Tabellen

## Bestehende uncommitted Änderungen

- `.opencode/` — Agenten-Konfiguration (nur im untracked state)
- `evidence/` — Test-Evidence (nicht committen)
- Keine Änderungen an getrackten Dateien

## Linux-Kompatibilität

- `feat/linux-git-installation` fügt Linux-Installations-Skripte hinzu (nicht auf main)
- `main` branch: XDG-kompatibel via `Path.home() / ".private-legal-navigator"`
- Keine hartcodierten Windows-Pfade im Code
- `pyproject.toml` definiert `Operating System :: OS Independent`

## Risikoklassifikation für M7-A

- **Tier:** HIGH_HUMAN_GATE
- **Begründung:** Rechtsquellenimport berührt XML-Sicherheit, Quellenauthentizität, alle Änderungen müssen vollständig nachvollziehbar sein
- **Kein Push, kein Merge, kein Release** ohne explizite Freigabe

## Entscheidung zur Branch-Strategie

- Basis: `main` (065072f)
- Ziel-Branch: `feat/m7a-legal-source-foundation`
- `feat/linux-git-installation` wird NICHT als Basis verwendet (eigenständiger Feature-Branch)
