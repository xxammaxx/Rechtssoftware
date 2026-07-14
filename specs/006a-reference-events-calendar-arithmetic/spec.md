# Spec — M6-A Bestätigte Bezugsereignisse und deterministische Kalenderarithmetik

## Feature
M6-A — Confirmed reference events and pure calendar arithmetic for non-binding calculation previews

## Overview

M5 erkennt Fristkandidaten aus Dokumenttext, berechnet jedoch keine Daten. M6-A schließt diese Lücke mit dem kleinsten sicheren Slice:

1. Möglichen Bezugspunkt zu einem M5-Kandidaten darstellen
2. Bezugsdatum ausdrücklich durch den Nutzer bestätigen lassen
3. Dauer (Tage oder Wochen) rein mathematisch addieren
4. Unverbindliches Kandidatendatum mit vollständigem Rechenweg ausgeben

M6-A berechnet KEINE rechtlich verbindliche Frist. Das Ergebnis ist eine **Berechnungsvorschau**.

---

## Product Invariants

| ID | Invariant |
|----|-----------|
| INV-M6A-01 | Ein unbestätigtes Bezugsdatum DARF keine Berechnung auslösen. |
| INV-M6A-02 | Ein automatisch erkannter Datumskandidat DARF nicht automatisch als rechtlich maßgebliches Bezugsdatum gelten. |
| INV-M6A-03 | Die Bestätigung MUSS eine explizite Nutzeraktion sein. |
| INV-M6A-04 | Die Herkunft des Bezugsdatums MUSS nachvollziehbar bleiben. |
| INV-M6A-05 | M6-A DARF nur Tage und Wochen berechnen. |
| INV-M6A-06 | Wochen MÜSSEN für die rein mathematische Vorschau als sieben Kalendertage behandelt werden. |
| INV-M6A-07 | Monate und Jahre MÜSSEN als unsupported behandelt werden. |
| INV-M6A-08 | Keine Wochenend- oder Feiertagsanpassung darf erfolgen. |
| INV-M6A-09 | Keine Zustellungs- oder Bekanntgabefiktion darf angewendet werden. |
| INV-M6A-10 | Keine rechtliche Regel darf automatisch ausgewählt werden. |
| INV-M6A-11 | Jede Ausgabe MUSS `human_review_required=true` enthalten. |
| INV-M6A-12 | Jede Ausgabe MUSS `legal_validity_assessed=false` enthalten. |
| INV-M6A-13 | Der vollständige Rechenweg MUSS maschinenlesbar dargestellt werden. |
| INV-M6A-14 | Eine Änderung des bestätigten Bezugsdatums MUSS zu einem neuen Ergebnis führen und darf das frühere Ergebnis nicht stillschweigend umdeuten. |
| INV-M6A-15 | Keine externen Laufzeitrequests. |
| INV-M6A-16 | Keine Falldaten oder Bezugsdaten in Logs. |
| INV-M6A-17 | Nur synthetische Testdaten. |
| INV-M6A-18 | Ergebnisse dürfen nicht als verbindliche Fristen bezeichnet werden. |
| INV-M6A-19 | Das System ist ausschließlich für die Nutzung durch eine einzelne natürliche Person ausgelegt. Multi-User-Zugriff ist nicht implementiert. |
| INV-M6A-20 | Freitextfelder (evidence_note, source_reference, confirmed_by) unterliegen Längenbeschränkungen (max 2000/100/100 Zeichen) und werden als potentiell unsicher behandelt. |
| INV-M6A-21 | Ein Logging-Filter MUSS die Felder confirmed_date, evidence_text, evidence_note und source_text vor der Ausgabe redigieren (Ersetzung durch [REDACTED]). |
| INV-M6A-22 | Manual-Einträge OHNE evidence_note erhalten eine Warnung MANUAL_ENTRY_WITHOUT_EVIDENCE und geringeres Audit-Gewicht. |
| INV-M6A-23 | Datumsbereich: Input 1900-01-01 bis 2099-12-31. Post-Calculation-Prüfung: calculated_date muss innerhalb 1900-01-01 bis 2099-12-31 liegen (Fehler: CALCULATED_DATE_OUT_OF_RANGE). |
| INV-M6A-24 | Die Bestätigungshistorie wird append-only gespeichert. Dies bietet kooperative Integrität, aber KEINE kryptografische Manipulationssicherheit. Der Nutzer mit Dateisystemzugriff kann die SQLite-Datenbank direkt editieren. Dies ist eine dokumentierte Einschränkung für ein lokales Single-User-Tool. |

