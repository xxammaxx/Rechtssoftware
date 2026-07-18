# Spec Quality Checklist — M5 Deterministische Fristkandidaten-Erkennung

**Purpose:** Validates completeness, clarity, consistency, and measurability of M5 requirements.
**Created:** 2026-07-18
**Audience:** Autor (Self-Check) + Reviewer (PR-Gate)
**Depth:** Standard (~30 items)

---

## Requirement Completeness

- [x] CHK001 [Autor] Is the behavior for empty/null `text_content` (document has no extractable text) explicitly specified beyond the `NO_DEADLINE_CANDIDATE` warning? [Completeness, Spec §FR-M5-01, Spec §Fehlerfälle]
- [x] CHK002 [Autor] Are the exact German month names accepted by R2 fully enumerated (e.g., "Jänner" vs. "Januar" — which variants are accepted/rejected)? [Completeness, Spec §R2]
- [x] CHK003 [Autor] Is the deduplication behavior for candidates with different `kind` values but overlapping or identical offsets specified? [Completeness, Spec §FR-M5-12]
- [x] CHK004 [Reviewer] Is the behavior specified for identical raw_text appearing at multiple non-overlapping positions in the document? [Completeness, Spec §FR-M5-12]
- [x] CHK005 [Autor] Are the R5 prefix patterns (e.g., "bis zum", "spätestens am") fully enumerated or is a regex pattern provided? [Completeness, Spec §R5] → Exhaustiv via Regex (Clarification)
- [x] CHK006 [Reviewer] Are requirements specified for the diagnostic logging destination (stdout, file, application log)? [Completeness, Spec §FR-M5-25] → Application-Logger
- [x] CHK007 [Autor] Is the behavior for very short documents (<10 characters) that contain no valid date patterns specified? [Completeness, Gap] → FR-M5-32: <30 Zeichen → leere Kandidatenliste + NO_DEADLINE_CANDIDATE

## Requirement Clarity

- [x] CHK008 [Autor] Is "lokal extrahierten Dokumenttext" (FR-M5-01) explicitly defined as `Document.text_content` from the M3 extraction pipeline? [Clarity, Spec §FR-M5-01] → FR-M5-01 jetzt: "das text_content-Feld aus der M3-Extraktion"
- [x] CHK009 [Reviewer] Is the versioning scheme for "stabile Regel-ID" (FR-M5-10) documented (e.g., `DEADLINE_DATE_NUMERIC_DE_V1` → `_V2` when changed)? [Clarity, Spec §FR-M5-10] → FR-M5-10: "_V1 = erste Version, _V2 bei Änderungen"
- [x] CHK010 [Reviewer] Is the overlap threshold for "überlappende identische Treffer" (FR-M5-12) defined in terms of offset proximity (exact match, containment, partial overlap)? [Clarity, Spec §FR-M5-12] → Containment-basiert
- [x] CHK011 [Autor] Is the error response format for the 500 `EXTRACTION_TIMEOUT` case fully specified with all response fields? [Clarity, Spec §API-Contract, Spec §Fehlerfälle]
- [x] CHK012 [Reviewer] Is the interaction between R1 (numeric) and R2 (textual month) when both could match the same text string explicitly resolved? [Clarity, Spec §R1, Spec §R2] → Unterschiedliche Muster
- [x] CHK013 [Autor] Is the R5 prefix proximity defined — how many characters before a date candidate are searched for a prefix pattern? [Clarity, Spec §R5] → 50 Zeichen rückwärts

## Requirement Consistency

- [x] CHK014 [Reviewer] Do FR-M5-18 ("keine vollständigen Dokumenttexte loggen") and FR-M5-25 (50-Zeichen raw_text in Logs) logically coexist without contradiction? [Consistency, Spec §FR-M5-18, Spec §FR-M5-25]
- [x] CHK015 [Reviewer] Is the deduplication priority order (EXPLICIT_DATE > RELATIVE_PERIOD > QUALITATIVE_REFERENCE) consistent between spec.md, data-model.md, and tasks.md? [Consistency, Spec §FR-M5-12, data-model.md, tasks.md T2.8]
- [x] CHK016 [Reviewer] Does the `DeadlineCertainty` enum in data-model.md (EXACT, UNRESOLVED, AMBIGUOUS) match the certainty values used in the spec's API response example and rule descriptions? [Consistency, data-model.md, Spec §API-Contract, Spec §R3/R4/R6]
- [x] CHK017 [Reviewer] Do the API error codes documented in spec.md (Fehlerfälle) match exactly those in contracts/api.md across all error scenarios? [Consistency, Spec §Fehlerfälle, contracts/api.md]
- [x] CHK018 [Reviewer] Is the `human_review_required: true` requirement (FR-M5-23) consistently present in both the spec's example JSON and contracts/api.md? [Consistency, Spec §FR-M5-23, Spec §API-Contract, contracts/api.md]

## Acceptance Criteria Quality

