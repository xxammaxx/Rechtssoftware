# Requirements Quality Checklist — M4 Document Classification

**Purpose**: Validate the completeness, clarity, consistency, and coverage of the M4 classification requirements
**Created**: 2026-07-18
**Scope**: Full vertical slice (API → Domain → Persistence)
**Depth**: Standard
**Audience**: Reviewer (PR gate)

## Requirement Completeness

- [x] CHK001 — Are explicit pattern/rule definitions (keyword lists, match criteria) specified for each of the six document types (bescheid, rechnung, mahnung, vertrag, widerspruch, sonstiges)? [Completeness, Gap]
  → **Resolved**: FR-M4-02 delegates pattern definitions to code-level Python Dataclasses. Research.md R03 documents pattern structure (case-insensitive regex, OR logic, equal weight). Implementation in `rule_based_classifier.py` defines all patterns.

- [x] CHK002 — Are requirements specified for the storage format of `matched_patterns` (SQLite has no native list type — JSON TEXT or separate table)? [Completeness, Gap, Spec §Data Model]
  → **Resolved**: Data-model.md specifies JSON TEXT column. Research.md R02 documents rationale and storage format.

- [x] CHK003 — Is the full classification pipeline sequence (upload → text extraction → pattern matching → confidence calculation → persistence → response) explicitly documented as a process flow? [Completeness, Spec §FR-M4-01]
  → **Resolved**: FR-M4-01 describes synchronous classification after upload + extraction. Plan.md architecture diagram shows full pipeline. Contracts/api.md documents the endpoint flow.

- [x] CHK004 — Are requirements specified for the behavior when a document is re-uploaded or re-classified? (Replace previous classification? Cascade delete?) [Completeness, Gap]
  → **Resolved**: Added to Abgrenzung: "Re-Klassifikation bestehender Dokumente (Klassifikation läuft genau einmal beim Upload; Dokumente sind immutabel)". Documents are create-only; each upload creates a new document.

- [x] CHK005 — Are the DocumentClassifier port interface methods (ABC) fully specified with input/output types? [Completeness, Spec §FR-M4-07]
  → **Resolved**: FR-M4-07 requires ABC modeling. The interface in `application/document_classifier.py` specifies `classify(text: str) -> ClassificationResult`. FR-M4-08 allows future ML replacement.

- [x] CHK006 — Is the `doc_type` NOT NULL constraint with default `'sonstiges'` explicitly documented as a business rule (not just a DB schema detail)? [Completeness, Spec §Data Model]
  → **Resolved**: Data-model.md invariants document NOT NULL defaults. FR-M4-04 and FR-M4-10 confirm behavior at domain level.

## Requirement Clarity

- [x] CHK007 — Is the confidence ratio formula unambiguous? (Numerator = matched patterns of winning type; Denominator = total patterns of winning type — clarified in Clarifications but not in FR-M4-03 itself?) [Clarity, Spec §FR-M4-03]
  → **Resolved**: FR-M4-03 updated to state "Ratio-Modell (gematchte Patterns / alle Patterns des Gewinnertyps)". Data-model.md provides formula and worked example.

- [x] CHK008 — Is the threshold `< 0.5` precise about the boundary value `0.5`? (Does `confidence = 0.5` fall into `sonstiges` or not?) [Clarity, Spec §FR-M4-04]
  → **Resolved**: Data-model.md invariants: "Threshold exclusiv: genau 0.5 bleibt bestehen". Contracts/api.md error table: "threshold is exclusive < 0.5".

- [x] CHK009 — Is "Definitionsreihenfolge" (FR-M4-09 tie-breaking) specified with a concrete, documented ordering of document types? [Clarity, Spec §FR-M4-09]
  → **Resolved**: Data-model.md: "Reihenfolge in PATTERNS-Dict". Research.md R03: insertion order (Python 3.7+), deterministic: bescheid, rechnung, mahnung, vertrag, widerspruch.

- [x] CHK010 — Is the structure of a classification pattern (keywords, case sensitivity, match logic — AND/OR) defined in requirements? [Clarity, Gap]
  → **Resolved**: Research.md R03 documents: case-insensitive via text_lower(), OR logic within type, equal weight per pattern, regex flexibility. FR-M4-02 delegates to code-level artifacts.

- [x] CHK011 — Is "gematchte Patterns werden gespeichert" (FR-M4-05) specific enough: are all matched patterns stored per document, or only the winning type's patterns? [Clarity, Spec §FR-M4-05]
  → **Resolved**: Data-model.md and research.md clarify: stored patterns are the winning type's matched patterns. Implementation stores `best_matches` from the winning type.

## Requirement Consistency

- [x] CHK012 — Do FR-M4-04 (confidence < 0.5 → sonstiges) and FR-M4-10 (empty text → sonstiges with 0.0) align without contradiction? (Empty text produces 0 patterns → confidence 0.0 → should always satisfy < 0.5) [Consistency, Spec §FR-M4-04, FR-M4-10]
  → **Resolved**: Aligned. Empty text → 0 matches → 0.0 confidence → < 0.5 → sonstiges. No contradiction.

- [x] CHK013 — Is the classification result always non-null for all documents, including edge cases? (doc_type and confidence vs. nullable fields) [Consistency, Spec §Data Model]
  → **Resolved**: Data-model.md: `doc_type TEXT NOT NULL DEFAULT 'sonstiges'`, `classification_confidence REAL NOT NULL DEFAULT 0.0`. Always present.

