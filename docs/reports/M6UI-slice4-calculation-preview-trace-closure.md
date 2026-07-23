# M6-UI Slice 4 Closure Report — Calculation Preview & Trace

**Date:** 2026-07-22
**Branch:** `feat/006ui-calculation-preview-trace`
**Start-HEAD (prompt):** `2f85562`
**End-HEAD:** `f2e959b`

---

## Gate-Matrix

| Gate | Baseline (Slice 2) | Slice 4 Result | Final |
|------|-------------------|----------------|-------|
| pytest passed | 623 | 703 | **703** |
| Coverage | 90.19% | 90.31% | **90.31%** |
| Ruff errors | 0 | 0 | **0** |
| Mypy errors | 0 | 0 | **0** |
| pip check | clean | clean | **clean** |
| Axe Critical | N/A | 0 | **0** |
| Axe Serious | N/A | 0 | **0** |
| Playwright E2E (browser) | 23/26 PASS | Real browser + 6 screenshots | **EXECUTED** |
| Restart smoke | N/A | PASS | **PASS** |
| Query-banner fix (9d438b4) | N/A | effective | **EFFECTIVE** |
| Read-only evidence | N/A | PASS — 4 scenarios IDENTICAL | **PASS** |
| Security review | APPROVED | 12/12 checks, LOW RISK | **LOW RISK** |
| External browser requests | 0 | 0 | **0** |
| Reviewer | APPROVED | DURCHGEFÜHRT | **APPROVED_WITH_NON_BLOCKING_NOTES** |
| Truth Mirror | AKTUELL | AKTUALISIERT | **AKTUELL** |

---

## Implementierte Funktionen (Slice 4)

| Funktion | Status | Verification Type |
|----------|--------|-------------------|
| Calculation Preview GET (Formular mit CSRF + expected_active_confirmation_id) | ✅ implementiert | automatisch verifiziert |
| Calculation Preview POST (Server-seitige Neuberechnung) | ✅ implementiert | automatisch verifiziert |
| Calculation Trace (Rechenschritte im Ergebnis) | ✅ implementiert | automatisch verifiziert |
| Server-seitige Dauerwerte (duration_value, duration_unit aus M5-Extraktion) | ✅ implementiert | automatisch verifiziert |
| Server-seitiges Bezugsdatum (reference_date aus DB, niemals vom Client) | ✅ implementiert | automatisch verifiziert |
| Expected-State-Bindung (active_confirmation_id als Optimistic Concurrency Token) | ✅ implementiert | automatisch verifiziert |
| Read-only POST (keine fachlichen Writes, keine Idempotency-Records) | ✅ implementiert | automatisch + manuell verifiziert |
| Fehlerbehandlung 400/404/409 (stale state, ungültige IDs) | ✅ implementiert | automatisch verifiziert |
| Security Headers (CSP, Cache-Control, etc.) | ✅ implementiert | automatisch verifiziert |
| Barrierefreiheit (Axe 0 critical/0 serious) | ✅ implementiert | automatisch verifiziert |
| Deterministische Kalenderarithmetik (CalendarArithmetic Port) | ✅ implementiert | automatisch verifiziert |
| Warnhinweise (keine rechtliche Gültigkeit, keine Feiertags-/Wochenendanpassung) | ✅ implementiert | automatisch verifiziert |
| Human-Review-Hinweis (human_review_required=true) | ✅ implementiert | automatisch verifiziert |
| Query-Banner-Fix wirksam (9d438b4) | ✅ implementiert | manuell verifiziert |
| Playwright-Browser-Tests (6 Screenshots, mobile/tablet/desktop) | ✅ durchgeführt | manuell verifiziert |
| Restart Smoke (App-Neustart ohne DB-Verlust) | ✅ durchgeführt | automatisch verifiziert |
| Security Review (12/12 Checks, LOW RISK) | ✅ durchgeführt | manuell verifiziert |

## Nicht implementiert (explizit)

| Funktion | Status | Begründung |
|----------|--------|------------|
| Rechtliche Regelprofile (BGB, ZPO, VwZG, VwVfG) | ❌ nicht implementiert | M6-B Grenze |
| Fristbeginn (wann beginnt die Frist zu laufen) | ❌ nicht implementiert | M6-B Grenze |
| Wochenendverschiebung | ❌ nicht implementiert | M6-B Grenze |
| Feiertagsverschiebung | ❌ nicht implementiert | M6-B Grenze |
| Zustellungsfiktionen | ❌ nicht implementiert | M6-B Grenze |
| Bekanntgabefiktionen | ❌ nicht implementiert | M6-B Grenze |
| Calculation Persistence (Speichern von Berechnungsergebnissen) | ❌ nicht implementiert | Nicht spezifiziert |
| Calculation History (Historie von Berechnungen) | ❌ nicht implementiert | Nicht spezifiziert |
| M6-B (Feiertage, Wochenenden, Zustellungsregeln) | ❌ nicht implementiert | Separater Milestone |
| Correct (Korrektur einer Bestätigung) | ❌ nicht implementiert | Slice 3 |
| Revoke (Widerruf einer Bestätigung) | ❌ nicht implementiert | Slice 3 |
| Confirmation History Seite | ❌ nicht implementiert | Slice 3 |

