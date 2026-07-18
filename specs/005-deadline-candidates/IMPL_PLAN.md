# Implementation Plan — M5 Deadline Candidate Extraction

## Feature Overview

| | |
|---|---|
| **Feature** | M5 — Deterministische Erkennung von Fristkandidaten aus lokal extrahiertem Dokumenttext |
| **Milestone** | M5 |
| **Risk Tier** | LOW_LOCAL (rein lokal, keine Persistenz, keine externen APIs) |
| **Spec** | `specs/005-deadline-candidates/spec.md` |

---

## Technical Context

### Stack

- **Language:** Python 3.11+
- **Framework:** FastAPI (bestehend)
- **Persistence:** Analyse-on-demand (keine neuen Tabellen)
- **Extraction Engine:** Python `re` (regex) + `datetime` (Validierung)
- **Thread Safety:** Zustandsloser, reentranter Extractor (FR-M5-26)
- **Timeout:** `threading.Timer` mit 5s-Limit (FR-M5-21) — vollständiger Abbruch, keine Partialergebnisse
- **Text Limit:** 500.000 Zeichen vor Verarbeitung (FR-M5-19)
- **R5 Prefix Proximity:** 50 Zeichen rückwärts vom Match-Start
- **Dedup Strategy:** Containment-basiert (vollständige Umschließung), Priorität EXPLICIT_DATE > RELATIVE_PERIOD > QUALITATIVE_REFERENCE
- **Logging:** `logging.getLogger("private_legal_navigator")` auf INFO-Level
- **Unexpected Exceptions:** Alle → HTTP 500 INTERNAL_ERROR

### Architecture Layer (modularer Monolith)

```
API Layer (FastAPI Routes)
  → Application Layer (DeadlineService)
    → Domain Layer (DeadlineCandidate, DeadlineWarning, StrEnum)
      → Infrastructure Layer (DeterministicDeadlineExtractor → regex → datetime)
```

### Dependencies

**Keine neuen externen Abhängigkeiten.** Alle benötigten Module sind Python-Standard:
`re`, `datetime`, `threading`, `dataclasses`, `enum`, `abc`

Bestehende Projekt-Abhängigkeiten (unverändert): FastAPI, pydantic, SQLite.

---

## Constitution Check

| Prinzip | Status | Umsetzung |
|---------|--------|-----------|
| §1 Local-only | ✅ Local-only | FR-M5-17: Keine Netzwerkverbindung |
| §2 Privacy by Design | ✅ Privacy | FR-M5-18, FR-M5-25: Keine vollständigen Texte in Logs; Diagnostic Level |
| §3 Keine automatische Rechtsentscheidung | ✅ Manual Review | `human_review_required: true` (FR-M5-23), Warncodes statt Berechnung |
| §4 Human Review | ✅ Required | Jeder Kandidat erfordert menschliche Prüfung |
| §5 Modularer Monolith | ✅ Layers | API → Application → Domain → Infrastructure |
| §6 Kleine vertikale Slices | ✅ Vertical Slice | Vollständiger Durchstich: Route → Service → Domain → Infra |
| §7 Red Tests vor Feature | ✅ (geplant) | T5.x-Tests vor Implementierung |
| §8 Lokale Gates | ✅ Local-first | Nur lokale Tests, kein Remote-CI |
| §9 Keine Remote-CI | ✅ | Nicht konfiguriert |
| §10 Evidence vor Erfolgsmeldung | ✅ Verifiable | Deterministische Ergebnisse, reproduzierbar |
| §11 Living Truth Mirror | ✅ Docs updated | data-model.md, contracts/api.md, tasks.md aktualisiert |
| §12 Synthetische Testdaten | ✅ Synthetic | FR-M5-20: Keine Produktivdaten in Tests |

**Gate: ✅ Bestanden** — Keine Verstöße gegen die Constitution.

---

## Architecture Decisions

| ID | Decision | Reference |
|----|----------|-----------|
| ADR-M5-01 | **Deterministic Regex** statt ML/LLM | `research.md` §1 |
| ADR-M5-02 | **Analyse-on-demand** statt Persistenz | `research.md` §2 |
| ADR-M5-03 | **R5 Post-Processing-Enrichment** | `research.md` §3, FR-M5-28 |
| ADR-M5-04 | **Thread-safe by Design** (stateless) | `research.md` §4, FR-M5-26 |
| ADR-M5-05 | **Regex + strptime** für Datumsvalidierung | `research.md` §5 |
| ADR-M5-06 | **Hardcoded German Months** (kein locale) | `research.md` §6 |
| ADR-M5-07 | **Diagnostic Logging** (50-Zeichen-Kürzung) | `research.md` §7, FR-M5-25 |
| ADR-M5-08 | **Certainty-Mapping** (exact/unresolved/ambiguous) | `research.md` §8, FR-M5-27 |
| ADR-M5-09 | **Timeout-Recovery** — vollständiger Abbruch, keine Partialergebnisse | `research.md` §9, FR-M5-21 |
| ADR-M5-10 | **R5-Prefix-Proximity** — 50 Zeichen rückwärts | `research.md` §10, FR-M5-28 |
| ADR-M5-11 | **Dedup-Strategy** — Containment-basiert mit Priorität | `research.md` §11, FR-M5-12 |
| ADR-M5-12 | **Logging-Destination** — Application-Logger | `research.md` §12, FR-M5-25 |
| ADR-M5-13 | **Unexpected Exceptions** — INTERNAL_ERROR | `research.md` §13 |

