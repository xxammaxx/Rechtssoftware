# Tasks — M1 Greenfield Foundation and Case Core

## Phase 0 — Environment & Governance

- [ ] **T001** — Workspace, Shell und Tools dokumentieren
- [ ] **T002** — Leeres Remote verifizieren, Repository initialisieren
- [ ] **T003** — Minimalen Main-Baseline-Commit erstellen
- [ ] **T004** — Spec-Kit initialisieren (SPECKIT_NATIVE oder Fallback)
- [ ] **T005** — Constitution erstellen gemäß INV-01 bis INV-20
- [ ] **T006** — Feature-Spec mit User Stories und Anforderungen schreiben
- [ ] **T007** — Clarify: Spezifikation auf Widersprüche und Lücken prüfen
- [ ] **T008** — Architekturagent ausführen (ARCH_GREEN erforderlich)
- [ ] **T009** — ADR-001: Modularer Monolith mit FastAPI + SQLite
- [ ] **T010** — Datenmodell und API-Contracts schreiben
- [ ] **T011** — Implementierungsplan (plan.md) erstellen
- [ ] **T012** — Spec-Kit-Analyse: FR-Abdeckung, Scope, Konsistenz

## Phase 1 — Python-Projekt & Domain

- [ ] **T013** — pyproject.toml, venv, Abhängigkeiten installieren
- [ ] **T014** — Red Tests für Domain (Case-Entity, Validierung)
- [ ] **T015** — Domain-Layer implementieren (case.py)

## Phase 2 — Persistenz

- [ ] **T016** — Red Tests für SQLite-Repository (Schema, CRUD, Idempotenz)
- [ ] **T017** — SQLite-Repository implementieren (database.py, sqlite_case_repository.py)

## Phase 3 — Application

- [ ] **T018** — Red Tests für Application Service (CaseService)
- [ ] **T019** — Application Service implementieren (case_service.py, case_repository.py)

## Phase 4 — API

- [ ] **T020** — Red Tests für API (Health, POST/GET cases, 404, Validation)
- [ ] **T021** — FastAPI-Routen, Schemas, Fehlerbehandlung implementieren
- [ ] **T022** — Konfiguration und App Factory implementieren

## Phase 5 — Quality Gates

- [ ] **T023** — Vollständige Tests ausführen (pytest, Coverage ≥ 90%)
- [ ] **T024** — API-Smoke-Test mit temporärem Datenverzeichnis
- [ ] **T025** — Security-Sweep (localhost-Bindung, kein Request-Logging, SQL-Parameter, Remote-Request-Sweep)
- [ ] **T026** — Dokumentation aktualisieren (README, ADR, Architecture, Security)

## Phase 6 — Review & Commit

- [ ] **T027** — Spec-Kit-Nachanalyse: Spec ↔ Code ↔ Tests ↔ Doku
- [ ] **T028** — Reviewer-Agent: Scope Creep, Schichten, SQL-Injection, Logging
- [ ] **T029** — Findings beheben und Gates wiederholen
- [ ] **T030** — Run Report finalisieren
- [ ] **T031** — Lokalen Feature-Commit erstellen (kein Push)

## Abhängigkeiten

```
T001 → T002 → T003 → T004 → T005 → T006 → T007 → T008 → T009 → T010 → T011 → T012
                                                                                    ↓
T013 → T014 → T015 → T016 → T017 → T018 → T019 → T020 → T021 → T022
                                                                     ↓
                                            T023 → T024 → T025 → T026 → T027 → T028 → T029 → T030 → T031
```
