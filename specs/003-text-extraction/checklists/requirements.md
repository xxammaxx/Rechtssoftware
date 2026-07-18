# Requirements Quality Checklist — M3 Dokumenttextgewinnung

**Purpose**: Validate completeness, clarity, consistency, and testability of requirements for PDF text extraction
**Created**: 2026-07-18
**Focus**: API contract rigor + edge case coverage + data model consistency
**Depth**: Standard
**Audience**: Reviewer (PR)

## Requirement Completeness

- [x] CHK001 - Are requirements defined for ALL three extraction outcomes (successful text, no text layer, extraction failure)? [Completeness, Spec §FR-M3-01, §EC-M3-01a–05, Resolved]
- [x] CHK002 - Is the synchronous extraction timing ("nach Upload" in FR-M3-01) explicitly stated — inline within the POST request vs. deferred/background? [Completeness, Spec §FR-M3-01, Resolved]
- [x] CHK003 - Are the requirements for the `ExtractionResult` port contract (TextExtractor return type) documented alongside the interface definition? [Completeness, Spec §FR-M3-06, data-model.md, Resolved]
- [x] CHK004 - Are logging requirements fully specified — which logger, what level (ERROR), what information is safe to log vs. excluded (no PII)? [Completeness, Spec §EC-M3-04, Resolved with logger convention]
- [x] CHK005 - Is the schema migration path for `extraction_error` (ALTER TABLE ADD COLUMN) documented as a requirement, not just a design detail? [Completeness, Resolved in data-model.md]

## Requirement Clarity

- [x] CHK006 - Is the distinction between "no text layer" (EC-M3-05: scanned PDF, extraction succeeded) and "extraction error" (EC-M3-01a/01b: corrupted/encrypted, extraction failed) unambiguous for an implementer reading the spec alone? [Clarity, Spec §EC-M3-02 vs §EC-M3-05, Resolved]
- [x] CHK007 - Are the possible values or format of `extraction_error` messages specified — free text, enumerated codes, or a template? [Clarity, Spec §EC-M3-03, Resolved]
- [x] CHK008 - Is "automatisch nach Upload" (FR-M3-01) sufficiently precise about when extraction fires — before or after file persistence? [Clarity, Spec §FR-M3-01, Resolved: "nach erfolgreicher Dateipersistierung"]
- [x] CHK009 - Are the pymupdf exception-to-error-message mappings documented, or is this left to implementation discretion? [Clarity, Resolved via EC-M3-01a/01b/01c + tasks.md T005]
- [x] CHK010 - Is "vollständig lokal" (FR-M3-02) scoped to exclude ALL remote calls including telemetry, license checks, or dependency downloads? [Clarity, Spec §FR-M3-02, §FR-M3-09, Resolved]

## Requirement Consistency

- [x] CHK011 - Does `extraction_error` have the same type (`str | None`, nullable, optional) across the Document entity, SQL schema, API response, and ExtractionResult contract? [Consistency, data-model.md, Resolved]
- [x] CHK012 - Is the absence of `extraction_error` in the document list endpoint (GET .../documents) consistently documented and is this intentional exclusion justified? [Consistency, contracts/api.md, Resolved]
- [x] CHK013 - Does the SQL schema (`TEXT DEFAULT NULL`) agree with the entity definition (`str | None = None`) and the API response (`"extraction_error": null`)? [Consistency, data-model.md, Resolved]
- [x] CHK014 - Are the edge case identifiers (EC-M3-01a through EC-M3-05) consistent with the functional requirement ID scheme (FR-M3-01 through FR-M3-09)? [Consistency, Resolved]
- [x] CHK015 - Does the API contract (contracts/api.md) align with the spec's functional requirements — no missing or extra response variants? [Consistency, Spec §FR-M3-04, contracts/api.md, Resolved]

## Acceptance Criteria & Testability

