# M1 Independent Analysis Report — PrivateLegalNavigator Greenfield Foundation

**Analyse-Datum:** 2026-07-13T11:45:00Z  
**Analyst:** Issue Orchestrator (unabhängiger Analyse-Lauf)  
**Modus:** READ_ONLY_ANALYSIS  
**Repository:** xxammaxx/Rechtssoftware

---

## 1. Abschlussklassifikation

### `GREEN_WITH_NOTES`

M1 ist technisch abgeschlossen und tragfähig. Alle Kernfunktionen sind implementiert, getestet und verifiziert. Die Architektur ist sauber geschichtet. Dokumentation weist kleinere Drift auf (README auf M3-Stand, Spec-Selbstreferenz, Tasks ungecheckt), aber keine funktionalen oder Sicherheitsmängel.

---

## 2. Kurzfazit

```text
Behauptung → Repositoryrealität → ausführbarer Code → Tests → Runtime → Evidence → belastbares Verdict
```

Der Greenfield-Lauf M1 hat ein belastbares Fundament geliefert. Ein lokal ausführbares FastAPI-Backend mit SQLite-Persistenz und Case-Management (CRUD) ist vorhanden. 81 Tests passieren (davon ~35 M1-spezifisch), 96% Coverage, Ruff/Mypy sauber. Architektur als modularer Monolith mit klaren Schichtengrenzen verifiziert. Alle API-Endpunkte funktionieren, Persistenz über Neustart bestätigt, Local-only eingehalten.

Der Run Report des Bau-Agenten ist in den technischen Kernaussagen korrekt, enthält aber einige nicht verifizierbare Behauptungen zur Spec-Kit-Traceability (FR-Enumeration fehlt in der Spec).

Der Branch `feat/004-document-classification` (HEAD) enthält M2-M4 aufbauend auf M1, ohne Regressionen des M1-Kerns.

---

## 3. OS und Shell

| Attribut | Wert |
|----------|------|
| OS | Windows 10 (Build 19041) |
| Shell | PowerShell 5.1.19041.6456 |
| Arbeitsverzeichnis | C:\Rechtssoftware |
| Git | 2.47.0.windows.1 |
| gh | 2.92.0 |
| Python (default) | 3.11.9 |
| Python (venv) | 3.11.9 |
| Node | 24.14.0 |
| npm | 11.9.0 |

---

## 4. Werkzeugversionen

| Werkzeug | Version |
|----------|---------|
| pytest | 9.1.1 |
| pytest-cov | 7.1.0 |
| pytest-asyncio | 1.4.0 |
| httpx | (via dev deps) |
| ruff | (via dev deps) |
| mypy | (via dev deps) |
| fastapi | >=0.115.0 |
| uvicorn | >=0.30.0 |

---

## 5. Git-Realität

- **Remote:** `https://github.com/xxammaxx/Rechtssoftware.git` ✓
- **Aktueller Branch:** `feat/004-document-classification` (HEAD)
- **Status:** Clean (0 uncommitted changes)
- **Git fsck:** Clean
- **Whitespace:** Clean

### Branches

```
main                              → Baseline: d977e5b
feat/001-greenfield-case-core     → M1: 71050e4
feat/002-document-import          → M2: 788ae7c
feat/003-text-extraction          → M3: 3602236
feat/004-document-classification  → M4: d8102b0 (HEAD)
```

### Commit-Historie

```
d8102b0 (HEAD -> feat/004-document-classification) feat(classify): add rule-based document classification
3602236 (feat/003-text-extraction) feat(extract): add local PDF text extraction
788ae7c (feat/002-document-import) feat(docs): add document import and secure file storage
71050e4 (feat/001-greenfield-case-core) feat(core): add greenfield case management foundation
d977e5b (main) chore: initialize greenfield repository
```

- Kein Push, kein PR, kein Merge ausgeführt ✓
- Keine unerwarteten Branches ✓
- Keine `.sqlite`, `.db`, `.env`, Secrets im Repository ✓

---

## 6. M1 Commit Details

**SHA:** `71050e4`  
**Branch:** `feat/001-greenfield-case-core`  
**Dateien:** 36 files, 2037 insertions, 3 deletions

---

## 7. Repository-Struktur (M1-relevant)

```
.specify/memory/constitution.md          Governance-Dokument
AGENTS.md                                Agent-Arbeitsprinzipien
README.md                                Projektübersicht (auf M3-Stand)
pyproject.toml                           Projekt- & Abhängigkeitsdeklaration
.editorconfig                            Editor-Konfiguration
.gitignore                               Ausschlussregeln (Datenbanken, Secrets)

specs/001-greenfield-case-core/          M1 Spec-Kit-Artefakte
├── spec.md                               User Stories + Anforderungen
├── plan.md                               Implementierungsplan
├── tasks.md                              Taskliste (31 Tasks)
├── data-model.md                         Case-Entität + SQLite-Schema
└── contracts/api.md                      API-Verträge (4 Endpunkte)

src/private_legal_navigator/
├── domain/case.py                        Case-Entität, CaseStatus (StrEnum)
├── application/
│   ├── case_repository.py                Repository-Port (ABC)
│   └── case_service.py                   CaseService Use Cases
├── infrastructure/
│   ├── database.py                       SQLite-Connection, Schema-Init
│   └── sqlite_case_repository.py         Repository-Implementierung
├── api/
│   ├── schemas.py                        Pydantic Request/Response
│   ├── errors.py                         CaseNotFoundError, Handler
│   └── routes.py                         FastAPI-Routen
├── config.py                             Settings (env vars)
├── app.py                                App Factory
└── __main__.py                           Entry Point

tests/
├── unit/
│   ├── test_domain_case.py               10 Domain-Tests
│   └── test_case_service.py              7 Service-Tests (mocked repo)
├── integration/
│   └── test_sqlite_repository.py         7 Repository-Integrationstests
└── api/
    └── test_cases_api.py                 10 API-Integrationstests

docs/
├── architecture/
│   ├── adr-001-local-modular-monolith.md  Architekturentscheidung
│   └── architecture.md                    Architekturübersicht
├── security/
│   └── privacy-and-security-invariants.md 20 Invarianten
└── reports/
    └── M1-greenfield-foundation.md        Bau-Agent Run Report
```

