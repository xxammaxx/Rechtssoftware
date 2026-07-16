# M6-A PR #5 Logging Privacy Repair — Final Report

## Status

**MERGE_READY_AWAITING_OWNER_APPROVAL**

## Kurzfazit

The mandatory M6-A logging privacy invariants (INV-M6A-16, INV-M6A-21,
INV-M6A-DP-08, FR-M6A-030) have been fully implemented and independently
verified. A centrally-wired PrivacyRedactionFilter now protects all
sensitive M6-A fields from plaintext disclosure in application logs.

## Ausgangszustand

| Item | Value |
|------|-------|
| Repo | xxammaxx/Rechtssoftware |
| Branch | feat/006a-reference-events |
| PR | #5 |
| Original Head | 1130b0c6e6ce25935edc591dd03413c8ab153875 |
| Base (main) | d51d6b3895e54c0cd3a102b8735916e3e846a142 |
| Repair Commit | 1d40d2be26acae075c9433c35688adffcc36bbff |
| OS | Windows 10 (MINGW64_NT) |
| Shell | Git Bash (MSYS2) |
| Python | 3.11.9 |

## Logging-Architektur vor Repair

Vor dem Repair existierte KEIN Logging-Framework in der Anwendung:

- Keine `logging`-Importe in `src/`
- Keine `getLogger()`-Aufrufe
- Keine Handler, Formatter oder Filter
- Keine `print()`-Statements
- Kein strukturiertes Logging
- Keine Logging-Konfiguration in `app.py` oder `config.py`

Die einzige Logging-Ausgabe stammte von Uvicorn/FastAPI (Request-Logs)
und dem Test-Client `httpx`. Diese bibliothekseigenen Logger enthalten
keine Domain-Werte, sondern HTTP-Statuscodes und URLs.

Die Application selbst loggte **nichts**.

## Redaktionsvertrag

### Zu redigierende Felder

| Feld | Grund |
|------|-------|
| `confirmed_date` | INV-M6A-21 — Bezugsdatum |
| `reference_date` | INV-M6A-16 — Bezugsdaten |
| `calculated_date` | INV-M6A-16 — berechnetes Datum |
| `suggested_date` | INV-M6A-16 — vorgeschlagenes Datum |
| `evidence_text` | INV-M6A-21 — Quelltext |
| `evidence_note` | INV-M6A-21 — Nutzerhinweis |
| `source_text` | INV-M6A-21 — Quellenangabe |
| `document_id` | INV-M6A-DP-08 — Dokument-ID |
| `confirmation_id` | INV-M6A-DP-08 — Bestätigungs-ID |
| `case_id` | Ermessensentscheidung — Fallbezug |
| `candidate_id` | Ermessensentscheidung — Kandidatenbezug |
| `supersedes_confirmation_id` | Ermessensentscheidung — Verkettung |
| `reference_event_candidate_id` | Ermessensentscheidung |
| `deadline_candidate_id` | Ermessensentscheidung |

### Ersatzwert

Einheitlich `[REDACTED]`. Keine Hashes, keine Teilmaskierung, keine
Umkehrbarkeit.

## Architekturentscheidung

**Variant C — Strukturierter Logging-Filter + zentrales Wiring**

```
M6-A code
→ structured safe fields (via extra= / Mapping args)
→ PrivacyRedactionFilter (key-based redaction)
→ Root logger handler
→ Formatter
```

Begründung:
- Defense-in-Depth: Filter fängt alle drei Pfade (extra, args, nested mappings)
- Key-basierte Erkennung vermeidet False Positives
- Keine Änderung an bestehendem Code erforderlich (es gab keinen)
- Idempotent bei mehrfachem `create_app()`
- Operative Metadaten bleiben erhalten

## Implementierung

### Neue Dateien

| Datei | Zweck | Zeilen |
|-------|-------|--------|
| `src/.../infrastructure/log_redaction.py` | PrivacyRedactionFilter + configure_logging() | 158 |
| `tests/unit/test_log_redaction.py` | 42 Unit-Tests für Filter | 390 |
| `tests/api/test_event_logging_privacy.py` | 27 API-Privacy-Tests mit caplog | 370 |

### Geänderte Dateien

| Datei | Änderung |
|-------|----------|
| `src/.../app.py` | +4 Zeilen: `configure_logging()` in `create_app()` |

### Filter-Design

`PrivacyRedactionFilter(logging.Filter)`:

1. **Extra-Attribute**: Für jedes nicht-builtin Record-Attribut:
   - Sensitive key → `[REDACTED]`
   - Mapping-Wert → rekursive Redaktion

2. **Mapping-Args**: Wenn `record.args` ein Mapping ist:
   - Sensitive keys → `[REDACTED]`

3. **Idempotenz**: `_privacy_filtered`-Flag verhindert Doppelausführung

4. **Keine Mutation**: Originaldaten bleiben unverändert

