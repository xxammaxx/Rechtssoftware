# M5 PR #2 — Independent Review Report

**Review-Agent:** Hermes (unabhängig vom Bau-Agenten)
**Datum:** 2026-07-14
**Repository:** xxammaxx/Rechtssoftware
**Issue:** #1 — M5: Deterministische Fristkandidaten-Erkennung
**Pull Request:** #2 — feat: add deterministic deadline candidate extraction

---

## 1. Abschlussklassifikation

**MERGE_READY_AWAITING_OWNER_APPROVAL**

Alle Gates grün. PR #2 reviewbereit. Merge muss vom Eigentümer freigegeben werden.

---

## 2. Kurzfazit

PR #2 setzt den M5-Scope korrekt um. Die Extraktion ist deterministisch,
ReDoS-sicher, und liefert diskrete Certainty-Werte statt unkalibrierter
Confidence-Scores. Ein MAJOR Finding (AMBIGUOUS_DATE-Warncode definiert
aber nie emittiert) wurde behoben. Drei MINOR und zwei NOTE Findings
in Dokumentation wurden korrigiert.

---

## 3. OS und Shell

| Field | Value |
|-------|-------|
| OS | Windows 10 (MINGW64_NT-10.0-19045) |
| Shell | Git Bash (MSYS2) 5.2.37 |
| User | xxammaxx |
| Working Dir | C:\Rechtssoftware |

---

## 4. Git-Realität

| Field | Value |
|-------|-------|
| Base SHA (main) | `38074daefc06b7c2ed44cda18f32431bbf62b99e` |
| Original Head SHA | `bcbebe8839528da8d82c594e93b5a96ce58a5488` |
| Final Head SHA | `ad017c56ce55bbfd38d5267585a78daf1e3fd576` |
| Branch | `feat/005-deadline-candidates` |
| Commits | 3 (feature → docs → review fix) |
| Worktree | Clean |
| Local = Remote | ✅ |

---

## 5. Diff-Dateizahl

`git diff --stat origin/main...origin/feat/005-deadline-candidates` = **18 Dateien**

| Kategorie | Anzahl | Dateien |
|-----------|--------|---------|
| Neue Domain/App/Infra | 5 | deadline.py, deadline_extractor.py, deadline_service.py, deterministic_deadline_extractor.py, deadline_schemas.py |
| Neue Specs | 4 | spec.md, data-model.md, contracts/api.md, tasks.md |
| Neue Tests | 4 | test_domain_deadline.py, test_deadline_extractor.py, test_deadline_service.py, test_deadline_api.py |
| Neue Docs | 1 | M5-deadline-candidates.md |
| Modifiziert | 4 | README.md, architecture.md, document_routes.py, app.py |

**Klärung der Diskrepanz (18 vs 20):** Der ursprüngliche Run Report listete 17 Dateien (13 neu + 4 modifiziert) und behauptete "20". Tatsächlich sind es 18. Der Run Report wurde korrigiert.

---

## 6. Base-Gates (origin/main)

| Gate | Result |
|------|--------|
| pytest | 83 passed |
| coverage | 96.41% |
| ruff | PASS |
| mypy | PASS (28 files) |
| pip check | PASS |

---

## 7. PR-Gates (origin/feat/005-deadline-candidates, final)

| Gate | Result |
|------|--------|
| pytest | **165 passed** (83 regression + 82 M5) |
| coverage | **95.82%** |
| ruff | PASS |
| mypy | PASS (33 source files) |
| pip check | PASS (project deps) |

---

## 8. Spec-Kit-Traceability

**SPEC_GREEN**

Alle FR-M5-01 bis FR-M5-24 sind in Spec, Code und Tests abgebildet.

| FR | Status | Evidence |
|----|--------|----------|
| FR-M5-01..FR-M5-18 | COVERED | Spec → Domain/Infra → Tests |
| FR-M5-19 (Textlimit 500K) | COVERED | `MAX_TEXT_LENGTH = 500_000`, Test `test_text_too_large_raises` |
| FR-M5-20 (Regex-Timeout) | COVERED | `ThreadPoolExecutor` + `future.result(timeout=5.0)` |
| FR-M5-21 (DeadlineExtractor ABC) | COVERED | `application/deadline_extractor.py` |
| FR-M5-22 (human_review_required) | COVERED | Hardcoded `True` in Domain + API |
| FR-M5-23 (AMBIGUOUS_DATE) | COVERED | **Repariert**: Generierung in `_generate_warnings` + 4 Tests |
| FR-M5-24 (StrEnum) | COVERED | Alle Enums nutzen `StrEnum` |

