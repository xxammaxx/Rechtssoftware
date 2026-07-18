# Tasks — M1 Greenfield Foundation and Case Core

## Phase 1 — Setup

- [X] T001 Create pyproject.toml with dependencies (FastAPI, uvicorn, pytest, httpx, ruff, mypy)
- [X] T002 [P] Create project directory structure per plan.md (domain/, application/, infrastructure/, api/, tests/unit, tests/integration, tests/api)

## Phase 2 — Foundational (cross-cutting, required by all stories)

- [X] T003 Implement config module (PLN_DATA_DIR, PLN_HOST, PLN_PORT) in src/private_legal_navigator/config.py
- [X] T004 [P] Define repository port (Protocol) in src/private_legal_navigator/application/case_repository.py
- [X] T005 [P] Define error classes and handlers (VALIDATION_ERROR, CASE_NOT_FOUND, DATABASE_ERROR, INTERNAL_ERROR) in src/private_legal_navigator/api/errors.py
- [X] T006 [P] Define Pydantic API schemas (CaseResponse, CaseCreate, CaseListResponse, ErrorResponse) in src/private_legal_navigator/api/schemas.py
- [X] T007 Implement database connection + schema initialization in src/private_legal_navigator/infrastructure/database.py
- [X] T008 Implement app factory with lifespan (init DB on startup, close on shutdown) in src/private_legal_navigator/app.py
- [X] T009 Implement entry point (uvicorn.run) in src/private_legal_navigator/__main__.py

## Phase 3 — [US1] Fall anlegen (P1)

- [X] T010 [US1] Write Red Tests for Case domain entity (validation, title trimming, empty title rejection, title > 200 chars rejection, UUID generation, status default) in tests/unit/test_case.py
- [X] T011 [US1] Implement Case domain entity + validation in src/private_legal_navigator/domain/case.py
- [X] T012 [US1] Write Red Tests for SQLite repository CRUD in tests/integration/test_sqlite_case_repository.py
- [X] T013 [US1] Implement SQLite repository (create, list, get_by_id + schema init + indexes) in src/private_legal_navigator/infrastructure/sqlite_case_repository.py
- [X] T014 [US1] Write Red Tests for CaseService (create case with validation, empty title rejection, 200-char limit) in tests/unit/test_case_service.py
- [X] T015 [US1] Implement CaseService in src/private_legal_navigator/application/case_service.py
- [X] T016 [P] [US1] Write Red Tests for POST /api/v1/cases (201 Created, 422 Validation Error, empty title, title > 200 chars, trimmed title) in tests/api/test_routes.py
- [X] T017 [US1] Implement POST /api/v1/cases endpoint in src/private_legal_navigator/api/routes.py

## Phase 4 — [US2] Fälle auflisten (P1)

- [X] T018 [US2] Write Red Tests for GET /api/v1/cases (200 with items+count, empty list, created_at DESC sort order) in tests/api/test_routes.py
- [X] T019 [US2] Implement GET /api/v1/cases endpoint (sorted by created_at DESC, with items+count response) in src/private_legal_navigator/api/routes.py

## Phase 5 — [US3] Falldetail abrufen (P1)

- [X] T020 [US3] Write Red Tests for GET /api/v1/cases/{case_id} (200 with case, 404 unknown UUID, 422 invalid UUID format) in tests/api/test_routes.py
- [X] T021 [US3] Implement GET /api/v1/cases/{case_id} endpoint in src/private_legal_navigator/api/routes.py

## Phase 6 — Health Check & Integration

- [X] T022 [P] Write Red Tests for GET /health (200 with {"status": "ok"}) in tests/api/test_routes.py
- [X] T023 Implement GET /health endpoint in src/private_legal_navigator/api/routes.py

## Phase 7 — Quality Gates & Polish

- [X] T024 Run full test suite: pytest with Coverage ≥ 90%
- [X] T025 [P] API smoke test with temporary data directory (start app, hit /health, POST case, GET cases, GET case by id)
- [X] T026 [P] Security sweep (localhost-only binding, no PII in logs, SQL parameterization, no external requests)
- [X] T027 Update documentation (README, ADR-001, architecture.md, privacy-and-security-invariants.md)
- [X] T028 Spec-Kit post-analysis: Spec ↔ Code ↔ Tests ↔ Docs alignment check
- [X] T029 Reviewer-agent review: scope creep, layer separation, error handling, logging
- [X] T030 Run Report finalisieren
- [ ] T031 Lokalen Feature-Commit erstellen (kein Push) — **ausstehend: Benutzerfreigabe erforderlich**

## Abhängigkeiten

```
T001 ──→ T002
  │
  ├──→ T003 ──→ T007 ──→ T013
  ├──→ T004 ──→ T015
  ├──→ T005 ──→ T017, T019, T021
  └──→ T006 ──→ T017, T019, T021
                    │
T008 ←── T009 ←─────┤
  │
  └──→ Phase 3 [US1]: T010 → T011 → T012 → T013 → T014 → T015 → T016 → T017
                                                                          │
                                    Phase 4 [US2]: T018 ──────────────→ T019
                                                                          │
                                    Phase 5 [US3]: T020 ──────────────→ T021
                                                                          │
                                    Phase 6:     T022 ──────────────→ T023
                                                                          │
                                    Phase 7:     T024 → T025 → T026 → T027 → T028 → T029 → T030 → T031
```

## Parallele Ausführung

| Phase | Parallel Tasks | Bedingung |
|-------|---------------|-----------|
| 1 | T002 | Nach T001 |
| 2 | T004, T005, T006 gleichzeitig | Nach T001 |
| 2 | T003 → T007 → T013 (sequentiell) | Nach T001 |
| 3 | T010 → T011 → T012 → T013 → T014 → T015 → T016 → T017 (streng sequentiell, TDD) | Nach Phase 2 |
| 4 | T018 → T019 | Nach Phase 3 |
| 5 | T020 → T021 | Nach Phase 3 |
| 6 | T022 → T023 | Nach Phase 3 |
| 7 | T025, T026 gleichzeitig | Nach T024 |

## Implementierungsstrategie

1. **MVP (Phase 1-3)**: Fall anlegen – der gesamte vertikale Slice von API über Service, Repository bis zur SQLite-Datenbank. Nach Phase 3 kann ein Fall über die API angelegt werden.
2. **Incremental (Phase 4-5)**: Fälle auflisten und Detail abrufen bauen auf der bestehenden Repository/Service-Infrastruktur auf – nur neue API-Endpunkte + Tests.
3. **Integration (Phase 6)**: Health-Check-Endpunkt.
4. **Quality (Phase 7)**: Tests, Coverage, Security, Dokumentation.

## MVP Scope

**Phase 1 + 2 + 3 = MVP** — Nach Abschluss von T017 kann der Nutzer:
- Einen Fall mit Titel über POST /api/v1/cases anlegen
- Titel-Validierung (leer/zu lang) abgefangen
- Fall in SQLite persistiert
- Health-Check über GET /health
- Coverage ≥ 90% auf MVP-Code