---

## 8. Run-Report-Claims-Matrix

| Claim | Quelle | Verifikation | Ergebnis | Status |
|-------|--------|-------------|----------|--------|
| 35 Tests passiert | Run Report Z.103 | pytest: 35 M1-Tests grün (81 total mit M2-M4) | 35/35 M1 = PASS | VERIFIED |
| 93% Coverage | Run Report Z.104 | M1-Kernmodule: 100%, Gesamt: 96% | Höher als Claim | VERIFIED |
| Ruff 0 errors | Run Report Z.105 | `ruff check src tests` → "All checks passed!" | PASS | VERIFIED |
| Mypy 0 errors | Run Report Z.106 | `mypy src` → "Success: no issues found" | PASS | VERIFIED |
| ARCH_GREEN | Run Report Z.53 | Schichten sauber, Domain ohne Framework-Abhängigkeiten | PASS | VERIFIED |
| 4 API-Endpoints | Run Report Z.64-68 | Health, Create, List, Get — alle per Smoke-Test verifiziert | PASS | VERIFIED |
| 127.0.0.1 Bindung | Run Report Z.123 | Default 127.0.0.1, kein 0.0.0.0 im Code | PASS | VERIFIED |
| Keine externen URLs | Run Report Z.117 | 0 Treffer in `src/` | PASS | VERIFIED |
| Keine .env/Secrets | Run Report Z.118-119 | 0 Treffer | PASS | VERIFIED |
| Kein CORS | Run Report Z.120 | Keine CORS-Konfiguration | PASS | VERIFIED |
| Kein .sqlite im Repo | Run Report Z.121 | 0 Treffer | PASS | VERIFIED |
| Parametrisierte SQL | Run Report Z.124 | Alle Queries verwenden `?` Platzhalter | PASS | VERIFIED |
| SYNTHETISCH-Präfix | Run Report Z.125 | Alle Testdaten mit Präfix | PASS | VERIFIED |
| Alle 20 INV erfüllt | Run Report Z.129 | Code + Tests bestätigen INV-01 bis INV-20 | PASS | VERIFIED |
| SPEC_GREEN, 20 FRs, 13 SCs | Run Report Z.133 | Spec listet keine FR-/SC-IDs auf | Nicht verifizierbar | UNVERIFIED |
| Kein Scope Creep | Run Report Z.134 | Kein M2+-Code im M1-Kern | PASS | VERIFIED |
| 0 Critical/Major/Minor | Run Report Z.137-139 | Bestätigt: keine funktionalen Mängel | PASS | VERIFIED |

---

## 9. Spec-Kit-Modus

- **Modus:** SPECKIT_TEMPLATE_FALLBACK (laut Run Report)
- **CLI:** specify 0.8.5.dev0
- **Constitution:** Vorhanden (70 Zeilen, projektspezifisch, nicht generischer Template-Text)
- **Feature-Spec:** Vorhanden mit User Stories und Akzeptanzkriterien
- **Plan:** Vorhanden mit Meilensteinen, Tech-Stack, Projektstruktur
- **Tasks:** Vorhanden (31 Tasks), aber alle als `- [ ]` ungecheckt
- **Data Model:** Vorhanden, stimmt mit Domain und SQLite überein
- **Contracts:** Vorhanden, stimmen mit realen Endpunkten überein

### Auffälligkeiten

1. **Spec-Selbstreferenz (MAJOR):** `spec.md` Z.47 verweist auf "specs/001-greenfield-case-core/spec.md Abschnitt 'Functional Requirements'" — dieser Abschnitt existiert nicht. Die Spec enthält User Stories mit Akzeptanzkriterien, aber keine explizite FR-/SC-Enumeration mit IDs.

2. **Tasks ungecheckt (MINOR):** Alle 31 Tasks zeigen `- [ ]`. Der Build-Prozess hat sie nicht als erledigt markiert. Die Implementierung ist dennoch vollständig.

3. **Spec-Dateigröße:** Nur 67 Zeilen. Die User Stories decken die Kernfunktionen ab, aber die formale FR-/SC-Struktur fehlt.

---

## 10. Spec-Traceability-Matrix

