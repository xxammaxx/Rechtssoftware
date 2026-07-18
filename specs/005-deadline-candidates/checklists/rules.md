# Rule Engine Requirements Quality — M5 Deterministische Fristkandidaten-Erkennung

**Purpose:** Validates completeness, clarity, consistency, and measurability of M5 Rule Engine requirements (R1–R6, Dedup, Warnings, Timeout).
**Created:** 2026-07-18
**Audience:** Reviewer (PR-Gate)
**Depth:** Standard (~30 items)

---

## Requirement Completeness — Rule Coverage

- [x] CHK001 Are the exact regex patterns for R1 (numeric dates) and R2 (textual months) specified with all allowed variations (leading zeros, whitespace, single-digit days/months)? [Completeness, Spec §R1, Spec §R2]
- [x] CHK002 Are the R3 relative period patterns fully enumerated — is every supported phrasing variant documented (e.g., "binnen 14 Tagen" vs. "innerhalb von 14 Tagen")? [Completeness, Spec §R3]
- [x] CHK003 Are the R5 context prefix patterns fully enumerated as a regex or exhaustive list (e.g., "bis zum", "bis spätestens", "spätestens am", "bis einschließlich", "zum")? [Completeness, Spec §R5] → Exhaustiv via Regex `(bis\s+(zum|spätestens|einschließlich)|spätestens\s+am|zum)\s+` (Clarification)
- [x] CHK004 Are the R6 qualitative reference phrases fully enumerated — is the set exhaustive or exemplary? [Completeness, Spec §R6]
- [x] CHK005 Are the allowed time units for R3/R4 fully enumerated with all inflection variants (Tage, Tagen, Wochen, Monate, Monaten, Jahre, Jahren)? [Completeness, Spec §R3, Spec §R4]
- [x] CHK006 Is the 500K character limit enforced before or after text preprocessing (e.g., whitespace normalization)? [Completeness, Spec §FR-M5-19] → Vor jeglicher Normalisierung (FR-M5-19 clarify)
- [x] CHK007 Is the interaction between the 500K character limit and the 5-second timeout specified — e.g., should a 500K text that triggers timeout also result in full abort? [Completeness, Gap] → FR-M5-29: >500K → 413 TEXT_TOO_LARGE (vor Regex); ≤500K + Timeout → 500 EXTRACTION_TIMEOUT

## Requirement Clarity — Rule Definitions

- [x] CHK008 Is the year range for R1 explicitly bounded — are years 1900 and 2099 inclusive or exclusive? [Clarity, Spec §R1]
- [x] CHK009 Is the R2 month name hardcoded list specified with exact string values (e.g., "Januar", not "Jan." as abbreviation)? [Clarity, Spec §R2]
- [x] CHK010 Is the R5 prefix search direction explicitly defined — are only preceding characters searched, or also surrounding context? [Clarity, Spec §R5]
- [x] CHK011 Is the R5 prefix proximity of 50 characters measured from the match start (offset of first digit/character) or from the match end? [Clarity, Spec §R5]
- [x] CHK012 Is the containment definition for dedup (FR-M5-12) explicitly documented — does A contain B when A.start_offset ≤ B.start_offset AND A.end_offset ≥ B.end_offset? [Clarity, Spec §FR-M5-12]
- [x] CHK013 Is the time unit normalization for R3 defined — e.g., should "14 Tage" be stored as amount=14, unit="Tag" or amount=2, unit="Woche"? [Clarity, Spec §R3]

## Requirement Consistency — Cross-Rule Interactions

- [x] CHK014 Are R1 and R2 consistent in their year validation — does R2 validate years beyond the 1900-2099 range the same way as R1? [Consistency, Spec §R1, Spec §R2] → R2 jetzt harmonisiert: "Jahr auf 1900–2099 begrenzt (analog zu R1)"
- [x] CHK015 Is the interaction between R5 enrichment and dedup specified — does R5 enrichment run before or after dedup? [Consistency, Spec §R5, Spec §FR-M5-12, data-model.md] → R5 vor Dedup
- [x] CHK016 Is the certainty assignment (exact/unresolved/ambiguous) consistent across all rules in the spec and data model? [Consistency, Spec §R1–R6, data-model.md, Spec §FR-M5-27]
- [x] CHK017 Do the warning code generation rules (FR-M5-13 to FR-M5-16) align with the error case table (Fehlerfälle) regarding NO_DEADLINE_CANDIDATE vs. empty document text? [Consistency, Spec §FR-M5-13–16, Spec §Fehlerfälle]
- [x] CHK018 Is the 5-second timeout (FR-M5-21) consistently defined as wall-clock time across the spec, plan, and data model? [Consistency, Spec §FR-M5-21, IMPL_PLAN.md, research.md] → Wandzeit / wall-clock (Clarification + FR-M5-21)

## Acceptance Criteria Quality — Rule Verifiability