---

## User Stories

### US1 — Bezugspunkt erkennen (P1)
Als Nutzer möchte ich sehen, welches Ereignis möglicherweise als Bezugspunkt einer relativen Fristformulierung gemeint ist.

**Acceptance Criteria:**
- Zu jedem M5-RELATIVE_PERIOD-Kandidaten werden mögliche Bezugsereignisse aus dem Dokumenttext dargestellt
- Mögliche Bezugsdaten aus M5-EXPLICIT_DATE-Kandidaten im selben Dokument werden als Kandidaten angeboten
- Jeder Bezugsereignis-Kandidat hat den Status `UNCONFIRMED`
- Kein Bezugsereignis wird automatisch als gültig angenommen
- Die Herkunft jedes Kandidaten ist nachvollziehbar (document_id, offset, source_text)

### US2 — Bezugspunkt bestätigen (P1)
Als Nutzer möchte ich das tatsächliche Bezugsdatum ausdrücklich bestätigen oder manuell eingeben.

**Acceptance Criteria:**
- Benutzer kann ein vorgeschlagenes Datum bestätigen (Status → CONFIRMED)
- Benutzer kann ein Datum ablehnen (Status → REJECTED)
- Benutzer kann ein Datum manuell eingeben (confirmation_method = MANUALLY_ENTERED)
- Benutzer kann ein bestätigtes Datum ändern
- Benutzer kann eine Bestätigung widerrufen (Status → REVOKED)
- Jede Bestätigungsaktion wird mit Zeitstempel auditierbar protokolliert
- Ohne Bestätigung kann keine Kalenderarithmetik ausgeführt werden

### US3 — Reine Tages- oder Wochenaddition (P1)
Als Nutzer möchte ich aus einem bestätigten Datum und einer erkannten Dauer ein rein rechnerisches Kandidatendatum erhalten.

**Acceptance Criteria:**
- Tagesdauern werden als Kalendertage addiert (14 Tage = 14 Kalendertage)
- Wochendauern werden als Vielfache von 7 Kalendertagen addiert (2 Wochen = 14 Kalendertage)
- Schaltjahre und Jahreswechsel werden korrekt behandelt
- Monats- und Jahresdauern werden abgelehnt (UNSUPPORTED_DURATION_UNIT)
- Negative und Null-Dauern werden abgelehnt
- Ergebnis ist eine CALCULATED_CANDIDATE

### US4 — Rechenweg prüfen (P1)
Als Nutzer möchte ich sehen, welche Werte verwendet und wie sie addiert wurden.

**Acceptance Criteria:**
- Der vollständige Rechenweg wird als Liste von `calculation_steps` ausgegeben
- Jeder Schritt enthält: operation, input_date, amount, output_date
- Bestätigtes Bezugsdatum ist im Ergebnis enthalten
- Verwendete Dauer ist im Ergebnis enthalten
- Alle Ein- und Ausgaben sind ISO-8601-datiert

### US5 — Grenzen erkennen (P2)
Als Nutzer möchte ich deutlich sehen, dass keine rechtliche Fristberechnung, Feiertagsprüfung oder Zustellungsfiktion erfolgt ist.

**Acceptance Criteria:**
- `legal_validity_assessed` ist immer `false`
- `human_review_required` ist immer `true`
- `adjustments.weekend_adjustment_applied` ist immer `false`
- `adjustments.holiday_adjustment_applied` ist immer `false`
- `adjustments.legal_rule_applied` ist immer `false`
- Alle Warnungen sind explizit und maschinenlesbar
- Der Begriff "Frist" erscheint NUR in Warnungen und Disclaimer-Text

### US6 — Bestätigung ändern oder widerrufen (P2)
Als Nutzer möchte ich ein zuvor bestätigtes Bezugsdatum ändern oder widerrufen können.

**Acceptance Criteria:**
- Änderung einer Bestätigung erzeugt einen neuen Bestätigungsdatensatz
- Der vorherige Datensatz bleibt historisch erhalten (SUPERSEDED)
- Widerruf erzeugt REVOKED-Status
- Nach Widerruf ist keine Berechnung mehr möglich
- Der Audit-Trail ist zu jedem Zeitpunkt vollständig

---

## Funktionale Anforderungen

