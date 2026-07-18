# Tasks — M4 Document Classification

## Feature
M4 — Regelbasierte Dokumentklassifikation mit Unsicherheitsmodell

## Overview

The M4 feature is **substantially pre-existing**. This task list focuses on fixing **3 discrepancies** between the clarified spec and current implementation:

1. **Confidence algorithm**: Ratio-model (per type) vs. current proportional (across types)
2. **Tie-breaking**: Ratio-score vs. absolute count
3. **matched_patterns**: Missing from entity, DB, API schema, and response

See [plan.md](plan.md) for full gap analysis and [research.md](research.md) for design decisions.

## Dependency Graph

```
US1 (P1) ─────────────────────┐
  T001 RuleBasedClassifier     │  (no deps, pure function refactor)
  T002 ClassificationResult    │  (no deps)
  T003 Tests: classifier       │  (depends on T001, T002)
                               │
US3 (P2) ─────────────────────┘
  T004 Document entity          │
  T005 DocumentService          │  (depends on T004)
  T006 SQLite schema            │  (depends on T004)
  T007 SQLiteRepository         │  (depends on T004, T006)
  T008 API schema               │  (depends on T004)
  T009 API route                │  (depends on T008)
  T010 Tests: API               │  (depends on T006-T009)
  T011 Tests: service           │  (depends on T004, T005)

Polish ────────────────────────
  T012 Full test suite          │  (depends on all above)
  T013 Linting                  │  (depends on all above)
```

**Parallel execution**: US1 and US3 are **independent** — T001-T003 can run in parallel with T004-T011.

## Implementation Strategy

1. **MVP**: US1 only (T001-T003) — algorithm fix is the critical path
2. **Incremental**: US3 adds matched_patterns visibility (T004-T011)
3. **Verification**: Full test + lint pass (T012-T013)

---

## Phase 1: Setup

No setup required. Project is already initialized with all dependencies installed.

---

## Phase 2: Foundational

No foundational tasks. All required infrastructure (FastAPI, SQLite, pymupdf) is in place.

---

## Phase 3: US1 — Dokumenttyp automatisch erkennen (P1)

**Story Goal**: Documents are automatically classified with correct type and confidence using ratio-model.

**Independent Test Criteria**:
- Grouped fixture keywords (bescheid/rechnung/…) reliably classify to correct type
- Empty/unrecognized text → `sonstiges` with `confidence=0.0`
- Confidence uses ratio-model: `matched_patterns_of_winning / total_patterns_of_winning`
- Tie-breaking: highest ratio wins; tie → first in definition order
- Classification result invariants: `0.0 <= confidence <= 1.0`; `confidence < 0.5` forces `sonstiges`

- [x] T001 Refactor `RuleBasedClassifier.classify()` in `src/private_legal_navigator/infrastructure/rule_based_classifier.py` to use ratio-model confidence and ratio-based tie-breaking per data-model.md algorithm spec. Update docstring.

- [x] T002 [P] Verify `ClassificationResult.__post_init__()` in `src/private_legal_navigator/domain/classification.py` uses exclusive `< 0.5` threshold (exactly 0.5 is valid). Add inline comment documenting boundary behavior.

- [x] T003 [US1] Update classifier unit tests in `tests/unit/test_classifier.py`:
  - Adjust `test_classify_bescheid` confidence assertion for ratio-model values
  - Add test `test_tie_breaking_uses_ratio` — verifies tie-breaking logic
  - Add test `test_confidence_exactly_0_5_is_valid` — verifies boundary behavior
  - Add test `test_ratio_model_independence` — verifies ratio is per-type, not cross-type
  - Verify existing tests still pass with new algorithm

---

## Phase 4: US3 — Klassifikationsdetails abrufen (P2)

**Story Goal**: Users can see which patterns matched via `matched_patterns` in API responses.

**Independent Test Criteria**:
- `matched_patterns` is present in DocumentResponse (POST + GET list)
- `matched_patterns` is persisted in SQLite as JSON TEXT column
- `matched_patterns` survives round-trip (save → load → API response)
- Empty text / no match → `matched_patterns: []`

- [x] T004 [P] [US3] Add `matched_patterns: list[str]` parameter and instance attribute to `Document.__init__()` in `src/private_legal_navigator/domain/document.py`. Default to empty list `[]`.

- [x] T005 [US3] Update `DocumentService.upload_document()` in `src/private_legal_navigator/application/document_service.py` to pass `classification.matched_patterns` to `Document` constructor.

- [x] T006 [P] [US3] Add `matched_patterns TEXT NOT NULL DEFAULT '[]'` column to `CREATE_DOCUMENTS_TABLE` in `src/private_legal_navigator/infrastructure/sqlite_document_repository.py`.

- [x] T007 [US3] Update `SqliteDocumentRepository` in `src/private_legal_navigator/infrastructure/sqlite_document_repository.py`:
  - `save()`: serialize `matched_patterns` via `json.dumps()`
  - `_row_to_doc()`: deserialize via `json.loads()` (default `[]` if NULL/empty)
  - Add `matched_patterns` to INSERT and SELECT column lists
  - Import `json` module

- [x] T008 [P] [US3] Add `matched_patterns: list[str] = Field(default_factory=list)` to `DocumentResponse` in `src/private_legal_navigator/api/schemas.py`.

- [x] T009 [US3] Update `_doc_to_response()` in `src/private_legal_navigator/api/document_routes.py` to include `matched_patterns=doc.matched_patterns`.

- [x] T010 [US3] Update `tests/api/test_documents_api.py`:
  - In `test_upload_pdf`, assert `"matched_patterns" in data` and `isinstance(data["matched_patterns"], list)`
  - Add test `test_list_documents_includes_classification` verifying `matched_patterns` in list response

- [x] T011 [US3] Update `tests/unit/test_document_service.py`:
  - In `test_upload_classifies_document`, set `ClassificationResult` with `matched_patterns=["bescheid"]` and verify `result.matched_patterns == ["bescheid"]`
  - In `test_get_document_text_with_classification`, include `matched_patterns` in Document constructor

- [x] T014 [FR-M4-12] Add logging to `DocumentService.upload_document()` in `src/private_legal_navigator/application/document_service.py`: log doc_type, confidence, and matched pattern count at INFO level.

---

## Phase 5: Verification & Polish

- [x] T012 Run full test suite: `.venv/Scripts/python.exe -m pytest --cov=src/private_legal_navigator -v` — **85/85 passed, 96% coverage**.

- [x] T013 Run linting on changed files: `ruff check` — **all checks passed**; `mypy` — **no issues found**.

---

## Task Summary

| Phase | Tasks | Parallel | Label |
|-------|-------|----------|-------|
| Setup | — | — | — |
| Foundational | — | — | — |
| US1 (P1) | T001–T003 | T001 ⟂ T002 → T003 | [US1] |
| US3 (P2) | T004–T011 | T004 ⟂ T006 ⟂ T008 → T005, T007, T009 → T010, T011 | [US3] |
| Verification | T012–T013 | Sequential | — |

## Phase 6: Convergence

- [x] T015 Update Document class docstring invariants in `src/private_legal_navigator/domain/document.py` to include M4 fields: `doc_type`, `classification_confidence`, and `matched_patterns` (partial)

---

**Total tasks**: 14 (+1 convergence)
**MVP scope**: T001–T003 (US1 only — algorithm fix)
**Parallel opportunities**: T001 with T002; T004 with T006 with T008
