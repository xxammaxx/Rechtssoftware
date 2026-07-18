# Implementation Plan — M4 Document Classification

## Feature
M4 — Regelbasierte Dokumentklassifikation mit Unsicherheitsmodell

## Technical Context

### Current Implementation Status
The M4 feature is **substantially pre-existing** in the codebase. All core components are in place:

| Component | File | Status |
|-----------|------|--------|
| Domain: `ClassificationResult` | `domain/classification.py` | ✅ Present |
| Domain: `Document` fields | `domain/document.py` | ✅ `doc_type`, `classification_confidence` |
| Port: `DocumentClassifier` ABC | `application/document_classifier.py` | ✅ Present |
| Implementation: `RuleBasedClassifier` | `infrastructure/rule_based_classifier.py` | ✅ Present |
| Service integration | `application/document_service.py` | ✅ `upload_document` calls classifier |
| API routes | `api/document_routes.py` | ✅ Classification in response |
| API schemas | `api/schemas.py` | ✅ `doc_type`, `classification_confidence` in response |
| DB schema | `infrastructure/sqlite_document_repository.py` | ✅ `doc_type`, `classification_confidence` columns |
| Tests: classifier | `tests/unit/test_classifier.py` | ✅ Comprehensive |
| Tests: service | `tests/unit/test_document_service.py` | ✅ Classification integration tested |
| Tests: API | `tests/api/test_documents_api.py` | ✅ Checks classification fields in response |
| App wiring | `app.py` | ✅ `RuleBasedClassifier` instantiated and injected |

### Discrepancies: Spec (post-Clarification) vs. Current Implementation

| Area | Spec Requirement | Current Implementation | Gap |
|------|-----------------|----------------------|-----|
| **Confidence algorithm** | Ratio-model: `matched_patterns_of_winning_type / total_patterns_of_winning_type` (Spec Q1) | Proportional model: `best_count / total_matches_across_all_types` | ⚠️ **ALGORITHM MISMATCH** |
| **Tie-breaking** | Highest ratio-score, tie → definition order (FR-M4-09) | Highest absolute count, `max()` default ordering | ⚠️ **LOGIC MISMATCH** |
| **matched_patterns storage** | Gematchte Patterns werden gespeichert (FR-M4-05) | No `matched_patterns` DB column | ❌ **MISSING** |
| **matched_patterns in response** | In DocumentResponse enthalten (FR-M4-06) | Not in `DocumentResponse` schema | ❌ **MISSING** |
| **Boundary confidence = 0.5** | `< 0.5` — ambiguous at exactly 0.5 (CHK008) | `__post_init__` uses `< 0.5` — not clear if intentional | ⚠️ **NEEDS CLARIFICATION** |
| **Pattern structure** | Not explicitly defined in spec (CHK010) | `self.PATTERNS` dict with regex patterns (case-insensitive via `text_lower`) | ✅ Implicitly defined in code |

### Architecture

```
POST /cases/{id}/documents
  → DocumentService.upload_document()
    → TextExtractor.extract(content)        # PDF → text
    → DocumentClassifier.classify(text)      # text → ClassificationResult
    → FileStorage.store(path, content)       # persist PDF file
    → DocumentRepository.save(doc)           # persist metadata + classification
```

### Dependencies
- **pymupdf** (existing) — PDF text extraction (unrelated to classification)
- **No new dependencies** — classification is pure Python regex

### Risk Assessment
- **Low**: Algorithm change (confidence, tie-breaking) — well-tested, pure function
- **Medium**: Adding `matched_patterns` to DB requires schema migration (existing data)
- **Low**: Adding `matched_patterns` to API response — backward-compatible field addition

---

## Constitution Check

| Constitution § | Implication | Compliance |
|----------------|-------------|------------|
| §1 Local-only | Classification must be local-only | ✅ Regex-based, no external calls |
| §2 Privacy by Design | No external data leaks | ✅ Classification result stored with document |
| §3 No automatic legal decisions | Classification is structural, not evaluative | ✅ Document types are administrative categories |
| §4 Human Review | User must review uncertain classifications | ✅ US2 (confidence visibility) enables this |
| §5 Modular architecture | Port → Implementation pattern | ✅ `DocumentClassifier` ABC |
| §6 Vertical slices | API → Domain → Infrastructure | ✅ Full slice exists |
| §7 Red Tests | Tests before implementation | ⚠️ Tests exist but may need updates for algorithm change |
| §8 Local Gates | Local runtime is truth | ✅ Can run tests locally |
| §12 Synthetic test data | Test data prefix "SYNTHETISCH –" | ✅ Already followed |

**Gate Assessment**: No blocking issues. Algorithm changes require test updates (Constitution §7: update red tests first).

---

## Approach

The M4 feature is largely implemented. This plan focuses on **fixing discrepancies** between the clarified spec and current implementation:

1. **Refactor confidence algorithm** from proportional to ratio-model
2. **Refactor tie-breaking** to use ratio-score (not absolute count)
3. **Add `matched_patterns` persistence** — JSON TEXT column in SQLite
4. **Add `matched_patterns` to API response** schema
5. **Verify/tighten boundary semantics** for `confidence = 0.5`
6. **Update tests** to match new algorithm

---

## Phases

### Phase 0: Research (see research.md)
Resolved unknowns:
- R01: Confidence ratio algorithm design
- R02: SQLite storage for list-of-strings (matched_patterns)
- R03: Pattern structure best practices
- R04: Migration strategy for existing documents

### Phase 1: Design Artifacts (see data-model.md, contracts/, quickstart.md)
- Updated data model with `matched_patterns` column
- API contract updates
- Validation/quickstart guide

### Phase 2: Implementation (future — `/speckit.tasks`)
- Confidence algorithm refactor
- Tie-breaking refactor
- Schema migration
- API response update
- Test updates
