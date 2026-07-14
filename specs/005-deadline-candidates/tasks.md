# Tasks — M5 Deadline Candidate Extraction

## Phase 1: Domain Models + Port

| # | Task | Acceptance | Prio |
|---|------|------------|------|
| T1.1 | `domain/deadline.py`: `DeadlineCandidateKind` (StrEnum) | 3 Werte: EXPLICIT_DATE, RELATIVE_PERIOD, QUALITATIVE_REFERENCE | P0 |
| T1.2 | `domain/deadline.py`: `DeadlineCertainty` (StrEnum) | 3 Werte: EXACT, UNRESOLVED, AMBIGUOUS | P0 |
| T1.3 | `domain/deadline.py`: `DeadlineWarningCode` (StrEnum) | 5 Werte gemäß Spec | P0 |
| T1.4 | `domain/deadline.py`: `DeadlineCandidate` (dataclass) | Felder: kind, raw_text, start_offset, end_offset, normalized_date, amount, unit, reference_required, certainty, rule_id | P0 |
| T1.5 | `domain/deadline.py`: `DeadlineWarning` (dataclass) | Felder: code, message | P0 |
| T1.6 | `domain/deadline.py`: `DeadlineExtractionResult` (dataclass) | Felder: document_id, candidates, warnings, human_review_required | P0 |
| T1.7 | `application/deadline_extractor.py`: `DeadlineExtractor(ABC)` | Port mit `extract(text: str) -> DeadlineExtractionResult` | P0 |

## Phase 2: Rule Engine (Infrastructure)

| # | Task | Acceptance | Prio |
|---|------|------------|------|
| T2.1 | `infrastructure/deterministic_deadline_extractor.py`: Grundgerüst | Importe, Klasse implementiert `DeadlineExtractor(ABC)` | P0 |
| T2.2 | R1 — Numerische Datums-Regex | Erkennt TT.MM.JJJJ, validiert mit datetime.strptime, Normalisierung | P0 |
| T2.3 | R2 — Ausgeschriebene Monatsnamen | Hardcoded German month dict, validiert mit datetime.date | P0 |
| T2.4 | R3 — Relative Zeiträume mit Zahl | Erkennt "innerhalb von N Tagen", "binnen N Wochen" etc. | P0 |
| T2.5 | R4 — Relative Zeiträume mit Artikel | Erkennt "innerhalb eines Monats", "binnen einer Woche" | P0 |
| T2.6 | R6 — Qualitative Referenzen | Erkennt "unverzüglich", "ohne schuldhaftes Zögern" | P1 |
| T2.7 | Deduplizierung und Sortierung | Überlappende Treffer entfernt, nach start_offset sortiert | P0 |
| T2.8 | Warnung-Generierung | Warnungen gemäß Spec (LEGAL_CALCULATION_NOT_PERFORMED, etc.) | P0 |
| T2.9 | Textgrößenlimit und Timeout | 500K Zeichen Limit, threading Timer 5s Timeout | P0 |

## Phase 3: Application Service

| # | Task | Acceptance | Prio |
|---|------|------------|------|
| T3.1 | `DeadlineService` Klasse | Nutzt DocumentRepository + DeadlineExtractor | P0 |
| T3.2 | Dokument laden und Text prüfen | DocumentNotFound, kein Text → Warnung | P0 |
| T3.3 | Extraktion delegieren und Ergebnis formen | Korrektes Result-Objekt zurückgeben | P0 |

## Phase 4: API Integration

| # | Task | Acceptance | Prio |
|---|------|------------|------|
| T4.1 | Pydantic Response-Schemas | DeadlineCandidateResponse, DeadlineExtractionResponse, etc. | P0 |
| T4.2 | Neuer Endpunkt in document_routes.py | POST /cases/{cid}/documents/{did}/deadline-candidates | P0 |
| T4.3 | Dependency Injection im app.py | DeadlineExtractor und DeadlineService registrieren | P0 |
| T4.4 | Fehlerbehandlung | 404, 413, 500 Fehlerfälle gemäß API-Contract | P0 |

## Phase 5: Tests

| # | Task | Acceptance | Prio |
|---|------|------------|------|
| T5.1 | Domain Unit Tests | __post_init__ validation, field defaults | P0 |
| T5.2 | Rule Engine Tests — positive Fälle (numerisch) | 31.07.2026, 1.7.2026, 31. 07. 2026 | P0 |
| T5.3 | Rule Engine Tests — positive Fälle (Text monat) | 31. Juli 2026, 1. August 2026 | P0 |
| T5.4 | Rule Engine Tests — relative Perioden | "innerhalb von zwei Wochen", "binnen 14 Tagen", "innerhalb eines Monats" | P0 |
| T5.5 | Rule Engine Tests — qualitative Referenzen | "unverzüglich", "ohne schuldhaftes Zögern" | P1 |
| T5.6 | Rule Engine Tests — negative Fälle | Ungültige Daten, Aktenzeichen, Versionsnummern | P0 |
| T5.7 | Rule Engine Tests — Edge Cases | Leerer Text, sehr langer Text, überlappende Treffer, deterministische Reihenfolge | P0 |
| T5.8 | Rule Engine Tests — Regex-Sicherheit | Catastrophic backtracking Test, Timeout-Test | P1 |
| T5.9 | Application Service Tests | Dokument laden, Text analysieren, Fehlerfälle | P0 |
| T5.10 | API Integration Tests | 200, 404, 413, kein Text, mehrere Kandidaten, kein Kandidat | P0 |
| T5.11 | Regression Tests | Alle bestehenden 83 Tests müssen weiterhin grün sein | P0 |

## Phase 6: Quality Gates + Documentation

| # | Task | Acceptance | Prio |
|---|------|------------|------|
| T6.1 | pytest (alle Tests) | Alle M5 + Regression Tests grün | P0 |
| T6.2 | Coverage ≥ 90% | pytest --cov --cov-fail-under=90 | P0 |
| T6.3 | Ruff check | Keine Fehler | P0 |
| T6.4 | Mypy check | Keine Fehler | P0 |
| T6.5 | Archivektur-Dokumentation aktualisieren | docs/architecture/architecture.md | P1 |
| T6.6 | README aktualisieren | M5 Status, API-Endpunkt | P1 |
| T6.7 | M5 Abschlussbericht | docs/reports/M5-deadline-candidates.md | P1 |