---

## 9. Architekturverdict

**ARCH_PASS**

- Domain (`deadline.py`): Nur `dataclasses`, `datetime`, `StrEnum`. Keine Framework-Abhängigkeit.
- Application (`deadline_extractor.py`): `DeadlineExtractor(ABC)` Port. Konsistent mit M2-M4 Mustern.
- Infrastructure (`deterministic_deadline_extractor.py`): Implementiert Port.
- API: Pydantic-Schemas in `deadline_schemas.py`, Endpunkt in `document_routes.py`.
- Dependency Injection: `app.py` registriert `DeterministicDeadlineExtractor`.
- Keine unnötigen Abstraktionsschichten. Keine Rule-Engine-Zweitebene.

---

## 10. Confidence-/Certainty-Bewertung

**PASS**

- `DeadlineCertainty(StrEnum)` = `EXACT / UNRESOLVED / AMBIGUOUS`
- Diskrete Semantik, kein numerischer Pseudo-Confidence-Score
- API-Feld `certainty` (nicht `confidence`)
- Kein Risiko falscher statistischer Sicherheit

---

## 11. Regex- und ReDoS-Bewertung

**PASS — alle 6 Patterns ReDoS-safe**

| Rule | Pattern | Risiko | Bewertung |
|------|---------|--------|-----------|
| R1 | Numeric dates | Niedrig | Negated char classes, bounded `{1,4}` |
| R2 | Textual dates | Niedrig | Mutually exclusive alternation |
| R3 | Relative numeric | Niedrig | Distinct literal prefixes, `\d+` bounded by context |
| R4 | Relative article | Niedrig | Distinct literal prefixes |
| R5 | Fristkontext prefix | Niedrig | Bounded `{1,2}`, lookahead only |
| R6 | Qualitative | Sehr niedrig | Nur Literal-Alternation, keine Quantifizierer |

**Timeout:** `ThreadPoolExecutor(max_workers=1)` + `future.result(timeout=5.0)` = echter Timeout.

---

## 12. Eingabegrenzen

**PASS**

- `MAX_TEXT_LENGTH = 500_000` (≈100 Seiten)
- Geprüft vor Regex-Verarbeitung in `extract()`
- `TextTooLargeError` → API 413
- Tests: `MAX_TEXT_LENGTH` akzeptiert, `MAX_TEXT_LENGTH + 1` rejected

---

## 13. Datumsregeln

**PASS**

- R1: `31.07.2026`, `1.7.2026`, `31. 07. 2026` → erkannt
- R2: `31. Juli 2026`, alle 12 Monate → erkannt
- Ungültig: `31.02.2026` → `AMBIGUOUS_DATE` (vorher still geskippt, jetzt repariert)
- `29.02.2024` → akzeptiert (Schaltjahr), `29.02.2025` → `AMBIGUOUS_DATE`
- `00.01.2026`, `01.13.2026`, `99.99.9999` → kein Match (Regex pre-filter)
- False Positives: Versionsnummern (`v1.07.2026`) → `(?<![A-Za-z0-9])` Lookbehind

---

## 14. Relative Fristen

**PASS**

- `innerhalb von 14 Tagen` → `RELATIVE_PERIOD, amount=14, unit=Tag`
- `binnen einer Woche` → `RELATIVE_PERIOD, amount=1, unit=Woche`
- `reference_required=true`, `normalized_date=null`
- Keine Berechnung eines Enddatums
- `innerhalb von 0 Tagen`, `innerhalb von 999999 Tagen` → akzeptiert (bekannte M5-Begrenzung: keine Range-Validierung)

---

## 15. Qualitative Hinweise

**PASS**

- `unverzüglich`, `ohne schuldhaftes Zögern`, `zum nächstmöglichen Zeitpunkt`
- → `QUALITATIVE_REFERENCE, reference_required=true, normalized_date=null`
- Sätze ohne Handlungsfrist → kein False Positive (Literal-Match only)

---

## 16. Offsets

**PASS**