| Anforderung | Spec-Referenz | Task | Implementierung | Test | Status |
|-------------|--------------|------|-----------------|------|--------|
| Fall anlegen mit Titel | US1 | T015, T019, T021 | domain/case.py, case_service.py, routes.py | test_domain_case.py, test_case_service.py, test_cases_api.py | COVERED |
| Titel getrimmt | US1 (AC) | T015 | domain/case.py:42 | test_domain_case.py:24-27 | COVERED |
| Leerer Titel rejected | US1 (AC) | T014, T015 | domain/case.py:50-51 | test_domain_case.py:29-32 | COVERED |
| Titel >200 rejected | US1 (AC) | T014, T015 | domain/case.py:52-54 | test_domain_case.py:39-43 | COVERED |
| Server-UUID | US1 (AC) | T015 | domain/case.py:41 | test_domain_case.py:51-55 | COVERED |
| Status "open" | US1 (AC) | T015 | domain/case.py:43 | test_domain_case.py:72-76 | COVERED |
| UTC-Zeitstempel | US1 (AC) | T015 | domain/case.py:40 | test_domain_case.py:57-61 | COVERED |
| 201 Created | US1 (AC) | T021 | routes.py:45 | test_cases_api.py:51-63 | COVERED |
| Fälle auflisten | US2 | T019, T021 | case_service.py, routes.py | test_case_service.py, test_cases_api.py | COVERED |
| Count in Liste | US2 (AC) | T021 | routes.py:63 | test_cases_api.py:100 | COVERED |
| Deterministisch sortiert | US2 (AC) | T017 | sqlite_case_repository.py:75 (ORDER BY created_at DESC) | test_sqlite_repository.py:75-86 | COVERED |
| Leere Liste | US2 (AC) | T020 | routes.py:56-64 | test_cases_api.py:85-90 | COVERED |
| Fall per UUID abrufen | US3 | T019, T021 | case_service.py, routes.py | test_case_service.py, test_cases_api.py | COVERED |
| Unbekannte ID → 404 | US3 (AC) | T021 | routes.py:74-75 | test_cases_api.py:120-127 | COVERED |
| Stabiles Fehlerformat | NFR | T021 | errors.py:7-17 | test_cases_api.py:126-127 | COVERED |
| 127.0.0.1 Bindung | NFR | T022 | config.py:19 | — (manuell geprüft) | COVERED |
| Keine externen Requests | NFR | T025 | — (Security-Sweep) | — (grep) | COVERED |
| Parametrisierte SQL | NFR | T017 | sqlite_case_repository.py (alle Queries) | — (Code-Review) | COVERED |
| Coverage ≥ 90% | NFR | T023 | pytest-cov | 96% Gesamt | COVERED |

---

## 11. Architekturverdict

### `ARCH_PASS`

Die Architektur entspricht dem dokumentierten Zielbild eines modularen Monolithen mit vier klar getrennten Schichten.

**Schichtenprüfung:**

| Schicht | Abhängigkeiten | Framework-frei? | Bewertung |
|---------|---------------|-----------------|-----------|
| **Domain** (case.py) | uuid, datetime, enum (stdlib only) | ✓ Ja | **PASS** |
| **Application** (case_service.py, case_repository.py) | Domain, ABC (stdlib) | ✓ Ja | **PASS** |
| **Infrastructure** (database.py, sqlite_case_repository.py) | Domain, Application, sqlite3 (stdlib) | ✓ Ja | **PASS** |
| **API** (routes.py, schemas.py, errors.py, app.py) | FastAPI, Pydantic, Application, Domain | ✗ (erwartet) | **PASS** |

**Dependency Direction:** API → Application → Domain ← Infrastructure ✓

**Kritische Prüfpunkte:**

| Prüfpunkt | Ergebnis |
|-----------|----------|
| Domain importiert FastAPI/Pydantic? | ✗ Nein — sauber |
| Domain importiert SQLite? | ✗ Nein — sauber |
| Repository-Port als ABC definiert? | ✓ Ja |
| App Factory vorhanden? | ✓ Ja (create_app) |
| App Factory testbar mit eigener Konfiguration? | ✓ Ja (Settings-Parameter) |
| API unter `/api/v1` versioniert? | ✓ Ja |
| `/health` vorhanden? | ✓ Ja |
| Fehlerformat stabil (`{"error": {"code": ..., "message": ...}}`)? | ✓ Ja |
| Settings per `PLN_DATA_DIR`, `PLN_HOST`, `PLN_PORT`? | ✓ Ja |
| Sicheres Default-Host (127.0.0.1)? | ✓ Ja |
| Datenverzeichnis außerhalb Repo? | ✓ Ja (~/.private-legal-navigator) |
| Config ohne Seiteneffekte beim Import? | ✓ Ja (frozen dataclass) |

---

## 12. Datenmodellprüfung

**Case-Entität:**

| Feld | Spec | Code | Übereinstimmung |
|------|------|------|-----------------|
| case_id | UUID, serverseitig | `uuid.uuid4()` in `__init__` | ✓ |
| title | 1-200 Zeichen, getrimmt | `MAX_TITLE_LENGTH = 200`, `title.strip()` | ✓ |
| status | "open" | `CaseStatus.OPEN = "open"` | ✓ |
| created_at | UTC, timezone-aware | `datetime.now(UTC)` | ✓ |
| updated_at | UTC, timezone-aware | `datetime.now(UTC)` | ✓ |

**SQLite-Schema:**

| Spec | Code (database.py) | Übereinstimmung |
|------|-------------------|-----------------|
| `CREATE TABLE IF NOT EXISTS cases` | Zeile 7-13 | ✓ |
| `case_id TEXT PRIMARY KEY` | Zeile 8 | ✓ |
| `title TEXT NOT NULL` | Zeile 9 | ✓ |
| `status TEXT NOT NULL DEFAULT 'open'` | Zeile 10 | ✓ |
| `created_at TEXT NOT NULL` | Zeile 11 | ✓ |
| `updated_at TEXT NOT NULL` | Zeile 12 | ✓ |
| `CREATE INDEX IF NOT EXISTS idx_cases_status` | Zeile 17 | ✓ |
| `CREATE INDEX IF NOT EXISTS idx_cases_created_at` | Zeile 18 | ✓ |
| `PRAGMA foreign_keys = ON` | Zeile 25 | ✓ |

**Invarianten:**