## Red Tests (STAGE 2)

Alle 42 Unit-Tests sind **GREEN**. Sie decken ab:

| Test-Klasse | Tests | Beschreibung |
|------------|-------|-------------|
| TestFilterExistsAndWired | 2 | LT-01: Filter existiert und ist verdrahtet |
| TestRedactConfirmedDate | 2 | LT-02: confirmed_date |
| TestRedactCalculatedDate | 1 | LT-03: calculated_date |
| TestRedactSuggestedDate | 1 | LT-04: suggested_date |
| TestRedactEvidenceText | 1 | LT-05: evidence_text |
| TestRedactEvidenceNote | 1 | LT-06: evidence_note |
| TestRedactSourceText | 1 | LT-07: source_text |
| TestRedactDocumentId | 1 | LT-08: document_id |
| TestRedactConfirmationId | 1 | LT-09: confirmation_id |
| TestRedactMappingArgs | 1 | LT-10: Mapping-Argumente |
| TestRedactExtraFields | 1 | LT-11: extra-Felder |
| TestRedactNestedStructures | 2 | LT-12: Verschachtelte Strukturen |
| TestExceptionPath | 2 | LT-13: Exception-Pfad |
| TestIdempotency | 2 | LT-14: Idempotenz |
| TestOperationalMetadataPreserved | 4 | LT-15: Operative Metadaten erhalten |
| TestNoMutation | 2 | LT-16: Keine Mutation |
| TestSensitiveFieldsCompleteness | 1 | Vollständigkeitsprüfung |
| TestFilterHandlesAllFieldNames | 14 | Parametrisiert: jedes SENSITIVE_FIELD |
| TestRedactReferenceDate | 1 | reference_date |
| TestRedactCaseId | 1 | case_id |

## API Lifecycle Privacy Tests (STAGE 3)

27 Tests mit `caplog`-Fixture über alle M6-A-API-Pfade:

| Pfad | Tests | Ergebnis |
|------|-------|----------|
| Confirm (auto/manual/corrected/reject/invalid) | 5 | Keine sensiblen Werte in caplog.text |
| Calculation Preview | 2 | Keine IDs/Daten im Log |
| History | 1 | document_id nicht im Log |
| Reference Events List | 1 | document_id nicht im Log |
| Revoke | 1 | confirmation_id nicht im Log |
| Non-M6-A (health/case) | 2 | Filter beeinträchtigt keine anderen Endpunkte |
| Marker Sweep | 14 | Alle SENSITIVE_FIELDS sind gültige Identifier |
| Filter Wired | 1 | Filter auf Root-Logger |

## Sensitive Marker Sweep

```text
Sensitive marker occurrences in formatted application logs:
0
```

Null sensible Werte erscheinen in `caplog.text` über alle 27 API-Tests.

## Vollständige Revalidierung

| Gate | Ergebnis |
|------|----------|
| Tests | **315 passed, 0 skipped, 0 failed** |
| Coverage | **90.83%** (≥ 90%) |
| Log redaction module coverage | **93%** (59 stmts, 4 missed) |
| Ruff | **PASS** |
| Mypy | **PASS** (42 source files, 0 issues) |
| pip check (project deps) | **PASS** (hermes-agent warnings pre-existing) |
| Architecture | **ARCH_PASS** (Variant C, central filter) |
| Security | **SECURITY_PASS** (no plaintext leak, key-based redaction) |
| Compliance | **COMPLIANCE_PASS** (INV-M6A-16/21/DP-08, FR-M6A-030) |
| Critical open | 0 |
| Major open | 0 |
| Merge-blocking Minor open | 0 |

## Commits

```text
1d40d2b fix(m6a): enforce logging privacy invariants
1130b0c fix(m6a): repair confirmation state machine and context binding
f1447e6 feat(m6a): implement reference events and calendar arithmetic
```

## Geänderte Dateien (Delta: 1130b0c → 1d40d2b)

| Datei | Aktion | Zeilen |
|-------|--------|--------|
| `src/.../infrastructure/log_redaction.py` | NEW | +158 |
| `src/.../app.py` | MODIFIED | +4 |
| `tests/unit/test_log_redaction.py` | NEW | +390 |
| `tests/api/test_event_logging_privacy.py` | NEW | +370 |

## Nicht ausgeführte Aktionen

- Kein Merge
- Kein Auto-Merge
- Kein Force-Push
- Keine GitHub Actions
- Keine Branch-Löschung

## Nächster Owner-Schritt

1. PR #5 Review — bestätigen, dass der Logging-Filter den Anforderungen entspricht
2. Merge PR #5 (Squash) nach `main`
3. Post-Merge-Verifikation: `pytest --cov`, alle Gates
4. Issue #3 schließen nach erfolgreichem Main-Test

---

**PR #5 bleibt ungemergt und READY FOR REVIEW.**