---

## Phase Breakdown

> **Constitution §7:** Tests werden vor Implementierung ausgeführt. Die Test-Tasks
> aus Phase 5 (T5.1 für Domain, T5.2–T5.8 für Rule Engine, T5.9 für Service,
> T5.10 für API) müssen **vor** dem jeweils ersten Task der zugehörigen
> Implementierungs-Phase grün sein. Siehe `tasks.md` für die Ausführungsreihenfolge.

### Phase 1: Domain Models + Port

Implementierung der Domain-Entitäten und des Application-Ports.
- Datei: `src/private_legal_navigator/domain/deadline.py`
- Datei: `src/private_legal_navigator/application/deadline_extractor.py`

| Task | Prio | Acceptance |
|------|------|------------|
| T1.1–T1.6: Domain-Dataclasses und Enums | P0 | StrEnum-Basis, __post_init__-Validierung, Felder gemäß data-model.md |
| T1.7: DeadlineExtractor(ABC) Port | P0 | `extract(text: str) -> DeadlineExtractionResult` |

### Phase 2: Rule Engine (Infrastructure)

Implementierung der 6 Regeln (R1–R6), Deduplizierung, Sortierung, Warnungen.
- Datei: `src/private_legal_navigator/infrastructure/deterministic_deadline_extractor.py`

| Task | Prio | Acceptance |
|------|------|------------|
| T2.1: Grundgerüst | P0 | Klasse implementiert DeadlineExtractor(ABC) |
| T2.2: R1 — Numerisches Datum | P0 | Regex + strptime-Validierung, Normalisierung |
| T2.3: R2 — Ausgeschriebene Monate | P0 | Hardcoded Monatsdict, datetime.date |
| T2.4: R3 — Relative Zeiträume mit Zahl | P0 | kind=RELATIVE_PERIOD, amount=N, reference_required=true |
| T2.5: R4 — Relative Zeiträume mit Artikel | P0 | kind=RELATIVE_PERIOD, amount=1, reference_required=true |
| T2.6: R6 — Qualitative Referenzen | P1 | kind=QUALITATIVE_REFERENCE, reference_required=true |
| T2.7: R5 — Fristkontext-Präfix (Post-Processing-Enrichment) | P0 | Präfix-Suche max. 50 Zeichen rückwärts, raw_text erweitern, start_offset anpassen |
| T2.8: Deduplizierung + Sortierung | P0 | Containment-basiert (vollständige Offset-Umschließung), Priorität EXPLICIT_DATE > RELATIVE_PERIOD > QUALITATIVE_REFERENCE, nach start_offset sortieren |
| T2.9: Warnung-Generierung | P0 | 5 Warncodes gemäß spec.md |
| T2.10: Textlimit + Timeout | P0 | 500K Zeichen Limit vor Verarbeitung; threading.Timer 5s — **vollständiger Abbruch**, keine Partialergebnisse in candidates |
| T2.11: Logging | P0 | Diagnostic Level über `logging.getLogger("private_legal_navigator")` auf INFO-Level |
| T2.12: Exception Safety | P0 | Alle unerwarteten Regex-Exceptions fangen → HTTP 500 INTERNAL_ERROR |

### Phase 3: Application Service

Orchestriert DocumentRepository + DeadlineExtractor.
- Datei: `src/private_legal_navigator/application/deadline_service.py`

| Task | Prio | Acceptance |
|------|------|------------|
| T3.1: DeadlineService Klasse | P0 | Nutzt DocumentRepository + DeadlineExtractor |
| T3.2: Dokument laden und Text prüfen | P0 | DocumentNotFound, kein Text → Warnung |
| T3.3: Extraktion delegieren | P0 | Korrektes DeadlineExtractionResult |

### Phase 4: API Integration

Endpunkt und Response-Schemas.
- Datei: `src/private_legal_navigator/api/routes/document_routes.py`