- [x] CHK019 Can the correct normalization of R1 dates (e.g., "1.7.2026" → "2026-07-01") be objectively verified per test case? [Measurability, Spec §FR-M5-04, Spec §R1]
- [x] CHK020 Can the AMBIGUOUS_DATE warning for invalid calendar dates (e.g., "31.02.2026") be consistently reproduced across all date formats? [Measurability, Spec §FR-M5-05, Spec §R1]
- [x] CHK021 Can the dedup containment priority (EXPLICIT_DATE > RELATIVE_PERIOD > QUALITATIVE_REFERENCE) be verified in a test with all three candidate types overlapping at the same position? [Measurability, Spec §FR-M5-12]
- [x] CHK022 Can the 5-second timeout be verified with a crafted input that triggers catastrophic backtracking? [Measurability, Spec §FR-M5-21] → FR-M5-30: konstruierter Input mit katastrophalem Backtracking, candidates-Liste leer
- [x] CHK023 Can the "vollständiger Abbruch, keine Partialergebnisse" timeout behavior be verified — is there a defined test procedure for this? [Measurability, Spec §FR-M5-21, Spec §Fehlerfälle]

## Scenario Coverage — Extraction Flows

- [x] CHK024 Is the primary flow specified where all six rules (R1–R6) produce candidates from a single document with mixed content? [Scenario Coverage, Gap] → FR-M5-31: Mixed-Kinds-Testfall
- [x] CHK025 Is the alternate flow specified where only R5 context prefixes are found but no date candidates (i.e., prefix without a following date)? [Scenario Coverage, Gap] → R5: "Existieren keine EXPLICIT_DATE-Kandidaten, hat R5 keine Wirkung"
- [x] CHK026 Is the exception flow specified where text preprocessing (e.g., whitespace stripping) reveals a text shorter than any potential match? [Scenario Coverage, Gap] → FR-M5-19: "Text nach Whitespace-Stripping unter 30 Zeichen → von FR-M5-32 abgedeckt"
- [x] CHK027 Is the recovery flow specified when extraction is aborted mid-pipeline (e.g., R1/R2 completed but timeout occurs before R5 enrichment)? [Scenario Coverage, Gap] → Vollständiger Abbruch (Clarification)

## Edge Case Coverage — Boundary Conditions

- [x] CHK028 Are boundary dates at year 1900 and 2099 explicitly covered — is "01.01.1900" matched and "01.01.2100" rejected per the regex? [Edge Case, Spec §R1]
- [x] CHK029 Is the behavior for text with only R5-relevant prefixes (e.g., "bis zum") but NO date candidates specified? [Edge Case, Spec §R5] → "Keine Wirkung" (R5 clarify)
- [x] CHK030 Is the behavior specified when R5 enrichment causes a candidate to exceed the 50-character logging truncation limit? [Edge Case, Spec §FR-M5-25, Spec §R5] → Kürzung nach R5-Enrichment (FR-M5-25 clarify)
- [x] CHK031 Is the behavior for a 500,001-character document that, after whitespace normalization, falls to <500K characters specified? [Edge Case, Spec §FR-M5-19] → Prüfung auf rohen text_content vor Normalisierung (FR-M5-19 clarify)
- [x] CHK032 Is the behavior for overlapping candidates of the same kind (e.g., two EXPLICIT_DATE candidates with overlapping offsets) specified? [Edge Case, Spec §FR-M5-12]

## Non-Functional Requirements — Rule Engine Safeguards

- [x] CHK033 Is catastrophic backtracking explicitly identified as a risk in the spec (not just in IMPL_PLAN.md) with corresponding regex safety requirements? [NFR, Gap] → FR-M5-30: konstruierter Input für Timeout-Test
- [x] CHK034 Is the regex timeout implementation approach (e.g., `threading.Timer` vs. `signal.SIGALRM`) specified as a constraint? [NFR, Spec §FR-M5-21]
- [x] CHK035 Is the thread-safety requirement (FR-M5-26) explicitly linked to the rule engine's stateless design (no shared mutable state across extract() calls)? [NFR, Spec §FR-M5-26]

## Dependencies & Assumptions — Rule Engine Context

- [x] CHK036 Is the assumption that Python's `re.finditer()` returns matches in left-to-right order documented as a dependency for deterministic behavior? [Assumption, Gap] → Regelkatalog-Preamble: "re.finditer() liefert Matches in der Reihenfolge ihres Auftretens"
- [x] CHK037 Is the Python `re` module's behavior with overlapping matches documented as a constraint (i.e., no overlapping matches without lookahead)? [Dependency, Gap] → Regelkatalog-Preamble: "re.finditer() liefert keine überlappenden Matches"
- [x] CHK038 Is the assumption that the input text is UTF-8 encoded (or at least ASCII-compatible for German text) documented? [Assumption, Gap] → Regelkatalog-Preamble: "Eingabetext als UTF-8 angenommen"

## Ambiguities & Conflicts — Rule Definitions

- [x] CHK039 Is there any ambiguity between R3 "binnen N Einheit" and R2 month-in-year patterns (e.g., "binnen 14. August" — is this a relative period or a date)? [Ambiguity, Spec §R2, Spec §R3]
- [x] CHK040 Is the term "überlappende identische Treffer" (FR-M5-12) fully resolved — are "identisch" defined as same raw_text or same offsets? [Ambiguity, Spec §FR-M5-12]
- [x] CHK041 Are there any unquantified adjectives in the rule specifications ("schnell", "robust", "zuverlässig") that should be replaced with measurable criteria? [Ambiguity, Spec §R1–R6]