| ID | Anforderung |
|----|-------------|
| FR-M6A-001 | Das System MUSS mögliche Bezugsereignisse zu einem M5-Kandidaten darstellen können. |
| FR-M6A-002 | Ein mögliches Bezugsereignis MUSS zunächst den Status `unconfirmed` besitzen. |
| FR-M6A-003 | Das System MUSS eine ausdrückliche Nutzerbestätigung verlangen. |
| FR-M6A-004 | Eine Bestätigung MUSS das bestätigte Datum enthalten. |
| FR-M6A-005 | Eine Bestätigung MUSS die Herkunft des Datums enthalten. |
| FR-M6A-006 | Eine Bestätigung MUSS den Zeitpunkt der Bestätigungsaktion enthalten. |
| FR-M6A-007 | Ein Nutzer MUSS ein vorgeschlagenes Datum ablehnen können. |
| FR-M6A-008 | Ein Nutzer MUSS ein Datum manuell eingeben können. |
| FR-M6A-009 | Ein Nutzer MUSS eine Bestätigung ändern können. |
| FR-M6A-010 | Ein Nutzer MUSS eine Bestätigung widerrufen können. |
| FR-M6A-011 | Ohne bestätigtes Bezugsdatum DARF keine Kalenderarithmetik ausgeführt werden. |
| FR-M6A-012 | Das System MUSS Tagesdauern als Kalendertage addieren können. |
| FR-M6A-013 | Das System MUSS Wochendauern als Vielfache von sieben Kalendertagen darstellen können. |
| FR-M6A-014 | Monats- und Jahresdauern MÜSSEN im ersten Build abgelehnt werden. |
| FR-M6A-015 | Negative Dauern MÜSSEN abgelehnt werden. |
| FR-M6A-016 | Eine Dauer von null MUSS abgelehnt werden (INVALID_DURATION_AMOUNT). |
| FR-M6A-017 | Übergroße Dauern MÜSSEN durch eine dokumentierte Grenze verhindert werden. |
| FR-M6A-018 | Das Ergebnis MUSS als `calculated_candidate` bezeichnet werden. |
| FR-M6A-019 | Das Ergebnis MUSS das bestätigte Bezugsdatum enthalten. |
| FR-M6A-020 | Das Ergebnis MUSS die verwendete Dauer enthalten. |
| FR-M6A-021 | Das Ergebnis MUSS die Operation enthalten. |
| FR-M6A-022 | Das Ergebnis MUSS das rechnerische Kandidatendatum enthalten. |
| FR-M6A-023 | Das Ergebnis MUSS `legal_validity_assessed=false` enthalten. |
| FR-M6A-024 | Das Ergebnis MUSS `human_review_required=true` enthalten. |
| FR-M6A-025 | Das Ergebnis MUSS ausweisen, dass keine Wochenend- oder Feiertagsanpassung durchgeführt wurde. |
| FR-M6A-026 | Das Ergebnis MUSS ausweisen, dass keine Zustellungs- oder Bekanntgaberegel angewendet wurde. |
| FR-M6A-027 | Die Ausgabe MUSS deterministisch sein. |
| FR-M6A-028 | Die API MUSS bestehende Fehler-Envelopes verwenden. |
| FR-M6A-029 | Das System DARF keine externe Laufzeitabhängigkeit benötigen. |
| FR-M6A-030 | Das System DARF bestätigte Bezugsdaten nicht in Logs ausgeben. |

---

## Erfolgskriterien

| ID | Kriterium |
|----|-----------|
| SC-M6A-001 | Die Spezifikation trennt mathematische Berechnung und rechtliche Bewertung. |
| SC-M6A-002 | Kein Ablauf ermöglicht eine Berechnung ohne bestätigtes Bezugsdatum. |
| SC-M6A-003 | Tage und Wochen sind eindeutig spezifiziert. |
| SC-M6A-004 | Monate, Jahre, Werktage und Arbeitstage sind explizit zurückgestellt. |
| SC-M6A-005 | Der Rechenweg ist vollständig maschinenlesbar. |
| SC-M6A-006 | Alle Ergebnisse erfordern menschliche Prüfung. |
| SC-M6A-007 | Keine Ausgabe behauptet eine rechtlich verbindliche Frist. |
| SC-M6A-008 | Keine Feiertags- oder Wochenendlogik ist Teil des ersten Builds. |
| SC-M6A-009 | Keine Zustellungsfiktion ist Teil des ersten Builds. |
| SC-M6A-010 | Mindestens 25 konkrete Testvektoren sind definiert. |
| SC-M6A-011 | Alle Research-Claims besitzen eine Primärquelle oder sind als Produktentscheidung gekennzeichnet. |
| SC-M6A-012 | Architektur-, Spec- und Contract-Artefakte widersprechen sich nicht. |
| SC-M6A-013 | Der spätere Build kann ohne erneute Grundsatzentscheidung umgesetzt werden. |