| Task | Prio | Acceptance |
|------|------|------------|
| T4.1: Pydantic Response-Schemas | P0 | DeadlineCandidateResponse, DeadlineExtractionResponse, etc. |
| T4.2: POST-Endpunkt | P0 | `POST /cases/{cid}/documents/{did}/deadline-candidates` |
| T4.3: Dependency Injection | P0 | Extractor und Service in app.py registrieren |
| T4.4: Fehlerbehandlung | P0 | 404, 413, 500 gemäß API-Contract |

### Phase 5: Tests

```powershell
.venv/Scripts/python.exe -m pytest --cov=src/private_legal_navigator --cov-fail-under=90
.venv/Scripts/python.exe -m ruff check src tests
.venv/Scripts/python.exe -m mypy src
```

| Task | Prio | Umfang |
|------|------|--------|
| T5.1: Domain Unit Tests | P0 | __post_init__, Enums, defaults |
| T5.2–T5.6: Rule Engine Tests | P0 | Positive + negative + edge cases aller 6 Regeln |
| T5.7: Edge Cases | P0 | Leerer Text, lange Texte, Überlappungen |
| T5.8: Regex-Sicherheit | P1 | Catastrophic backtracking, Timeout |
| T5.9: Application Service Tests | P0 | Dokument laden, Fehlerfälle |
| T5.10: API Integration Tests | P0 | 200, 404, 413, leere/mehrere Kandidaten |
| T5.11: Regression Tests | P0 | Alle 83+ bestehenden Tests grün |

### Phase 6: Quality Gates + Documentation

| Task | Prio | Acceptance |
|------|------|------------|
| T6.1: pytest (alle Tests) | P0 | Alle Tests grün |
| T6.2: Coverage ≥ 90% | P0 | pytest --cov-fail-under=90 |
| T6.3: Ruff check | P0 | Keine Fehler |
| T6.4: Mypy check | P0 | Keine Fehler |
| T6.5: Architekturdokumentation | P1 | docs/architecture/architecture.md |
| T6.6: README | P1 | M5-Status und API-Endpunkt |
| T6.7: M5-Abschlussbericht | P1 | docs/reports/M5-deadline-candidates.md |

---

## Risk Assessment

| Risiko | Gegenmaßnahme |
|--------|---------------|
| Catastrophic Backtracking | 5s Timeout (FR-M5-21) + 500K Zeichenlimit (FR-M5-19); vollständiger Abbruch bei Timeout |
| Falsche Offsets durch R5-Enrichment | start_offset wird explizit angepasst; 50-Zeichen-Proximitätsgrenze (Clarification) |
| Ungültige Kalenderdaten | datetime.strptime()-Validierung vor Kandidaten-Erzeugung |
| Privacy-Leak in Fehlerantworten | Keine Dokumenttexte, Stacktraces oder Pfade in Responses |
| Nicht-thread-sichere Zustände | Explizit thread-safe by Design (FR-M5-26) |
| False Positives durch R5-Präfix | 50-Zeichen-Limit reduziert Risiko; Testabdeckung für Präfix-Kombinationen |
| Partial-Ergebnisse bei Abbruch | Vollständiger Abbruch garantiert — entweder vollständige oder leere Kandidatenliste |

---

## Gates

| Gate | Status | Details |
|------|--------|---------|
| Spec Complete | ✅ | spec.md + 2 Clarification Sessions (9 Q&A) |
| Constitution Check | ✅ | Alle 12 Prinzipien eingehalten |
| Research Complete | ✅ | research.md (13 Design Decisions) |
| Data Model Complete | ✅ | data-model.md (incl. R5-Datenfluss, Dedup-Strategie) |
| Contracts Complete | ✅ | contracts/api.md |
| Quickstart Validated | ✅ | quickstart.md |
| Tasks Defined | ✅ | tasks.md (76 tasks, 6 Phasen) |
| Spec Quality Checklist | ✅ | checklists/spec-quality.md (40 Items) |
| Verification Contract | 🔲 | Vor Implementierung zu erstellen |
| Red Tests Passing | 🔲 | Phase 5 |
| Owner Approval | 🔲 | Vor Commit erforderlich |
| All Tests Green | 🔲 | Phase 6 |
| Documentation Updated | 🔲 | Phase 6 |

---

## Nächste Schritte

1. `/speckit.clarify` — Session 1 (abgeschlossen, 4 Fragen)
2. `/speckit.clarify` — Session 2 (abgeschlossen, 5 Fragen)
3. `/speckit.plan` (diese Datei — abgeschlossen)
4. `/speckit.checklist` (abgeschlossen — checklists/spec-quality.md)
5. `/speckit.taskstoissues` (GitHub Issues erstellen)
6. Verification Contract erstellen
7. Red Tests schreiben (Phase 5)
8. Implementierung (Phasen 1–4)
9. Quality Gates (Phase 6)