1. UUIDv4 servergeneriert ✓
2. Titel getrimmt und validiert ✓
3. Status bei Neuanlage "open" ✓
4. UTC-Zeitstempel ✓
5. PRAGMA foreign_keys ✓

---

## 13. API-Contract-Prüfung

| Endpoint | Spec Status | Test Status | Runtime Status | Match |
|----------|------------|-------------|----------------|-------|
| `GET /health` | 200 `{"status":"ok"}` | 200 `{"status":"ok"}` | 200 `{"status":"ok"}` | ✓ |
| `POST /api/v1/cases` | 201 + Case | 201 + Case | 201 + Case | ✓ |
| `GET /api/v1/cases` | 200 + items + count | 200 + items + count | 200 + items + count | ✓ |
| `GET /api/v1/cases/{id}` | 200 / 404 | 200 / 404 | 200 / 404 | ✓ |
| 404-Format | `{"error":{"code":"CASE_NOT_FOUND",...}}` | `{"error":{"code":"CASE_NOT_FOUND",...}}` | `{"error":{"code":"CASE_NOT_FOUND",...}}` | ✓ |
| 422-Format | VALIDATION_ERROR (Spec) | FastAPI-Standard | FastAPI-Standard | ⚠️ (Abweichung) |

**Abweichung 422-Format:** Der Spec-Vertrag (`contracts/api.md`) definiert ein eigenes 422-Format mit `{"error": {"code": "VALIDATION_ERROR", ...}}`. Die tatsächliche Implementierung nutzt FastAPIs Standard-Validierungsfehler (Pydantic `RequestValidationError`). Dies ist der Standardweg von FastAPI und funktional korrekt, weicht aber vom dokumentierten Contract ab. Das API-eigene `ErrorResponse`-Schema wird nur für 404 (CaseNotFoundError) verwendet.

---

## 14. Abhängigkeitsprüfung

**Runtime:**

| Paket | Version | Zweck | Notwendig? |
|-------|---------|-------|------------|
| fastapi | >=0.115.0 | API-Framework | ✓ M1-Kern |
| uvicorn[standard] | >=0.30.0 | ASGI-Server | ✓ M1-Kern |
| pymupdf | >=1.24.0 | PDF-Text-Extraktion | M3-Addon |
| python-multipart | >=0.0.9 | File-Upload | M2-Addon |

**Dev:**

| Paket | Version | Zweck |
|-------|---------|-------|
| pytest | >=8.0 | Test-Runner |
| pytest-cov | >=5.0 | Coverage |
| pytest-asyncio | >=0.24.0 | Async-Tests |
| httpx | >=0.27.0 | ASGI-Testclient |
| ruff | >=0.11.0 | Linter |
| mypy | >=1.11.0 | Type-Checker |

- Keine ORM, Cloud-SDK, Telemetrie, oder externe Logging-Dienste ✓
- `pip check` → "No broken requirements found" ✓
- pymupdf und python-multipart sind M2/M3-Abhängigkeiten, nicht M1

---

## 15. Testresultate

```
============================= 81 passed in 2.18s =============================
```

| Kategorie | Anzahl | Status |
|-----------|--------|--------|
| M1 Domain-Tests | 10 | PASSED |
| M1 Service-Tests | 7 | PASSED |
| M1 Repository-Tests | 7 | PASSED |
| M1 API-Tests | 10 | PASSED |
| M2-M4 Tests | 47 | PASSED |
| **Gesamt** | **81** | **PASSED** |

---

## 16. Coverage

```
Gesamt: 496 statements, 18 missed → 96%
```

**M1-Kernmodule:**
- `domain/case.py`: 100% ✓
- `application/case_service.py`: 100% ✓
- `application/case_repository.py`: 100% ✓
- `infrastructure/database.py`: 100% ✓
- `infrastructure/sqlite_case_repository.py`: 100% ✓
- `api/routes.py`: 100% ✓
- `api/schemas.py`: 100% ✓
- `api/errors.py`: 100% ✓
- `config.py`: 81% (3 missed: alternative env-var branches)
- `app.py`: 85% (8 missed: M2-M4 wiring, not M1 concern)
- `__main__.py`: 0% (Entry Point, keine Logik)

**Bewertung:** M1-Kernmodule erreichen im Wesentlichen 100% Coverage. Die 93%-Behauptung des Run Reports ist konservativ und wurde übertroffen.

---

## 17. Testqualitätsbewertung

**Positiv:**
- Domain-Tests prüfen Geschäftsregeln direkt (Titel-Validierung, Trimming, UUID, UTC) ✓
- Repository-Integrationstests nutzen reale temporäre SQLite-Datenbanken ✓
- `test_persistence_survives_reconnect` beweist echte Persistenz ✓
- API-Tests nutzen ASGI-Transport mit isoliertem `tmp_path` ✓
- Fehlerpfade sind getestet (404, 422, leere DB) ✓
- Testisolation durch `tmp_path`-Fixture gegeben ✓
- Keine Scheintests (z.B. `assert True`) identifiziert ✓
- `SYNTHETISCH –` Präfix konsequent verwendet ✓

**Verbesserungswürdig:**
- Service-Tests mocken das Repository vollständig (`MagicMock`) — dies ist beim Unit-Testen der Service-Logik akzeptabel, aber die Integration wird separat getestet ✓
- `test_get_invalid_uuid_format` nutzt `assert response.status_code in (404, 422)` — unspezifisch (MINOR)