- Python-String-Indizes (Unicode-Codepoints) — implizit durch `str[start:end]`
- `text[c.start_offset:c.end_offset] == c.raw_text` → durch `test_consistent_output` abgedeckt
- ASCII, Umlaute, `ß`, Gedankenstrich → alle korrekt
- Dokumentation im data-model.md vermerkt

---

## 17. Deduplizierung und Sortierung

**PASS**

- Deduplizierung via `start_offset` (erster Treffer bleibt)
- Sortierung: `start_offset ASC`
- Deterministisch: `test_consistent_output` prüft bytegenaue Reproduzierbarkeit

---

## 18. Warncodes

| Code | Status |
|------|--------|
| `LEGAL_CALCULATION_NOT_PERFORMED` | Garantiert in jeder Antwort |
| `NO_DEADLINE_CANDIDATE` | Bei `len(candidates) == 0` |
| `MULTIPLE_DEADLINE_CANDIDATES` | Bei `len(candidates) > 1` |
| `RELATIVE_REFERENCE_REQUIRED` | Bei `any(c.reference_required)` |
| `AMBIGUOUS_DATE` | **Repariert**: Bei kalendarisch ungültigen Daten |

---

## 19. Human Review

**PASS — strukturell garantiert**

- Domain: `human_review_required: bool = True` (Default, nie überschrieben)
- API: `human_review_required: bool = True`
- Technisch: Kein Codepfad setzt den Wert auf `False`

---

## 20. API-Contract

**PASS**

| Case | HTTP | Error Code | Status |
|------|------|------------|--------|
| Erfolg | 200 | — | ✅ |
| Dokument nicht gefunden | 404 | `DOCUMENT_NOT_FOUND` | ✅ |
| Text zu groß (>500K) | 413 | `TEXT_TOO_LARGE` | ✅ |
| Regex-Timeout | 500 | `EXTRACTION_TIMEOUT` | ✅ |
| Ungültige UUID | ≥400 | Validation error | ✅ |

---

## 21. Logging und Datenschutz

**PASS**

- Kein `print()` oder `logging` von Dokumenttext
- `raw_text` im API-Ergebnis: nur konkrete Fundstelle (Data Minimization)
- Keine Stacktraces in Fehlerantworten (zentrale Exception-Handler)
- Keine Persistenz der Kandidaten (Analyse-on-demand)

---

## 22. Security

**SECURITY CLEAN**

- ReDoS: Alle Patterns sicher (siehe §11)
- Timeout: Echter ThreadPoolExecutor-Timeout
- Textlimit: 500K enforced
- Keine externen Requests
- Keine Secrets im Code
- 127.0.0.1 Binding

---

## 23. Compliance

**COMPLIANCE CLEAN**

- Keine verbindliche Rechtsfristberechnung
- Keine Rechtsberatungsbehauptung
- Keine falsche Sicherheit (discrete certainty + mandatory warnings)
- Relative Angaben bleiben ungelöst
- Human Review zwingend (strukturell)
- `LEGAL_CALCULATION_NOT_PERFORMED` immer sichtbar

---

## 24. Testqualitätsprüfung

**PASS**

- Positive Tests: Alle 6 Regeln abgedeckt
- Negative Tests: Ungültige Daten, False Positives (Versionsnummern)
- Offset-Tests: Deduplizierung, Sortierung, Konsistenz
- Warncode-Tests: Alle 5 Codes geprüft
- API-Tests: Erfolg, 404, Schema-Validierung, Error Envelopes
- Regex-Safety: Backtracking-Test, Partial-Date-Test
- Mutationsresistenz: Ein leerer Extractor würde erkannt, falsche Offsets würden erkannt, fehlendes Human-Review-Flag würde erkannt

---

## 25. Findings

### Behoben während Stufe 2

| Severity | Finding | Fix |
|----------|---------|-----|
| MAJOR | MISSING_AMBIGUOUS_DATE_WARNING — Warncode nie emittiert | Implementiert + 4 Tests |
| MINOR | STALE_RUN_REPORT_NUMBERS — "20 Dateien" vs 18 | Run Report korrigiert |
| MINOR | UNDEFINED_ABBREVIATION — "LCPN" in PR | PR-Beschreibung korrigiert |
| MINOR | TERMINOLOGY_INCONSISTENCY — "confidence" vs "certainty" | Run Report korrigiert |
| NOTE | TYPO — "Zutellungsfiktion" | PR-Beschreibung korrigiert |
| NOTE | OFFSET_SEMANTICS — nicht explizit dokumentiert | Im data-model.md bereits vermerkt |

