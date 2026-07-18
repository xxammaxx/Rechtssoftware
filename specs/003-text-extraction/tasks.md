# Tasks — M3 Dokumenttextgewinnung

## Feature
M3 — Dokumenttextgewinnung mit lokalem PDF-Text

## Implementation Strategy
**MVP-first, incremental delivery.** Phase 2 (Foundational) must complete first as it provides types and schema changes needed by both user stories. US1 and US2 are sequential (US2 depends on US1's output). Tests follow red-test-first convention per Constitution §7.

## User Stories & Priorities

| Story | Priority | Description | Independent Test Criteria |
|-------|----------|-------------|--------------------------|
| US1 | P1 | PDF-Text extrahieren | Upload valid PDF → document created with text_content populated. Upload corrupted PDF → document created with text_content="" and extraction_error set. |
| US2 | P1 | Extrahierten Text abrufen | GET .../text returns document_id, text_content, text_length, extraction_error. Returns correct values for success, no-text-layer, and failure cases. |

## Dependency Graph

```
Phase 2 (T001–T003)
    │
    ▼
Phase 3 — US1 (T004–T007)
    │
    ▼
Phase 4 — US2 (T008–T010)
    │
    ▼
Phase 5 — Validation (T011)
```

US1 and US2 must run sequentially — US2 depends on extraction_error field being populated in the Document entity and persisted by the repository.

## Parallel Execution Opportunities

- **T001, T002, T003** — Parallel (different files, independent)
- **T004 + T005** — Sequential (T004 = red tests, T005 = implementation)
- **T006 + T007** — Sequential (T006 = red tests, T007 = implementation)
- **T008, T009, T010** — T008 and T010 can be parallel; T009 depends on T008

---

## Phase 1: Setup

No setup tasks required. Project exists at `C:\Rechtssoftware`, pymupdf is installed, `.venv` active.

---

## Phase 2: Foundational (blocking prerequisites)

- [x] T001 Add `ExtractionResult` NamedTuple to TextExtractor port in `src/private_legal_navigator/application/text_extractor.py`
  - New type: `ExtractionResult = NamedTuple("ExtractionResult", [("text", str), ("error", str | None)])`
  - Update `extract()` return type annotation from `-> str` to `-> ExtractionResult`
  - Update docstring to document the two fields

- [x] T002 [P] Add `extraction_error: str | None = None` field to Document entity in `src/private_legal_navigator/domain/document.py`
  - Add parameter to `__init__` (keyword-only, defaults to `None`)
  - Assign to `self.extraction_error`
  - Update class docstring invariants to mention `extraction_error` is None on success, str on failure

- [x] T003 [P] Add `extraction_error` column to SQL schema and repository queries in `src/private_legal_navigator/infrastructure/sqlite_document_repository.py`
  - Add ALTER TABLE migration: `ALTER TABLE documents ADD COLUMN extraction_error TEXT DEFAULT NULL`
  - Add to `CREATE_DOCUMENTS_TABLE` for fresh installs
  - Include `extraction_error` in INSERT, SELECT queries
  - Pass to `_row_to_doc` constructor
  - Ensure migration is idempotent (check column existence before ALTER)

---

## Phase 3: US1 — PDF-Text extrahieren (P1)

- [x] T004 [P] [US1] Write/update unit tests for PdfTextExtractor returning ExtractionResult in `tests/unit/test_pdf_text_extractor.py`
  - Test: valid PDF returns `ExtractionResult(text=..., error=None)`
  - Test: invalid PDF (corrupted bytes) returns `ExtractionResult(text="", error="...")`
  - Test: empty bytes returns `ExtractionResult(text="", error="...")`
  - Verify extraction_error messages contain NO document content (PII-safe per EC-M3-04)
  - These tests will fail against current code (red tests)

- [x] T005 [US1] Update PdfTextExtractor with differentiated exception handling in `src/private_legal_navigator/infrastructure/pdf_text_extractor.py`
  - Change return type from `str` to `ExtractionResult`
  - Catch `pymupdf.EmptyFileError` → ExtractionResult(text="", error="Datei ist leer")
  - Catch `pymupdf.FileDataError` → attempt to distinguish:
    - If error message contains "encrypt" → ExtractionResult(text="", error="PDF ist verschlüsselt")
    - Otherwise → ExtractionResult(text="", error="PDF ist korrupt")
  - Catch `Exception` → ExtractionResult(text="", error="Unerwarteter Fehler bei Textextraktion")
  - Success path → ExtractionResult(text=joined_text, error=None)
  - Ensure error messages contain NO document content (PII-safe)
  - Language: German. All extraction_error messages MUST be in German.

- [x] T006 [P] [US1] Write/update unit tests for DocumentService ExtractionResult handling in `tests/unit/test_document_service.py`
  - Test: mock `extract()` returns `ExtractionResult("text", None)` → doc.text_content == "text", doc.extraction_error is None
  - Test: mock `extract()` returns `ExtractionResult("", "error")` → doc.text_content == "", doc.extraction_error == "error"
  - Test: upload with extraction error still calls `file_storage.store` and `doc_repo.save`
  - Update existing mock return values from plain str to ExtractionResult

- [x] T007 [US1] Update DocumentService.upload_document for ExtractionResult in `src/private_legal_navigator/application/document_service.py`
  - Call `self._text_extractor.extract(content)` → receives `ExtractionResult`
  - Pass `text_content=result.text` and `extraction_error=result.error` to Document constructor
  - Ensure upload proceeds even when extraction_error is set (EC-M3-02)

---

## Phase 4: US2 — Extrahierten Text abrufen (P1)

- [x] T008 [P] [US2] Add `extraction_error: str | None = None` field to DocumentTextResponse in `src/private_legal_navigator/api/schemas.py`
  - Add field after `text_length`

- [x] T009 [US2] Update get_document_text route to include extraction_error in `src/private_legal_navigator/api/document_routes.py`
  - Add `extraction_error=doc.extraction_error` to the `DocumentTextResponse(...)` constructor call

- [x] T010 [P] [US2] Write API integration tests for extraction_error in text response in `tests/api/test_documents_api.py`
  - Test: upload valid PDF → GET .../text → extraction_error is null
  - Test: upload invalid PDF → GET .../text → extraction_error contains error message
  - Test: extraction_error is NOT present in document list response (GET .../documents)

---

## Phase 5: Validation

- [x] T011 Run full test suite and verify all tests pass
  ```bash
  .venv/Scripts/python.exe -m pytest tests/ -v --tb=short
  .venv/Scripts/python.exe -m pytest --cov=src/private_legal_navigator --cov-fail-under=90
  ```

## Task Summary

| Phase | Tasks | Count |
|-------|-------|-------|
| Phase 2 — Foundational | T001–T003 | 3 |
| Phase 3 — US1 (PDF-Text extrahieren) | T004–T007 | 4 |
| Phase 4 — US2 (Extrahierten Text abrufen) | T008–T010 | 3 |
| Phase 5 — Validation | T011 | 1 |
| **Total** | **T001–T011** | **11** |

## Independent Test Criteria

### US1 — PDF-Text extrahieren
- Upload a valid PDF (minimal PDF with "Hallo Welt" text)
  - Expected: HTTP 201, document saved
  - GET .../text → text_content contains "Hallo Welt", extraction_error is null
- Upload a corrupted PDF (random bytes with .pdf extension)
  - Expected: HTTP 201 (upload succeeds), document saved
  - GET .../text → text_content is "", extraction_error contains error message
- Upload an empty file
  - Expected: HTTP 201, extraction_error contains "Datei ist leer"

### US2 — Extrahierten Text abrufen
- GET .../text for existing document → 200 with all four fields
- GET .../text for nonexistent document → 404
- Response fields: document_id (UUID), text_content (str), text_length (int), extraction_error (str | null)