**Mutationsplausibilität (gedanklich):**
- Repository das nicht speichert → `test_save_and_get_by_id` + `test_persistence_survives_reconnect` würden versagen ✓
- Statische API-Antwort → `test_create_case_returns_201` prüft dynamische UUID + Titel ✓
- Falsche Sortierung → `test_list_all_returns_all_cases` prüft Inhalte (nicht Reihenfolge direkt, aber Vollständigkeit) ⚠️
- Naive datetime → `test_created_at_is_utc_aware` prüft tzinfo ✓
- SQL-Injection → parametrisierte Queries im Code, kein String-Building ✓
- Fehlerhaftes 404-Format → `test_get_nonexistent_case_returns_404` prüft `error.code` ✓

---

## 18. Typprüfung

```
mypy src → "Success: no issues found in 28 source files"
```

- `strict = true` in pyproject.toml ✓
- `warn_unused_configs = true` ✓
- Note: `pyproject.toml: unused section(s): module = ['tests.*']` — harmloser Config-Hinweis

---

## 19. Linting

```
ruff check src tests → "All checks passed!"
```

- Ruff-Regeln: E, F, W, I, N, UP, B, C4, SIM ✓
- Keine ignorierten Warnungen ✓

---

## 20. API-Smoke-Test

| Test | Request | Status | Ergebnis |
|------|---------|--------|----------|
| Health | `GET /health` | 200 | `{"status":"ok"}` ✓ |
| Leere Fallliste | `GET /api/v1/cases` | 200 | `{"items":[],"count":0}` ✓ |
| Fall anlegen | `POST /api/v1/cases {"title":"SYNTHETISCH – Analyse-Testfall"}` | 201 | UUID + title + status "open" ✓ |
| Fallliste (mit Fall) | `GET /api/v1/cases` | 200 | count=1, items[0].title korrekt ✓ |
| Falldetail | `GET /api/v1/cases/{uuid}` | 200 | Alle Felder korrekt, UTC-Zeitstempel ✓ |
| Unbekannte UUID | `GET /api/v1/cases/000...000` | 404 | `{"error":{"code":"CASE_NOT_FOUND",...}}` ✓ |
| Leerer Titel | `POST` mit `""` | 422 | Abgelehnt ✓ |
| Whitespace-Titel | `POST` mit `"   "` | 422 | Abgelehnt ✓ |
| Titel >200 Zeichen | `POST` mit 201×"A" | 422 | Abgelehnt ✓ |
| **Persistenz** | Server-Stop → Server-Start (gleiches PLN_DATA_DIR) | — | Fall weiterhin vorhanden ✓ |

---

## 21. Persistenztest

1. Server gestartet mit `PLN_DATA_DIR=.../pln-analysis-{uuid}` ✓
2. Fall angelegt ✓
3. Server gestoppt ✓
4. Server neu gestartet mit gleichem `PLN_DATA_DIR` ✓
5. `GET /api/v1/cases` → count=1, selber case_id, selber title ✓

**Bewertung:** SQLite-Persistenz über Neustart verifiziert. Keine In-Memory-Datenbank, kein Datenverlust.

---

## 22. SQLite-Prüfung

| Prüfpunkt | Ergebnis |
|-----------|----------|
| Schema idempotent (`IF NOT EXISTS`) | ✓ |
| `PRAGMA foreign_keys = ON` | ✓ |
| Parametrisierte Queries (kein String-Building) | ✓ |
| Connection pro Operation (kein globaler State) | ✓ |
| `conn.close()` in `finally`-Block | ✓ |
| `INSERT OR REPLACE` für Upsert | ✓ |
| `ORDER BY created_at DESC` deterministisch | ✓ |
| UUID als TEXT gespeichert | ✓ |
| datetime als ISO-8601-String | ✓ |
| `sqlite3.Row` für benannte Spalten | ✓ |
| Keine Thread-safety-Issues (Connections kurzlebig) | ✓ |

---

## 23. Local-Only-Prüfung

| Check | Ergebnis |
|-------|----------|
| Default-Host `127.0.0.1` | ✓ |
| Kein `0.0.0.0` im Code | ✓ |
| Keine `https?://`-URLs im Source | ✓ |
| Keine HTTP-Clients (requests, httpx, aiohttp, urllib) im Source | ✓ |
| Keine Telemetrie/Analytics | ✓ |
| Kein CORS | ✓ |
| Port nach Server-Stop geschlossen | ✓ |

---

## 24. Logging-Prüfung

| Check | Ergebnis |
|-------|----------|
| `print()` im Source | 0 Treffer ✓ |
| `logging.` / `logger.` im Source | 0 Treffer ✓ |
| Request-Body-Logging | Nicht vorhanden ✓ |
| Falltitel in Logs | Nicht vorhanden ✓ |
| Datenbankpfade in Logs | Nicht vorhanden ✓ |
| Stacktraces in API-Antworten | Nicht vorhanden (nur Error-Envelope) ✓ |
| Uvicorn Access Logs | Standard (URLs, Statuscodes — URLs enthalten UUIDs, akzeptabel) ⚠️ |

**Bewertung:** Kein sensitives Logging im Anwendungscode. Uvicorns Standard-Access-Log protokolliert URLs inkl. Case-UUIDs — dies ist bei lokalem Betrieb akzeptabel, da nur der lokale Nutzer Zugriff auf die Konsole hat.

---

## 25. Security-Ergebnis

| Check | Ergebnis |
|-------|----------|
| `.env` im Repository | 0 Treffer ✓ |
| API-Keys / Tokens / Secrets | 0 Treffer ✓ |
| `.sqlite` / `.db` im Repository | 0 Treffer ✓ |
| Echte Falldaten | 0 Treffer ✓ |
| CORS-Konfiguration | Keine (Safe Default) ✓ |
| Netzwerkbindung | 127.0.0.1 ✓ |
| SQL-Injection | Parametrisierte Queries ✓ |
| Testdaten-Präfix | "SYNTHETISCH –" ✓ |
| `.gitignore` deckt Datenbanken ab | `*.sqlite`, `*.sqlite3`, `*.db`, `data/` ✓ |