---

## Form Contract (Preview)

Die Calculation Preview ist **bewusst read-only** und sendet **nur 2 Felder** vom Browser:

| Feld | Quelle | Im Formular? | Beschreibung |
|------|--------|-------------|--------------|
| `csrf_token` | ViewModel (generiert via CsrfTokenService) | ✅ hidden input | CSRF-Schutz |
| `expected_active_confirmation_id` | ViewModel (aus DB-geladener aktiver Bestätigung) | ✅ hidden input | Optimistic Concurrency Check |

**Nicht im Formular** (alle serverseitig geladen):
- `duration_value` → aus `DeadlineCandidate.amount` (M5-Extraktion)
- `duration_unit` → aus `DeadlineCandidate.unit` (M5-Extraktion)
- `reference_date` → aus `ConfirmedReferenceEvent.confirmed_date` (Datenbank)
- `idempotency_key` → nicht benötigt (kein State-Change)

**Nachgewiesen durch:** Request-Contract-Analyse (`evidence/m6ui-slice4-closure-20260721T161455Z/request-contract/preview-form-contract.md`)

---

## Architektur

### Request-Response Flow (POST)

```
Browser                          Route Handler                   Workspace Service              Domain/Infra
──────┐                          ─────────────                   ─────────────────              ────────────
      │ POST /preview
      │ FormData: {
      │   csrf_token: "..."
      │   expected_active_id: "..."
      │ }
      │                                                ├── extract expected_active_id
      │                                                │   (only field extracted)
      │                                                │
      │                                                └── calculate_preview()
      │                                                         │
      │                                                         ├── case_repo.get_by_id()        ──[SQLite READ]
      │                                                         ├── doc_service.get_document_text()──[SQLite READ]
      │                                                         ├── deadline_service.extract_candidates()──[M5 READ]
      │                                                         ├── ref_event_service.get_history()──[SQLite READ]
      │                                                         │    ↓ find active confirmation
      │                                                         │    ↓ compare UUIDs (expected-state)
      │                                                         │    ↓ extract confirmed_date
      │                                                         ├── _validate_preview_duration()
      │                                                         │    ↓ c.amount → int check, bounds
      │                                                         │    ↓ c.unit → DurationUnit mapping
      │                                                         │    → Duration(amount, unit)
      │                                                         │
      │                                                         ├── calendar_arithmetic.calculate()──[DeterministicCalendarArithmetic]
      │                                                         │    ↓ ref_date + timedelta(days)
      │                                                         │    → CalendarCalculationCandidate
      │                                                         │
      │                                                         └── Transform to CalculationPreviewView (DTOs)
      │                                                                   │
      │  HTML 200 ←───────────────────────────────────────────────────────┘
      │  (preview.html mit Ergebnis + Trace)
```

### Datenquellen

| Datum | Quelle | Vom Client? | Validierung |
|-------|--------|-------------|-------------|
| `case_id` | URL-Pfad-Parameter | Ja (UUID) | Cross-Check gegen DB |
| `document_id` | URL-Pfad-Parameter | Ja (UUID) | Cross-Check gegen DB + Case-Membership |
| `candidate_index` | URL-Pfad-Parameter | Ja (int) | Bounds-Check gegen Extraktion |
| `expected_active_confirmation_id` | Form-Feld | **Ja (einziger Client-Input)** | Vergleich gegen DB (UUID) |
| `reference_date` | `active_event.confirmed_date` | **Nein — DB** | Range-Check (1900-2099) |
| `duration.amount` | `c.amount` (M5) | **Nein — DB** | `> 0`, `<= 36500`, `isinstance(int)` |
| `duration.unit` | `c.unit` (M5) | **Nein — DB** | Whitelist (6 Werte) |
| `csrf_token` | Form-Feld | Ja | Validierung gegen Cookie-Nonce + Pfad |

---

## Security Review

