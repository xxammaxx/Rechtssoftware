# M6-A PR #5 — Independent Implementation Review

## Status: READ_ONLY_FINDINGS_COMPLETE → REPAIR_IN_PROGRESS

**Date:** 2026-07-16
**Reviewer:** Hermes Agent (independent review gate)
**Base SHA:** d51d6b3895e54c0cd3a102b8735916e3e846a142
**Head SHA:** f1447e6cdd868e59b090ec23308eb50cb2052407

---

## Read-Only Findings

### [CRITICAL] F-01 — Foreign Key und CASCADE DELETE fehlen

**Kategorie:** Persistence / Security
**Merge-Blocker:** Ja

**Beobachtung:** `sqlite_event_repository.py` Zeile 21 definiert `document_id TEXT NOT NULL` ohne `REFERENCES documents(document_id) ON DELETE CASCADE`. Der Spec (data-model.md:303) und ADR-002 (Zeile 87/100) fordern beides. `PRAGMA foreign_keys = ON` ist in `get_connection()` aktiv — aber die Constraint fehlt in der Tabellendefinition.

**Risiko:** Dokumentlöschung hinterlässt verwaiste Bestätigungsdatensätze. INV-M6A-DP-02 ist nicht technisch erfüllt.

---

### [CRITICAL] F-03 — Status und Methode vermischt ("superseded_marked")

**Kategorie:** Domain / Persistence
**Merge-Blocker:** Ja

**Beobachtung:** `sqlite_event_repository.py` Zeilen 69/85 schreiben `"superseded_marked"` in die Spalte `confirmation_method`. Dies ist kein gültiger `ConfirmationMethod`-Wert (erlaubt: `auto_suggested`, `manually_entered`, `corrected`). Ein Statuswert wird in eine Methodenspalte geschrieben — semantische Vermischung.

**Reproduktion:** `sqlite_event_repository.py:74` — `"superseded_marked"` als confirmation_method-Value; `_row_to_domain:216-218` — versucht dies mit Fallback auf `AUTO_SUGGESTED` abzufangen.

---

### [CRITICAL] F-04 — candidate_index wird in SQL-Abfragen ignoriert

**Kategorie:** Persistence
**Merge-Blocker:** Ja

**Beobachtung:** `get_active(document_id, candidate_index)` (Zeile 132) und `get_by_candidate_index(document_id, candidate_index)` (Zeile 169) nehmen `candidate_index` als Parameter entgegen, filtern aber nur nach `document_id`. Der `candidate_index` wird in keiner WHERE-Klausel verwendet.

**Risiko:** Confirmation-Abruf über Dokument- und Kandidatengrenzen hinweg. Ein Confirmation für Kandidat 0 kann als aktiv für Kandidat 1 ausgegeben werden.

---

### [CRITICAL] F-05 — Instabile Candidate-IDs (uuid4 pro Aufruf)

**Kategorie:** API / Domain
**Merge-Blocker:** Ja

**Beobachtung:** `event_routes.py:112,127` — `candidate_id=uuid4()` erzeugt bei jedem GET /reference-events neue UUIDs. Kein deterministisches Canonicalization-Schema.

**Risiko:** Client kann Candidate-IDs nicht über Aufrufe hinweg referenzieren. Confirm mit gespeicherter Candidate-ID schlägt fehl. TV-048 (deterministische Ausgabe) ist für die API-Ebene verletzt.

---

### [CRITICAL] F-06 — case_id wird nicht gegen Dokument geprüft

**Kategorie:** Security / API
**Merge-Blocker:** Ja

**Beobachtung:** `_validate_candidate_access()` prüft Document-Existenz und Candidate-Index, ignoriert aber `case_id` vollständig. Dokument aus Fall A ist unter Fall-B-URL erreichbar.

**Risiko:** Cross-Case-Zugriff. Ein Dokument kann über jede beliebige case_id-URL angesprochen werden.

---

### [CRITICAL] F-09 — Calculation Preview akzeptiert falschen Kontext

**Kategorie:** Security / Application
**Merge-Blocker:** Ja

**Beobachtung:** `event_routes.py:441` lädt Confirmation nur über `_repo.get_by_id(confirmation_id)`. Keine Prüfung auf Document-Zugehörigkeit, Candidate-Index, Status oder Widerruf.

**Risiko:** Confirmation aus Dokument A kann für Berechnung in Dokument B verwendet werden. Widerrufene Confirmation kann berechnet werden.

---

### [CRITICAL] F-16 — API greift direkt auf _repo zu

**Kategorie:** Architecture
**Merge-Blocker:** Ja

**Beobachtung:** `event_routes.py:223` — `event_service._repo.get_by_id(body.confirmation_id)`; `event_routes.py:441` — `event_service._repo.get_by_id(body.confirmation_id)`. Die API-Route umgeht den Service-Layer und greift direkt auf private Repository-Interna zu.

---

### [MAJOR] F-02 — Kein confirmation_status-Feld auf ConfirmedReferenceEvent

**Kategorie:** Domain
**Merge-Blocker:** Nein (Spec konform, aber fragile implizite Zustandsverfolgung)

**Beobachtung:** `ConfirmedReferenceEvent` hat kein `confirmation_status`-Feld. Status wird implizit über `confirmed_date`-Nullability und `supersedes_confirmation_id` abgeleitet. Die Spec zeigt ebenfalls kein Statusfeld — aber die Implementierung wäre mit einem expliziten Feld robuster.