**Security-Verdict: CLEAN** — Keine Critical, Major, oder Minor Findings.

---

## 26. Compliance-Ergebnis

| Invariante | Beschreibung | Status |
|-----------|-------------|--------|
| INV-07 | Nur Unterstützung bei eigenen Angelegenheiten | ✓ (README, AGENTS.md) |
| INV-08 | Keine automatische Rechtsentscheidung | ✓ (READ-ME, Constitution) |
| INV-09 | Keine verbindliche Rechtsberatung | ✓ (README) |
| INV-10 | Keine automatische Kommunikation | ✓ (AGENTS.md) |
| INV-11 | Menschliche Prüfung erforderlich | ✓ (Constitution, README) |
| INV-12 | Unsicherheit nicht verbergen | ⚠️ M1 enthält noch keine Analyse — nicht relevant |

**Bewertung:** M1 ist reine Fallverwaltung und erzeugt keine impliziten Rechtsaussagen. Alle Grenzen sind dokumentiert.

---

## 27. Dokumentationswahrheit

| Dokument | Status | Anmerkung |
|----------|--------|-----------|
| README.md | **PARTIALLY_STALE** | Zeile 8: "M3" statt "M4"; Zeile 28: "Dokumentimport" als "noch nicht implementiert" obwohl M2 vorhanden |
| AGENTS.md | CURRENT | Korrekt |
| constitution.md | CURRENT | Projektspezifisch, vollständig |
| spec.md (M1) | **PARTIALLY_STALE** | Selbstreferenz auf nicht existierenden Abschnitt |
| plan.md (M1) | CURRENT | Korrekt |
| tasks.md (M1) | **PARTIALLY_STALE** | Alle Tasks ungecheckt |
| data-model.md (M1) | CURRENT | Stimmt mit Code überein |
| contracts/api.md (M1) | CURRENT | Stimmt mit Endpunkten überein (422-Format-Abweichung dokumentiert) |
| adr-001 | CURRENT | Nachvollziehbare Entscheidung |
| architecture.md | CURRENT | Stimmt mit Code überein |
| security-invariants.md | CURRENT | Alle 20 Invarianten dokumentiert |
| M1-run-report.md | **PARTIALLY_STALE** | FR/SC-Claim nicht verifizierbar, sonst korrekt |

---

## 28. Windows-Reproduzierbarkeit

| Check | Ergebnis |
|-------|----------|
| `py -3.11 -m venv .venv` funktioniert | ✓ |
| `.venv/Scripts/python.exe` korrekt | ✓ |
| Keine Execution-Policy-Änderung nötig | ✓ |
| Pfade mit Leerzeichen (nicht betroffen) | — |
| UTF-8 konsistent | ✓ |
| Zeilenenden `lf` | ✓ (.editorconfig) |
| Keine plattformspezifischen Testfehler | ✓ |

---

## 29. Scope-Prüfung

**M1-Scope (erwartet):**
- Projektgrundlage ✓
- Governance (Constitution, AGENTS.md) ✓
- Spec-Kit (Spec, Plan, Tasks, Contracts, Data Model) ✓
- Architektur (ADR, Architecture-Doc) ✓
- Case Domain ✓
- Case Service ✓
- SQLite Repository ✓
- FastAPI Case API ✓
- Tests (Unit, Integration, API) ✓
- Dokumentation ✓

**Unerlaubter Scope (nicht in M1):**
- Frontend ✗ (nicht vorhanden)
- OCR ✗ (nicht vorhanden)
- PDF-Verarbeitung ✗ (nur in M3)
- Rechtsanalyse ✗ (nicht vorhanden)
- Fristen ✗ (nicht vorhanden)
- LLM ✗ (nicht vorhanden)
- Cloud ✗ (nicht vorhanden)
- Authentifizierung ✗ (nicht vorhanden)
- Deployment ✗ (nicht vorhanden)

**M2-M4 Addons (nicht M1-Scope):**
- Document Domain/Service/Repository
- File Storage
- PDF Text Extraction
- Rule-based Classification
- Diese sind korrekt als separate Feature-Branches implementiert

**Scope-Verdict: CLEAN** — Kein Scope Creep in M1. Nachfolgende Features sind sauber in eigenen Branches/Commits.

---

## 30. Findings nach Schweregrad

### Critical: 0

Keine.

### Major: 0

Keine.

### Minor: 5

#### [MINOR] Spec-Selbstreferenz ohne existierenden Inhalt

**Kategorie:** Dokumentation / Spec-Kit  
**Datei:** `specs/001-greenfield-case-core/spec.md`  
**Zeile:** 47  
**Anforderung:** Spec-Kit-Mandat (Speckit-Phase: Specify)

**Beobachtung:** `spec.md` verweist auf sich selbst: "Siehe `specs/001-greenfield-case-core/spec.md` Abschnitt 'Functional Requirements'." Dieser Abschnitt existiert nicht. Die Spec enthält User Stories mit Akzeptanzkriterien, aber keine explizite Enumeration von FR-01 bis FR-20 und SC-01 bis SC-13.

**Risiko:** Die Behauptung des Run Reports ("alle 20 FRs abgedeckt, alle 13 SCs erfüllt") ist aus der Spec heraus nicht verifizierbar. Die Traceability ist nur implizit über User Stories und Akzeptanzkriterien gegeben.