---

## Benutzte Durations

| Unit | Unterstützt | Arithmetik |
|------|------------|------------|
| DAY | **YES** | `date + timedelta(days=N)` |
| WEEK | **YES** | `date + timedelta(weeks=N)` = 7×N Kalendertage |
| MONTH | **NO** | Variable Länge, fehlende Tage (§ 188 Abs. 3 BGB) |
| YEAR | **NO** | Schaltjahr-Problematik |
| BUSINESS_DAY | **NO** | Erfordert Feiertagsdaten und Bundesland |
| WORKING_DAY | **NO** | Erfordert Feiertagsdaten und Bundesland |
| HOUR | **NO** | Nicht kalendertagbasiert |
| QUALITATIVE | **NO** | Nicht mathematisch auflösbar |

---

## Bewusst nicht unterstützt

- Keine verbindliche Rechtsfristberechnung
- Keine automatische Zustellungsfiktion (§ 4 VwZG, § 180 ZPO)
- Keine automatische Bekanntgaberegel (§ 41 VwVfG)
- Keine Wochenendverschiebung (§ 193 BGB)
- Keine Feiertagsverschiebung (§ 193 BGB, § 222 ZPO)
- Keine Monats- oder Jahresarithmetik
- Keine automatische Rechtsregelauswahl
- Keine "Werktage" oder "Arbeitstage"
- Kein Frontend
- Keine Cloud-Dienste
- Keine externen Laufzeitrequests

---

## Warncodes (stabil)

| Code | Type | Bedeutung |
|------|------|-----------|
| `LEGAL_CALCULATION_NOT_PERFORMED` | Warning | Zwingend in jeder Antwort (von M5 geerbt) |
| `REFERENCE_EVENT_NOT_CONFIRMED` | Warning | Bezugsdatum nicht bestätigt |
| `REFERENCE_EVENT_REJECTED` | Warning | Bezugsereignis abgelehnt |
| `REFERENCE_EVENT_REVOKED` | Warning | Bestätigung widerrufen |
| `MULTIPLE_REFERENCE_EVENTS` | Warning | Mehrere Bezugsereignisse gefunden |
| `REFERENCE_DATE_REQUIRED` | Info | Bezugsdatum erforderlich für Berechnung |
| `DURATION_NOT_AVAILABLE` | Warning | Keine Dauer verfügbar |
| `UNSUPPORTED_DURATION_UNIT` | **Error** | Monat/Jahr/Werktag nicht unterstützt |
| `INVALID_DURATION_AMOUNT` | **Error** | Negative oder Null-Dauer |
| `DURATION_LIMIT_EXCEEDED` | **Error** | Dauer überschreitet Maximalwert |
| `NO_WEEKEND_OR_HOLIDAY_ADJUSTMENT` | Info | Keine Feiertags-/Wochenendanpassung |
| `NO_DELIVERY_OR_ANNOUNCEMENT_RULE_APPLIED` | Info | Keine Zustellungs-/Bekanntgaberegel |
| `HUMAN_REVIEW_REQUIRED` | Info | Menschliche Prüfung erforderlich |
| `CALCULATION_PREVIEW_ONLY` | Warning | Nur Berechnungsvorschau, nicht rechtsverbindlich |
| `CALCULATION_NOT_PERFORMED` | Warning | Berechnung nicht durchgeführt |
| `CALCULATED_DATE_OUT_OF_RANGE` | **Error** | Ergebnisdatum außerhalb des gültigen Bereichs (1900–2099) |
| `MANUAL_ENTRY_WITHOUT_EVIDENCE` | Warning | Manuelle Eingabe ohne Beleg/Evidenz (geringeres Audit-Gewicht) |
| `FIELD_TOO_LONG` | **Error** | Freitextfeld überschreitet maximale Länge |
| `INVALID_SOURCE_TYPE` | **Error** | Ungültiger source_type-Wert |

---

## Abgrenzung zu M5

| Aspekt | M5 | M6-A |
|--------|-----|------|
| Erkennung | Text → Kandidaten | — |
| Bezugsdatum | Nicht bestimmt | Nutzerbestätigung |
| Berechnung | Keine | Tage/Wochen-Addition |
| Ergebnis | DeadlineCandidate | CalendarCalculationCandidate |
| Human Review | Flag gesetzt | Strukturell erzwungen |
| Persistenz | Keine | Bestätigung persistent |
