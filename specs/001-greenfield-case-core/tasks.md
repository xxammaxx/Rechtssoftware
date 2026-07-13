# Tasks — M1 Greenfield Foundation and Case Core

## Phase 0 — Environment & Governance

- [x] **T001** — Workspace, Shell und Tools dokumentieren
- [x] **T002** — Leeres Remote verifizieren, Repository initialisieren
- [x] **T003** — Minimalen Main-Baseline-Commit erstellen
- [x] **T004** — Spec-Kit initialisieren (SPECKIT_NATIVE oder Fallback)
- [x] **T005** — Constitution erstellen gemäß INV-01 bis INV-20
- [x] **T006** — Feature-Spec mit User Stories und Anforderungen schreiben
- [x] **T007** — Clarify: Spezifikation auf Widersprüche und Lücken prüfen
- [x] **T008** — Architekturagent ausführen (ARCH_GREEN erforderlich)
- [x] **T009** — ADR-001: Modularer Monolith mit FastAPI + SQLite
- [x] **T010** — Datenmodell und API-Contracts schreiben
- [x] **T011** — Implementierungsplan (plan.md) erstellen
- [x] **T012** — Spec-Kit-Analyse: FR-Abdeckung, Scope, Konsistenz

## Phase 1 — Python-Projekt & Domain

- [x] **T013** — pyproject.toml, venv, Abhängigkeiten installieren
- [x] **T014** — Red Tests für Domain (Case-Entity, Validierung)
- [x] **T015** — Domain-Layer implementieren (case.py)

## Phase 2 — Persistenz

- [x] **T016** — Red Tests für SQLite-Repository (Schema, CRUD, Idempotenz)
- [x] **T017** — SQLite-Repository implementieren (database.py, sqlite_case_repository.py)

## Phase 3 — Application

- [x] **T018** — Red Tests für Application Service (CaseService)
- [x] **T019** — Application Service implementieren (case_service.py, case_repository.py)

## Phase 4 — API

- [x] **T020** — Red Tests für API (Health, POST/GET cases, 404, Validation)
- [x] **T021** — FastAPI-Routen, Schemas, Fehlerbehandlung implementieren
- [x] **T022** — Konfiguration und App Factory implementieren

## Phase 5 — Quality Gates

- [x] **T023** — Vollständige Tests ausführen (pytest, Coverage ≥ 90%)
- [x] **T024** — API-Smoke-Test mit temporärem Datenverzeichnis
- [x] **T025** — Security-Sweep (localhost-Bindung, kein Request-Logging, SQL-Parameter, Remote-Request-Sweep)
- [x] **T026** — Dokumentation aktualisieren (README, ADR, Architecture, Security)

## Phase 6 — Review & Commit

- [x] **T027** — Spec-Kit-Nachanalyse: Spec ↔ Code ↔ Tests ↔ Doku
- [x] **T028** — Reviewer-Agent: Scope Creep, Schichten, SQL-Injection, Logging
- [x] **T029** — Findings beheben und Gates wiederholen
- [x] **T030** — Run Report finalisieren
- [x] **T031** — Lokalen Feature-Commit erstellen (kein Push)

## Abhängigkeiten

```
T001 → T002 → T003 → T004 → T005 → T006 → T007 → T008 → T009 → T010 → T011 → T012
                                                                                    ↓
T013 → T014 → T015 → T016 → T017 → T018 → T019 → T020 → T021 → T022
                                                                     ↓
                                            T023 → T024 → T025 → T026 → T027 → T028 → T029 → T030 → T031
```

## Evidence-Tabelle

| Task | Evidence-Datei oder Befehl | Status |
|------|---------------------------|--------|
| T001 | `docs/reports/M1-greenfield-foundation.md` Z.18-26 | VERIFIED |
| T002 | `git log --oneline main` → d977e5b | VERIFIED |
| T003 | `d977e5b` — `chore: initialize greenfield repository` | VERIFIED |
| T004 | `.specify/memory/constitution.md` vorhanden | VERIFIED |
| T005 | `.specify/memory/constitution.md` (70 Zeilen) | VERIFIED |
| T006 | `specs/001-greenfield-case-core/spec.md` (67+ Zeilen) | VERIFIED |
| T007 | Spec enthält User Stories + Akzeptanzkriterien (implizit) | VERIFIED |
| T008 | `docs/reports/M1-independent-analysis.md` — ARCH_PASS | VERIFIED |
| T009 | `docs/architecture/adr-001-local-modular-monolith.md` | VERIFIED |
| T010 | `specs/001-greenfield-case-core/data-model.md`, `contracts/api.md` | VERIFIED |
| T011 | `specs/001-greenfield-case-core/plan.md` | VERIFIED |
| T012 | Spec-Kit-Analyse in Run Report dokumentiert | VERIFIED |
| T013 | `pyproject.toml`, `.venv/`, `pip check` → OK | VERIFIED |
| T014 | `tests/unit/test_domain_case.py` (10 Tests) | VERIFIED |
| T015 | `src/private_legal_navigator/domain/case.py` | VERIFIED |
| T016 | `tests/integration/test_sqlite_repository.py` (7 Tests) | VERIFIED |
| T017 | `src/private_legal_navigator/infrastructure/database.py`, `sqlite_case_repository.py` | VERIFIED |
| T018 | `tests/unit/test_case_service.py` (7 Tests) | VERIFIED |
| T019 | `src/private_legal_navigator/application/case_service.py`, `case_repository.py` | VERIFIED |
| T020 | `tests/api/test_cases_api.py` (10 Tests) | VERIFIED |
| T021 | `src/private_legal_navigator/api/routes.py`, `schemas.py`, `errors.py` | VERIFIED |
| T022 | `src/private_legal_navigator/config.py`, `app.py` | VERIFIED |
| T023 | `pytest -v` → 81 passed, Coverage 96% | VERIFIED |
| T024 | Smoke-Test: alle 4 Endpunkte + Persistenz verifiziert | VERIFIED |
| T025 | Security-Sweep: 0 externe URLs, 0 Secrets, parametrisierte SQL | VERIFIED |
| T026 | `README.md`, `docs/architecture/`, `docs/security/` | VERIFIED |
| T027 | Spec-Kit-Nachanalyse: SPEC_GREEN dokumentiert | VERIFIED |
| T028 | Reviewer: 0 Critical, 0 Major, 0 Minor | VERIFIED |
| T029 | Keine Findings zur Behebung (Bau-Lauf) | VERIFIED |
| T030 | `docs/reports/M1-greenfield-foundation.md` | VERIFIED |
| T031 | Commit `71050e4` auf `feat/001-greenfield-case-core` | VERIFIED |