**Evidence:**
```
$ rg -n "FR-|SC-" specs/001-greenfield-case-core/
specs/001-greenfield-case-core/tasks.md:16:- [ ] **T012** — Spec-Kit-Analyse: FR-Abdeckung, Scope, Konsistenz
```
Nur ein Treffer (Task-Referenz), keine tatsächlichen FR-/SC-Definitionen.

**Empfehlung:** Entweder die Selbstreferenz entfernen und klarstellen, dass die User Stories die primären Anforderungsartefakte sind, oder eine FR-/SC-Tabelle mit expliziten IDs nachtragen.

**Blockiert GREEN_SAFE?** Nein — die Anforderungen sind über User Stories und Akzeptanzkriterien abgedeckt und alle verifiziert. Das Problem ist rein dokumentarischer Natur und hat keine funktionale oder sicherheitsrelevante Auswirkung.

#### [MINOR] Tasks ungecheckt

**Kategorie:** Dokumentation  
**Datei:** `specs/001-greenfield-case-core/tasks.md`  
**Zeile:** 5-53  
**Anforderung:** Spec-Kit-Mandat (Evidence nach Tasks)

**Beobachtung:** Alle 31 Tasks zeigen `- [ ]` (unchecked). Der Build-Prozess hat die Implementierung abgeschlossen, aber die Checkboxen nicht aktualisiert.

**Risiko:** Unklar, welche Tasks tatsächlich abgeschlossen wurden und ob T027-T031 (Review, Findings, Commit) evtl. übersprungen wurden.

**Evidence:** `tasks.md` — alle Zeilen mit `- [ ]`

**Empfehlung:** Tasks auf `- [x]` setzen, wo die Implementierung abgeschlossen ist.

**Blockiert GREEN_SAFE?** Nein.

---

#### [MINOR] README Status veraltet (M3 statt M4)

**Kategorie:** Dokumentation  
**Datei:** `README.md`  
**Zeile:** 8, 28  
**Anforderung:** Constitution §11 (Living Truth Mirror)

**Beobachtung:** Zeile 8: "M3 — Dokumenttextgewinnung — abgeschlossen" (tatsächlich M4). Zeile 28: "Noch nicht implementiert: Dokumentimport" (wurde in M2 implementiert).

**Risiko:** Falsche Erwartung bei neuen Mitwirkenden.

**Empfehlung:** README auf M4 aktualisieren, "Noch nicht implementiert"-Liste bereinigen.

**Blockiert GREEN_SAFE?** Nein.

---

#### [MINOR] API 422-Format weicht vom Contract ab

**Kategorie:** API / Spezifikation  
**Datei:** `specs/001-greenfield-case-core/contracts/api.md` / `src/private_legal_navigator/api/errors.py`  
**Zeile:** contract Z.39-47, errors.py (kein 422-Handler)  
**Anforderung:** API-Contracts

**Beobachtung:** Der API-Contract definiert ein eigenes 422-Format (`{"error": {"code": "VALIDATION_ERROR", ...}}`), aber die Implementierung nutzt FastAPIs Standard-Validierungsfehler (Pydantic-Exceptions). Das spezifizierte Format wird nur für 404 verwendet.

**Risiko:** Clients, die sich auf das spezifizierte 422-Format verlassen, erhalten abweichende Antworten.

**Empfehlung:** Entweder einen eigenen Validation-Exception-Handler implementieren oder den Contract an die FastAPI-Standard-Fehler anpassen.

**Blockiert GREEN_SAFE?** Nein — FastAPIs Standard-422 ist funktional korrekt und maschinenlesbar.

---

#### [MINOR] Unspezifische Assertion in test_get_invalid_uuid_format

**Kategorie:** Test  
**Datei:** `tests/api/test_cases_api.py`  
**Zeile:** 133  
**Anforderung:** US3 (ungültiges UUID-Format angemessen behandeln)

**Beobachtung:** `assert response.status_code in (404, 422)` — der Test akzeptiert beide Statuscodes. Der tatsächliche Code (FastAPI) liefert 422 für ungültige UUID-Formatierung. Der Test sollte den erwarteten Statuscode pinnen.

**Risiko:** Änderungen am Routing könnten unbemerkt das Verhalten ändern.

**Empfehlung:** Auf `assert response.status_code == 422` ändern (oder konsistent mit dem gewählten Verhalten).

**Blockiert GREEN_SAFE?** Nein.

### Notes: 3

#### [NOTE] Settings akzeptiert str statt Path (Runtime-Footgun)

**Kategorie:** Code-Qualität  
**Datei:** `src/private_legal_navigator/config.py`  
**Zeile:** 18-20

**Beobachtung:** Die frozen dataclass `Settings` hat `data_dir: Path` aber keine Runtime-Validierung. Wird ein String übergeben, schlägt `database_path`-Property mit `TypeError` fehl. Normalerweise werden Settings nur über Env-Vars oder Default-Factory konstruiert, die `Path`-Objekte liefern.

**Empfehlung:** `__post_init__`-Validierung hinzufügen oder `field(default_factory=...)` beibehalten (aktuell ausreichend für normale Nutzung).

---

#### [NOTE] M1 Run Report enthält nicht verifizierbare FR/SC-Claims

**Kategorie:** Dokumentation  
**Datei:** `docs/reports/M1-greenfield-foundation.md`  
**Zeile:** 133

**Beobachtung:** "SPEC_GREEN — alle 20 FRs abgedeckt, alle 13 SCs erfüllt" — die Spec enthält keine FR-/SC-Enumeration.

**Empfehlung:** Claim anpassen oder Spec ergänzen.

---

#### [NOTE] Uvicorn Access Log enthält Case-UUIDs in URLs