- [x] CHK016 - Can each FR-M3 requirement be independently verified through a single API call or unit test assertion? [Measurability, Spec §FR-M3-01–09, Resolved]
- [x] CHK017 - Can each EC-M3 edge case be reproduced and validated without requiring a real corrupted PDF (e.g., via synthetic test data)? [Measurability, Spec §EC-M3-01a–05, Resolved]
- [x] CHK018 - Is the three-way response distinction (success / no-text-layer / error) testable solely from the `text_content` + `extraction_error` fields without internal knowledge? [Acceptance Criteria, contracts/api.md, Resolved]
- [x] CHK019 - Is there an acceptance criterion for "upload succeeds despite extraction failure" — what HTTP status and body prove this behavior? [Acceptance Criteria, Spec §EC-M3-02, Resolved]
- [x] CHK020 - Can the "no PII in extraction_error" requirement (Constitution §2) be objectively verified? [Measurability, Gap → Resolved via EC-M3-04]

## Scenario Coverage

- [x] CHK021 - Is the happy path (valid PDF with extractable text) covered by requirements across all layers — upload succeeds, text stored, text retrievable? [Coverage, Spec §FR-M3-01, §FR-M3-04, Resolved]
- [x] CHK022 - Is the no-text-layer scenario (valid PDF, scanned document) covered — extractions succeeds, text_content is empty, extraction_error is null? [Coverage, Spec §EC-M3-05, Resolved]
- [x] CHK023 - Is the corrupted PDF scenario covered — pymupdf raises FileDataError, upload succeeds, text_content empty, extraction_error set? [Coverage, Spec §EC-M3-01a, §EC-M3-02, Resolved]
- [x] CHK024 - Is the encrypted/password-protected PDF scenario covered — distinct from generic "corrupted" with separate error message? [Coverage, Spec §EC-M3-01b, Resolved]
- [x] CHK025 - Is the empty file scenario covered — distinct pymupdf EmptyFileError handling specified? [Coverage, Resolved via EC-M3-01c]

## Edge Case Coverage

- [x] CHK026 - Are requirements defined for unicode/non-ASCII text content in PDFs (e.g., German umlauts, Cyrillic)? [Coverage, Resolved via Weitere Annahmen]
- [x] CHK027 - Is the behavior specified for extremely large PDFs near the 20 MB upload limit — timeout expectations, memory constraints? [Coverage, Resolved via Weitere Annahmen]
- [x] CHK028 - Are re-upload scenarios addressed — if a document with failed extraction is re-uploaded, does extraction re-run? [Coverage, Resolved via Weitere Annahmen]
- [x] CHK029 - Is the behavior for PDFs with mixed content (some pages with text, some without) specified? [Coverage, Resolved via Weitere Annahmen]

## Non-Functional Requirements

- [x] CHK030 - Are privacy constraints on `extraction_error` messages explicitly documented (error text MUST NOT contain document contents or PII)? [NFR, Resolved via EC-M3-04]
- [x] CHK031 - Is the local-only constraint (FR-M3-02, FR-M3-09) scoped to exclude implicit remote calls (e.g., font downloading by pymupdf)? [NFR, Resolved via FR-M3-02 + FR-M3-09]
- [x] CHK032 - Are performance expectations for extraction of a 20 MB PDF specified, or is "synchronous within request" considered acceptable? [NFR, Resolved via Weitere Annahmen]

## Dependencies & Assumptions

- [x] CHK033 - Is the pymupdf library version constraint documented as a dependency requirement? [Dependency, Resolved via Weitere Annahmen + pyproject.toml]
- [x] CHK034 - Is the assumption that extraction runs synchronously (blocking the HTTP request) explicitly stated rather than implied? [Assumption, Spec §FR-M3-01, Resolved: "synchron extrahiert"]
- [x] CHK035 - Is the assumption that PDFs > 20 MB are rejected before extraction (enforced by existing upload limit) validated against the extraction requirements? [Assumption, Resolved via Weitere Annahmen]
- [x] CHK036 - Are the consequences of a failing pymupdf dependency (library update breaks extraction) addressed? [Dependency, Resolved via Weitere Annahmen]