- [x] CHK014 — Do the API response examples in data-model.md match the fields specified in FR-M4-06? (matched_patterns is mentioned in FR but not in the JSON example) [Consistency, Spec §FR-M4-06, Spec §Data Model]
  → **Resolved**: Data-model.md updated in Phase 1 to include `matched_patterns` in JSON example. Now consistent with FR-M4-06.

## Acceptance Criteria Quality

- [x] CHK015 — Are measurable acceptance criteria defined for the confidence threshold boundary (0.0, 0.5, 1.0)? [Measurability, Gap]
  → **Resolved**: Quickstart.md boundary verification table covers all three values. Contracts/api.md error table documents behavior per condition. Unit tests verify 0.0 and < 0.5 behavior.

- [x] CHK016 — Are acceptance criteria defined for tie-breaking correctness (two types with equal ratio)? [Measurability, Gap]
  → **Resolved**: FR-M4-09 and data-model.md define tie-breaking algorithm. Quickstart.md section 4 documents manual verification procedure. T003 will add unit test.

- [x] CHK017 — Can every FR-M4 requirement be objectively verified by a reviewer or test? [Measurability, Spec §FR-M4-01 – FR-M4-10]
  → **Resolved**: All 10 FRs are verifiable: FR-M4-01/06 via API tests, FR-M4-02/07/08 via code review, FR-M4-03/04/05/09/10 via unit tests.

## Scenario Coverage

- [x] CHK018 — Is the integration scenario with the existing document upload flow (POST /cases/{id}/documents) specified at requirements level? (Does classification extend existing endpoint or replace it?) [Coverage, Spec §FR-M4-01]
  → **Resolved**: FR-M4-01 specifies synchronous classification in the existing POST endpoint. Contracts/api.md defines the extended response format.

- [x] CHK019 — Is the scenario "document has existing text extraction failure (empty text)" explicitly tied to classification behavior? [Coverage, Spec §FR-M4-10]
  → **Resolved**: FR-M4-10 directly specifies behavior for empty/ failed text extraction: sonstiges + 0.0 + empty patterns.

- [x] CHK020 — Is the re-classification scenario specified? (What happens when classification runs again on an already classified document?) [Coverage, Gap]
  → **Resolved**: Added to Abgrenzung: documents are immutable, classification runs exactly once on upload. No re-classification. The classifier is stateless/idempotent.

## Edge Case Coverage

- [x] CHK021 — Are all boundary confidence values addressed in requirements? (confidence = exactly 0.0, exactly 0.5, exactly 1.0) [Edge Case, Spec §FR-M4-04]
  → **Resolved**: FR-M4-04 covers < 0.5, data-model invariants specify 0.5 as valid (exclusive threshold), quickstart boundary table covers 0.0, 0.5, 1.0.

- [x] CHK022 — Is the scenario "all patterns match for one type → confidence = 1.0" explicitly documented? [Edge Case]
  → **Resolved**: Quickstart boundary verification table includes "All patterns match one type → That type → 1.0". Implicit in ratio formula.

- [x] CHK023 — Is the scenario "two or more document types produce identical confidence scores" addressed with tie-breaking logic? [Edge Case, Spec §FR-M4-09]
  → **Resolved**: FR-M4-09 directly specifies: highest ratio wins, tie → definition order.

- [x] CHK024 — Are performance/load expectations for classification defined? (Maximum latency for synchronous classification in upload endpoint?) [Edge Case, NFR, Gap]
  → **Resolved**: FR-M4-11 added: "Klassifikation muss innerhalb von 100 ms für typische Dokumente (< 50 KB Text) abschliessen". Research.md R05 documents rationale.

- [x] CHK025 — Are observability requirements specified? (Should classification decisions be logged with doc_type, confidence, matched patterns?) [NFR, Gap]
  → **Resolved**: FR-M4-12 added: "Jede Klassifikation wird geloggt: doc_type, confidence, Anzahl gematchter Patterns (INFO-Level, Python logging)". Research.md R06 documents log format and data minimization.

- [x] CHK026 — Are data protection requirements for classification metadata aligned with Constitution §2 (Privacy by Design, local-only)? [NFR, Compliance]
  → **Resolved**: Classification is local-only regex (no external calls). Classification data stored locally with document. Constitution §2 satisfied.

- [x] CHK027 — Are pattern definition documentation requirements specified? (Patterns as Python Dataclasses are code — is there a requirement for inline documentation?) [NFR, Gap]
  → **Resolved**: FR-M4-02 delegates patterns to code. Research.md R03 documents pattern structure. Code has comprehensive docstrings.

## Dependencies & Assumptions

- [x] CHK028 — Is the assumption that text extraction always produces a string (possibly empty) documented in requirements? [Assumption]
  → **Resolved**: FR-M4-10 handles empty text. Research.md R04 notes the assumption. The classifier always receives a string.

- [x] CHK029 — Is the dependency on pymupdf (text extraction) for classification input explicitly acknowledged? [Dependency]
  → **Resolved**: Plan.md lists pymupdf as existing dependency. The architecture shows TextExtractor → Classifier pipeline.

## Ambiguities

- [x] CHK030 — Is the term "gematchte Patterns" unambiguous? (Does it mean all patterns that matched across ALL types, or only the winning type's matched patterns?) [Ambiguity, Spec §FR-M4-05]
  → **Resolved**: FR-M4-05 + data-model.md + implementation all clarify: only the winning type's matched patterns are stored and returned.

- [x] CHK031 — Is the scenario "confidence = 0.0 with zero matches" clearly distinct from "confidence = 0.0 with some matches but all patterns of winning type failed"? [Ambiguity]
  → **Resolved**: Both paths produce the same result (sonstiges, 0.0, []). The distinction has no practical impact on behavior.