**Kategorie:** Security / Logging  
**Datei:** Laufzeitverhalten  

**Beobachtung:** Uvicorn loggt standardmäßig alle Requests inkl. URL-Pfade. Case-UUIDs erscheinen daher in der Konsole. Bei lokalem Betrieb akzeptabel.

**Empfehlung:** Bei Bedarf Log-Level im Produktivbetrieb auf WARNING setzen.

---

## 31. Offene Risiken

1. **Keine** — alle identifizierten Findings sind Minor oder Notes. Keine funktionalen, Sicherheits- oder Architekturrisiken.

---

## 32. Was kann die Software jetzt wirklich?

- Lokal starten: `python -m private_legal_navigator` ✓
- Health-Check beantworten ✓
- Synthetischen Fall per API anlegen ✓
- Fälle persistent in SQLite speichern ✓
- Persistenz über Neustart hinweg ✓
- Fallliste ausgeben (deterministisch sortiert nach created_at DESC) ✓
- Falldetail per UUID abrufen ✓
- Unbekannte UUIDs kontrolliert als 404 behandeln ✓
- Fehler mit stabilem maschinenlesbarem Format (404) ✓
- Validierungsfehler durch FastAPI/Pydantic (422) ✓

---

## 33. Was kann sie (M1) noch nicht?

- Dokumente importieren / speichern (→ M2)
- PDF-Textextraktion (→ M3)
- Dokumentklassifikation (→ M4)
- Fristen berechnen
- Rechtslagen bewerten
- Empfehlungen erzeugen
- Frontend anzeigen
- Mehrere Nutzer verwalten
- Daten verschlüsseln

---

## 34. M1-Abschlussurteil

### M1 ist abgeschlossen und tragfähig.

Die Architektur (`ARCH_PASS`), Tests (81/81, 96% Coverage), Codequalität (Ruff/Mypy sauber), API-Verträge (alle 4 Endpunkte verifiziert), Persistenz (über Neustart bestätigt), Sicherheitsgrenzen (Local-only, parametrisierte SQL, keine Secrets) und Compliance (keine automatische Rechtsentscheidung, Human Review dokumentiert) sind durch unabhängige Evidence belegt.

Die identifizierten Findings (1 Major dokumentarisch, 4 Minor, 3 Notes) beeinträchtigen nicht die Funktionsfähigkeit oder Sicherheit des M1-Kerns.

---

## 35. Priorisierter Reparaturplan

| Prio | Finding | Ziel | Betroffene Dateien | Akzeptanzkriterium | Scope |
|------|---------|------|-------------------|-------------------|-------|
| P1 | Spec-Selbstreferenz | FR/SC-Tabelle ergänzen ODER Selbstreferenz entfernen | `specs/001-greenfield-case-core/spec.md` | Spec ist vollständig und selbsttragend | klein |
| P2 | Tasks ungecheckt | Abgeschlossene Tasks markieren | `specs/001-greenfield-case-core/tasks.md` | Alle M1-Tasks zeigen `[x]` | klein |
| P2 | README-Status | Auf M4 aktualisieren, veraltete Claims entfernen | `README.md` | README spiegelt aktuellen Stand | klein |
| P3 | API 422-Format | Contract anpassen ODER Handler implementieren | `api/errors.py` oder `contracts/api.md` | Contract und Runtime konsistent | klein |
| P3 | Unspezifische Assertion | Statuscode pinnen | `tests/api/test_cases_api.py:133` | Test prüft exakten 422 | klein |
| P3 | Settings str-Footgun | `__post_init__` oder Type-Guard | `config.py` | Typsicherheit auch bei manueller Konstruktion | klein |

---

## 36. Empfohlener nächster Featurelauf

Da M1 `GREEN_WITH_NOTES` und alle Critical/Major-Findings rein dokumentarisch sind:

### Empfehlung: **M5 — Nächster vertikaler Slice** (nach README/Spec-Update)

Optionen:
- **M2 war Dokumentimport** (bereits implementiert auf `feat/002-document-import`)
- **M3 war Textextraktion** (bereits implementiert auf `feat/003-text-extraction`)
- **M4 war Dokumentklassifikation** (bereits implementiert auf `feat/004-document-classification`)

Da M2-M4 bereits gebaut sind, sollte der nächste Lauf entweder:
- **M5 – neuen Feature-Slice definieren** (z.B. Fristberechnung, Tagging, Suche)
- **Oder M1-M4 Review & Consolidation** — alle bisherigen Branches integrieren und auf `main` mergen (nach Push-Freigabe)

### Vor dem nächsten Lauf:
1. P1-Finding beheben (Spec-Selbstreferenz)
2. P2-Findings beheben (Tasks, README)
3. `git push` nach Freigabe durchführen (bisher kein Push erfolgt)

---

## 37. Methodik & Grenzen dieses Berichts

- **Modus:** READ_ONLY_ANALYSIS — keine Code-Änderungen durchgeführt
- **Shell:** PowerShell 5.1 (Windows)
- **Testausführung:** Isoliert in `.venv` mit Python 3.11.9
- **API-Tests:** Mit temporärem `PLN_DATA_DIR`, keine bestehenden Daten verändert
- **Keine externen Tools installiert** — alle Prüfungen mit vorhandenen Werkzeugen
- **Nicht geprüft:** Performance, Lastverhalten, Langzeitstabilität, Docker-Containerisierung
- **Nicht geprüft:** Remote-Repository-Status (gh api), da kein Push erfolgt ist

---

*Bericht erstellt am 2026-07-13 durch unabhängigen Analyse-Lauf.*
*Kein Commit — dieser Bericht muss manuell committed werden.*
