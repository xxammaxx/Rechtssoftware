# Research — M4 Document Classification

## R01: Confidence Algorithm — Ratio-Model Design

**Decision**: Refactor confidence from proportional model to ratio-model per Spec Clarification Q1.

**Rationale**:
- **Proportional model** (current): `confidence = best_count / total_matches_across_all_types`. This creates interdependence between types — adding patterns to one type can change the confidence of another type.
- **Ratio model** (spec): `confidence = matched_patterns_of_winning_type / total_patterns_of_winning_type`. Each type's confidence is independent. More predictable and interpretable.

**Algorithm** (proposed):

```python
def classify(self, text: str) -> ClassificationResult:
    if not text.strip():
        return ClassificationResult("sonstiges", 0.0, [])

    text_lower = text.lower()
    scores: dict[str, tuple[int, list[str]]] = {}

    for doc_type, patterns in self.PATTERNS.items():
        matched = [p for p in patterns if re.search(p, text_lower)]
        scores[doc_type] = (len(matched), matched)

    # Ratio-model: confidence per type = matched / total_patterns_of_that_type
    ratios: dict[str, tuple[float, list[str]]] = {}
    for doc_type, (count, matches) in scores.items():
        total = len(self.PATTERNS[doc_type])
        ratio = count / total if total > 0 else 0.0
        ratios[doc_type] = (ratio, matches)

    # Tie-breaking: highest ratio wins; tie → first in definition order
    best_type = max(ratios, key=lambda t: (ratios[t][0], -list(ratios.keys()).index(t)))
    best_ratio, best_matches = ratios[best_type]

    if best_ratio == 0.0:
        return ClassificationResult("sonstiges", 0.0, [])

    return ClassificationResult(
        doc_type=best_type,
        confidence=round(best_ratio, 2),
        matched_patterns=best_matches,
    )
```

**Alternatives considered**:
- Keep proportional model — simpler, but violates spec
- Weighted model (custom weights per pattern) — too complex for M4, reserved for future ML classifier

---

## R02: matched_patterns Storage — SQLite JSON TEXT

**Decision**: Store `matched_patterns` as JSON-encoded TEXT column in SQLite.

**Rationale**:
- **JSON TEXT column**: Simple, no schema change (single column), queryable with SQLite JSON functions if needed, zero new dependencies
- **Separate `document_patterns` table**: More normalized but introduces a new table and JOIN for a simple list
- Since the patterns list is write-once, read-always-with-document, and never queried independently, the JSON TEXT approach is optimal

**Storage format**:
```sql
ALTER TABLE documents ADD COLUMN matched_patterns TEXT NOT NULL DEFAULT '[]';
-- Stored as: '["bescheid", "festsetzung"]'
```

**Python mapping**:
- `json.dumps(matched_patterns)` on save
- `json.loads(matched_patterns)` on read (handles empty list `[]`, returns Python list)

**Alternatives considered**:
- Separate table (`document_patterns`) — normalized but overengineered for a simple list
- Pickle — not portable, not queryable
- Comma-separated — breaks if patterns contain commas

---

## R03: Pattern Structure Best Practices

**Decision**: Keep current pattern approach — case-insensitive regex via `text_lower()`, dictionary of type → list of regex patterns.

**Rationale**:
- Current approach is simple, transparent, and testable
- Regex allows flexible matching (prefixes, word boundaries, variations)
- Using `text_lower()` + lowercase patterns avoids case-sensitivity issues
- Adding `re.IGNORECASE` is an alternative but current approach is equivalent

**Key design points**:
| Aspect | Current | Assessment |
|--------|---------|------------|
| Case sensitivity | `text_lower()` + lowercase patterns | ✅ Works, explicit |
| Match logic | OR within type (any pattern can match) | ✅ Appropriate for keyword classification |
| Pattern format | Raw regex strings | ✅ Flexible, allows `r"\bword\b"` boundary matching |
| Pattern priority | Equal weight per pattern | ✅ Consistent with ratio-model |
| Re-classification | Stateless — always recomputes from text | ✅ Idempotent |

**No changes needed** to pattern structure. Patterns are already well-designed.

---

## R04: Migration Strategy for Existing Documents

**Decision**: Add `matched_patterns` column with `ALTER TABLE` + backfill for existing documents.

**Strategy**:
1. **Add column**: `ALTER TABLE documents ADD COLUMN matched_patterns TEXT NOT NULL DEFAULT '[]';`
2. **Backfill** (optional, for existing documents with text_content):
   - Query documents WHERE `text_content != ''` AND `matched_patterns IS '[]'`
   - Re-classify using `RuleBasedClassifier`
   - Update `matched_patterns` and (if algorithm changed) `classification_confidence` and `doc_type`
3. **Idempotency**: The `initialize_schema()` method in `SqliteDocumentRepository` already handles schema creation. A new version check or migration script may be needed.

**Risk**: Low. The `'[]'` default ensures all existing documents have a valid JSON empty list, avoiding null-handling issues.

**Alternatives considered**:
- Skip backfill — existing documents will have empty `matched_patterns`; acceptable for M4
- Full schema migration versioning — overengineered for single-column addition

---

## R05: Performance Expectations

**Decision**: Document maximum 100 ms for typical documents.

**Rationale**:
- Classification is pure regex on extracted text (typically < 50 KB for administrative documents)
- Regex matching against ~70 patterns total is near-instantaneous (< 1 ms)
- The 100 ms budget accounts for edge cases (very large documents) and headroom
- No synthetic benchmarks needed — the threshold exists as a design-time reference, not a CI gate

---

## R06: Observability — Classification Logging

**Decision**: Log every classification decision at INFO level via Python's built-in `logging` module.

**Rationale**:
- Enables debugging and audit without external dependencies
- Logs contain doc_type, confidence, and count of matched patterns (not the full pattern list — data minimization per Constitution §2)
- No PII in logs (Constitution compliance)
- Python logging is already available, no new dependency

**Log format** (example):
```
INFO  [classification] Document <id> classified as bescheid (confidence=0.53, patterns=8)
```

---

## Summary of Changes Needed

| Component | Change | Impact |
|-----------|--------|--------|
| `ClassificationResult.__post_init__` | Verify threshold `< 0.5` (exclusive) | Low |
| `RuleBasedClassifier.classify()` | Ratio-model + tie-breaking refactor | **High** — core algorithm |
| `Document` entity | Add `matched_patterns` field | Low |
| SQLite schema | Add `matched_patterns TEXT` column | Low |
| `SqliteDocumentRepository` | Save/load `matched_patterns` | Low |
| `DocumentResponse` schema | Add `matched_patterns: list[str]` field | Low |
| `_doc_to_response()` | Include `matched_patterns` | Low |
| Classifier tests | Update expected values for ratio-model | Medium |
| Service/API tests | Verify `matched_patterns` in response | Low |