---

### [MAJOR] F-07 — Revoke setzt EventType.UNKNOWN

**Kategorie:** Domain
**Merge-Blocker:** Nein

**Beobachtung:** `event_service.py:115` — `event_type=EventType.UNKNOWN` bei Revoke. Der ursprüngliche EventType des widerrufenen Ereignisses geht verloren.

---

### [MAJOR] F-08 — History entfernt SUPERSEDED-Datensätze

**Kategorie:** Persistence
**Merge-Blocker:** Ja (Audit-Trail unvollständig)

**Beobachtung:** `get_by_candidate_index` (Zeile 190-193) überspringt Zeilen mit `method == "superseded_marked"`. SUPERSEDED-Datensätze erscheinen nicht in der History. Der Audit-Trail ist unvollständig.

---

### [MAJOR] F-10 — calculation_id wird verworfen und neu generiert

**Kategorie:** Application
**Merge-Blocker:** Nein

**Beobachtung:** Service erzeugt `calculation_id` (Zeile 203), Arithmetic setzt sie auf `None` (deterministic_calendar.py:102), API-Route erzeugt neue `uuid4()` (event_routes.py:546). Dreifache ID-Generierung, keine Provenienz.

---

### [MAJOR] F-11 — Duration-Grenze prüft amount statt calendar_days

**Kategorie:** Domain
**Merge-Blocker:** Nein (Spec-konform, aber semantisch inkorrekt)

**Beobachtung:** `Duration.__post_init__:209` prüft `amount > 36500`. 5200 Wochen (36.400 Tage) passieren die Prüfung, weil `amount=5200 < 36500`. Eine Wochengrenze von 36500/7 ≈ 5214 wäre korrekt, aber die Prüfung sollte auf `calendar_days` basieren.

---

### [MAJOR] F-12 — OverflowError in _add_days_impl nicht abgefangen

**Kategorie:** Infrastructure
**Merge-Blocker:** Nein

**Beobachtung:** `_add_days_impl` (Zeile 135-137) ruft `timedelta(days=days)` ohne try/except. Bei `days > 10^9` kann dies `OverflowError` auslösen, bevor die Bereichsprüfung (die bei 36500 greift) erreicht wird. Im aktuellen Code wird der Wert durch `Duration.__post_init__` auf ≤36500 begrenzt — Overflow tritt erst ab ~10^9 Tagen auf. Das Risiko ist gering.

---

### [MAJOR] F-13 — API-Core-Tests werden übersprungen (10 skips)

**Kategorie:** Test
**Merge-Blocker:** Ja (10 von 14 API-Tests übersprungen)

**Beobachtung:** Alle 10 Skips stammen aus `test_event_api.py`. Ursache: Pseudo-PDF-Fixtures liefern keinen parsebaren Textlayer, M5-Extraktion findet keine RELATIVE_PERIOD-Kandidaten, `pytest.skip()` wird aufgerufen.

---

### [MAJOR] F-14 — Platzhaltertest (pass)

**Kategorie:** Test
**Merge-Blocker:** Nein

**Beobachtung:** `test_event_api.py:338` — `pass` für `test_unsupported_duration_unit`.

---

### [MINOR] F-15 — Logging-Redaktion fehlt

**Kategorie:** Compliance
**Merge-Blocker:** Nein

**Beobachtung:** INV-M6A-21 und INV-M6A-DP-08 sind nicht technisch erfüllt. Kein Logging-Filter im Code.

---

### [MINOR] F-17 — Error-Envelope weicht vom Bestand ab

**Kategorie:** API
**Merge-Blocker:** Nein

**Beobachtung:** M6-A verwendet `{"detail": {"code": ..., "message": ...}}`, während bestehende Routes (document_routes.py, app.py) `{"error": {"code": ..., "message": ...}}` verwenden. FR-M6A-028 fordert Nutzung bestehender Envelopes. Die Spec (contracts/api.md:377) zeigt `detail` — dies ist ein Spec/Code-Widerspruch, der durch FR-M6A-028 zugunsten des Bestands aufgelöst wird.

---

## Findings Summary

| ID | Severity | Merge-Blocker | Category |
|----|----------|---------------|----------|
| F-01 | CRITICAL | Ja | Persistence/Security |
| F-03 | CRITICAL | Ja | Domain/Persistence |
| F-04 | CRITICAL | Ja | Persistence |
| F-05 | CRITICAL | Ja | API/Domain |
| F-06 | CRITICAL | Ja | Security/API |
| F-09 | CRITICAL | Ja | Security/Application |
| F-16 | CRITICAL | Ja | Architecture |
| F-02 | MAJOR | Nein | Domain |
| F-07 | MAJOR | Nein | Domain |
| F-08 | MAJOR | Ja | Persistence |
| F-10 | MAJOR | Nein | Application |
| F-11 | MAJOR | Nein | Domain |
| F-12 | MAJOR | Nein | Infrastructure |
| F-13 | MAJOR | Ja | Test |
| F-14 | MAJOR | Nein | Test |
| F-15 | MINOR | Nein | Compliance |
| F-17 | MINOR | Nein | API |

**7 Critical, 2 Major merge-blocking → 9 merge-blocking findings total.**