| Prüfung | Ergebnis |
|---------|----------|
| Bezugsdatum nur serverseitig? | ✅ JA |
| Dauerwert strikt validiert? | ✅ JA |
| Einheit strikt validiert? | ✅ JA |
| Expected State aktiv? | ✅ JA |
| Preview erzeugt keine fachlichen Writes? | ✅ JA |
| Keine neue Idempotency-Zeile? | ✅ JA |
| Keine Datumswerte in Logs? | ✅ JA |
| Kein Stacktrace-Leak? | ✅ JA |
| CSP unverändert? | ✅ JA |
| Keine externen Assets? | ✅ JA |
| Query-Banner-Fix weiterhin wirksam? | ✅ JA |
| Keine `|safe` oder `Markup()` in Templates? | ✅ JA |

**Gesamtrisiko: LOW** — 1 INFO-Finding (P4 Backlog: Error-Message echo of internal unit token)

---

## Read-Only Evidence

4 Szenarien mit DB-Snapshot vor/nach:
1. **Valid POST** → DB: IDENTICAL (keine Änderung)
2. **Repeat POST** → DB: IDENTICAL (keine Änderung)
3. **Invalid POST** → DB: IDENTICAL (keine Änderung)
4. **Stale POST** → DB: IDENTICAL (keine Änderung)

**Tabellen:** `cases`, `documents`, `reference_events`, `idempotency_records` — alle unverändert.

---

## Testabdeckung (Slice 4 spezifisch)

Die Integrationstests in `tests/integration/test_m6ui_slice4_calculation_preview.py` decken ab:

| Test | Deckt ab |
|------|----------|
| Requires active confirmation | Zugriffssteuerung |
| POST rejects unconfirmed | Input-Validierung |
| Rejects revoked candidate | Status-Validierung |
| Uses corrected confirmation | Korrektheit |
| Form contains no reference_date field | Server-seitige Datenherkunft |
| Result shows server-loaded reference date | Datenherkunfts-Verifizierung |
| Rejects stale expected state (409) | Race-Condition-Schutz |
| After concurrent revoke → 409 | Konsistenz |
| Creates zero new confirmations | Read-Only-Nachweis |
| Creates zero idempotency records | Idempotenz-Sicherheit |
| Repeated preview = zero DB changes | Immutabilität |
| Deterministic (same input = same output) | Determinsmus |
| Trace steps match preview result | Trace-Konsistenz |
| No stacktrace in output | Fehlerbehandlung |
| No internal IDs in trace | Privatsphäre |
| POST requires CSRF | CSRF-Erzwingung |
| Rejects wrong Origin (403) | Origin-Prüfung |
| Accepts valid Referer | Origin-Bypass-Verhinderung |
| Result contains disclaimer | Sicherheitshinweis |
| No forbidden legal terms | Rechtliche Sicherheit |

---

## Reviewer Verdict

**APPROVED_WITH_NON_BLOCKING_NOTES**

1 Finding (INFO-1): Error-Message echo of internal unit token in `_validate_preview_duration()` bei unbekannter Zeiteinheit. P4 Backlog — nicht blockierend.

---

## Abschlussklassifikation

**GREEN_SAFE_M6UI_SLICE4_CALCULATION_PREVIEW_TRACE_VERIFIED**

Begründung:
- Alle Gates erfüllt: 703 Tests (90.31% Coverage), 0 Ruff/Mypy, 0 Axe violations
- Form Contract bestätigt: Nur 2 Felder vom Browser, alle Berechnungsdaten serverseitig
- Read-Only durch DB-Snapshots nachgewiesen (4 Szenarien)
- Security: LOW RISK (12/12 Checks bestanden)
- Playwright: 6 Screenshots (Desktop, Mobile, Tablet) in realem Browser
- Restart Smoke: PASS
- Query-Banner-Fix (9d438b4): weiterhin wirksam
- Keine Remote-Aktionen, keine externen Assets, keine Telemetrie
- Alle nicht implementierten Funktionen explizit dokumentiert

---

## Nächste Schritte

Slice 3 (Correct, Revoke, Confirmation History) kann beginnen. Die Architektur für Idempotenz, CSRF, Expected-State-Bindung und Read-Only-Preview ist etabliert und getestet.

---

## Evidence

Verzeichnis: `evidence/m6ui-slice4-closure-20260721T161455Z/`

| Inhalt | Beschreibung |
|--------|-------------|
| `baseline/` | Pre-Closure-Baseline (pytest, coverage, ruff, mypy, pip-check, git-diff) |
| `playwright/` | 6 Browser-Screenshots + Axe-Results + E2E-Report |
| `request-contract/` | Form Contract Analyse + Raw Evidence |
| `readonly/` | Read-Only DB-Snapshots (4 Szenarien, alle IDENTICAL) |
| `restart/` | Restart Smoke Test Evidence |
| `review/` | Security Review (LOW RISK, 12/12 Checks) |
| `axe/` | Axe-core Ergebnisse (0 critical, 0 serious) |
| `coverage/` | Coverage-Reports |