- [x] CHK019 [Autor] Can "deterministisch" (FR-M5-11) be objectively verified — is there a defined procedure to prove identical results across runs? [Measurability, Spec §FR-M5-11, Spec §US3]
- [x] CHK020 [Reviewer] Can the certainty distinction between "exact" (R1/R2 valid), "unresolved" (R3/R4/R6), and "ambiguous" (R1/R2 invalid) be objectively verified per test case? [Measurability, Spec §FR-M5-27, Spec §FR-M5-05]
- [x] CHK021 [Reviewer] Is the 5-second timeout (FR-M5-21) defined as wall-clock time or CPU time? [Measurability, Spec §FR-M5-21] → Wandzeit / wall-clock (Clarification)
- [x] CHK022 [Autor] Are the acceptance criteria for the `normalized_date` field (ISO 8601 YYYY-MM-DD) explicitly testable across all three candidate kinds (including null for non-date kinds)? [Measurability, Spec §FR-M5-04, data-model.md]
- [x] CHK023 [Reviewer] Are the severity/fix-time criteria for warning codes (e.g., when does AMBIGUOUS_DATE vs. NO_DEADLINE_CANDIDATE trigger different follow-up actions) defined? [Measurability, Spec §Warncodes] → Follow-up ist Frontend-Concern (M5-Grenze)

## Scenario Coverage

- [x] CHK024 [Autor] Is the alternate flow specified where a document has extractable text but produces zero candidates (empty candidate list + NO_DEADLINE_CANDIDATE)? [Scenario Coverage, Spec §FR-M5-14, Spec §Fehlerfälle]
- [x] CHK025 [Reviewer] Is the exception flow specified where the regex engine itself raises an unexpected exception (not timeout, not invalid date)? [Scenario Coverage, Gap] → INTERNAL_ERROR (Clarification)
- [x] CHK026 [Autor] Is the recovery flow specified when a timeout (FR-M5-21) is triggered mid-extraction — is a partial candidate list returned or empty? [Scenario Coverage, Gap] → Vollständiger Abbruch (Clarification)
- [x] CHK027 [Autor] Is a success scenario with mixed candidate kinds (explicit + relative + qualitative in one document) explicitly specified as a test criterion? [Scenario Coverage, Gap] → FR-M5-31: Mixed-Kinds-Testfall

## Edge Case Coverage

- [x] CHK028 [Autor] Are edge-case date notations — leading-zero variations (1.7.2026 vs. 01.07.2026) and whitespace variations (31. 07. 2026) — covered in the acceptance criteria? [Edge Case, Spec §R1]
- [x] CHK029 [Reviewer] Is the year range boundary behavior specified — what happens at year 1900 (inclusive?) and 2099 (inclusive?) in R1's regex? [Edge Case, Spec §R1]
- [x] CHK030 [Autor] Is the interaction between R5-enriched raw_text (which adjusts start_offset) and the 50-character logging truncation (FR-M5-25) specified? [Edge Case, Spec §FR-M5-25, Spec §R5] → Kürzung nach R5-Enrichment (Clarification)
- [x] CHK031 [Reviewer] Is the behavior for text containing only whitespace, special characters, or non-Latin scripts (e.g., Cyrillic dates) specified? [Edge Case, Gap] → Abgrenzung: leere Kandidatenliste; nicht-deutsche Texte i.d.R. leere Ergebnisse
- [x] CHK032 [Autor] Is the behavior specified when the same date is expressed in both numeric (R1) and textual (R2) form in close proximity? [Edge Case, Spec §FR-M5-12]

## Non-Functional Requirements

- [x] CHK033 [Reviewer] Are privacy/data minimization requirements explicitly linked to DSGVO articles in the spec itself (vs. only in data-model.md)? [NFR, Gap] → Abgrenzung verweist jetzt auf data-model.md §Datenschutz
- [x] CHK034 [Autor] Is the maximum request rate / concurrent request assumption for the endpoint documented? [NFR, Gap] → Abgrenzung: "Keine Mehrbenutzer- oder Concurrency-Anforderungen"
- [x] CHK035 [Reviewer] Is the `threading.Timer`-based timeout (FR-M5-21) documented as a non-functional constraint in the spec or only in the plan? [NFR, Spec §FR-M5-21, IMPL_PLAN.md] → Spec: "5 Sekunden Wandzeit/wall-clock" (Clarification)

## Dependencies & Assumptions

- [x] CHK036 [Autor] Is the assumption that M3 `Document.text_content` always returns a valid (not None, not non-string) value documented? [Assumption, Gap] → FR-M5-01: "Annahme: text_content ist ein gültiger String"
- [x] CHK037 [Reviewer] Is the hardcoded German month list's versioning strategy for future language support or locale additions documented? [Dependency, Spec §R2] → R2: "Version: 1.0 (DE). Zukünftige Sprachen via _EN_V1"
- [x] CHK038 [Autor] Is the assumption that the FastAPI server runs single-threaded (or multi-threaded) documented for the Thread-Safety requirement (FR-M5-26)? [Assumption, Gap] → FR-M5-26 ist proaktiv; Server-Modell unabhängig

## Ambiguities & Conflicts

- [x] CHK039 [Reviewer] Is the relationship between US1's acceptance criterion "Originaltext, Position und Regel-ID" and US3's offset-based positioning (start_offset, end_offset) non-ambiguous? [Ambiguity, Spec §US1, Spec §US3]
- [x] CHK040 [Reviewer] Are there any uses of ambiguous adjectives ("robust", "zuverlässig", "schnell") in the spec that remain unquantified? [Ambiguity, Spec passim] → Keine gefunden
