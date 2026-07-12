# Tasks — M2 Lokaler Dokumentimport und sichere Dateiverwaltung

## Phase 0 — Spec & Architecture

- [ ] **T001** — Constitution prüfen (keine Änderungen nötig)
- [ ] **T002** — Spec, Datenmodell, API-Contracts schreiben
- [ ] **T003** — Architekturvalidierung (ARCH_GREEN)

## Phase 1 — Domain

- [ ] **T004** — Red Tests: Document-Entity
- [ ] **T005** — Document-Entity + FileStorage-Port implementieren

## Phase 2 — Infrastructure

- [ ] **T006** — Red Tests: LocalFileStorage + SqliteDocumentRepository
- [ ] **T007** — LocalFileStorage implementieren
- [ ] **T008** — SqliteDocumentRepository implementieren (inkl. Schema-Migration)

## Phase 3 — Application

- [ ] **T009** — Red Tests: DocumentService
- [ ] **T010** — DocumentService implementieren

## Phase 4 — API

- [ ] **T011** — Red Tests: Upload/List/Download-Endpunkte
- [ ] **T012** — Document-Routen, Schemas, Fehlerbehandlung

## Phase 5 — Quality Gates

- [ ] **T013** — Vollständige Tests (Coverage ≥ 90%)
- [ ] **T014** — API-Smoke-Test mit synthetischem PDF
- [ ] **T015** — Security-Sweep (Path Traversal, MIME, Größe, Execution)
- [ ] **T016** — Dokumentation aktualisieren
- [ ] **T017** — Run Report + Feature-Commit