### Offen

Keine Critical oder Major Findings offen.

---

## 26. Durchgeführte Reparaturen

1. `deterministic_deadline_extractor.py`:
   - `_extract_numeric_dates()` → Rückgabe `(list, bool)`, trackt `has_ambiguous`
   - `_extract_textual_dates()` → ebenso
   - `_extract_impl()` → aggregiert `has_ambiguous_dates`
   - `_generate_warnings()` → neuer Parameter `has_ambiguous_dates`, emittiert `AMBIGUOUS_DATE`

2. `tests/unit/test_deadline_extractor.py`:
   - 4 neue Tests für AMBIGUOUS_DATE (ungültiges Kalenderdatum, ungültiger Tag, valides Datum kein Warning, textuelles ungültiges Datum)
   - 1 Test aktualisiert (31.13 → 31.04 für regex-kompatiblen Test)

3. `docs/reports/M5-deadline-candidates.md`: Dateizahl, Testzahlen, Coverage, Terminologie korrigiert

4. PR #2 Body: Typos, Abkürzungen, Zahlen aktualisiert

---

## 27. Remote-Verifikation

| Check | Result |
|-------|--------|
| Local SHA | `ad017c56ce55bbfd38d5267585a78daf1e3fd576` |
| Remote SHA | `ad017c56ce55bbfd38d5267585a78daf1e3fd576` |
| Match | ✅ |
| PR Status | OPEN, READY FOR REVIEW, MERGEABLE |
| GitHub Actions | 0 runs |

---

## 28. Empfohlene Merge-Methode

**SQUASH MERGE**

Begründung: 3 Commits bilden einen unteilbaren Feature-Slice. Ein Squash-Commit hält den `main`-Verlauf sauber.

Empfohlener Squash-Titel:
```
feat(deadlines): add deterministic deadline candidate extraction (#2)
```

---

## 29. Was kann M5 jetzt?

1. Explizite Datumsangaben (TT.MM.JJJJ, geschriebene Monate) erkennen und als ISO-Datum normalisieren
2. Relative Fristformulierungen als ungelöste Kandidaten mit `reference_required=true` markieren
3. Qualitative Referenzen ("unverzüglich", "fristgerecht") erkennen
4. Fundstellen mit Offsets, Regel-IDs und Originaltext dokumentieren
5. Kalendarisch ungültige Daten als `AMBIGUOUS_DATE` warnen
6. Warncodes deterministisch und vollständig generieren
7. Alle Ergebnisse mit `human_review_required=true` Hard-Gate ausliefern
8. Textlimit (500K) und Regex-Timeout (5s) durchsetzen

---

## 30. Was kann M5 ausdrücklich nicht?

- Keine verbindliche Rechtsfristberechnung
- Keine Feiertags- oder Wochenendlogik
- Keine Zustellungsfiktion
- Keine relativen Fristen ohne Bezugspunkt auflösen
- Keine Rechtsberatung
- Keine Frontend-Integration
- Keine Cloud-Dienste

---

## 31. Nächster Owner-Schritt

Der Eigentümer reviewt PR #2 und entscheidet über den Merge (Squash Merge empfohlen).
Issue #1 bleibt bis zum Merge offen.

---

## 32. Verpflichtende Schlussdeklaration

```
PR #2 vollständig geprüft:             JA
PR-Diff-Dateien geprüft:               18
Base-Gates reproduziert:               JA
PR-Gates reproduziert:                 JA
Spec-Kit:                              SPEC_GREEN
Architektur:                           ARCH_PASS
Security:                              CLEAN
Compliance:                            CLEAN
Critical Findings offen:              0
Major Findings offen:                 0
PR-Branch aktualisiert:                JA
Feature-Branch gepusht:                JA
GitHub Actions ausgeführt:             NEIN
PR aus Draft genommen:                 JA
Auto-Merge aktiviert:                  NEIN
PR gemergt:                            NEIN
Issue #1 geschlossen:                  NEIN
Merge-Empfehlung:                      SQUASH
Finaler Status:                        MERGE_READY_AWAITING_OWNER_APPROVAL
```
