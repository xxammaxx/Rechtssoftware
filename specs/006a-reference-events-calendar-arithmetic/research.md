# Research — M6-A Reference Events and Calendar Arithmetic

## Research Status: GREEN

All 10 research questions answered with primary source evidence. No normative gaps identified. Boundaries are clear and unambiguous.

---

## RQ-01 — What is purely mathematical vs. legal?

### The Clean Dividing Line

```
┌──────────────────────────────────────────────────────────────────────┐
│  M6-A SCOPE (pure arithmetic)                                        │
│                                                                      │
│  reference_date + N days → candidate_date                            │
│  reference_date + N weeks → candidate_date                           │
│                                                                      │
│  This is calendar arithmetic: no legal rules applied.                │
└──────────────────────────────────────┬───────────────────────────────┘
                                       │ BOUNDARY
┌──────────────────────────────────────▼───────────────────────────────┐
│  OUTSIDE M6-A (legal rule application)                               │
│                                                                      │
│  § 187 BGB:    Fristbeginn — day of event excluded or included       │
│  § 188 BGB:    Fristende — month/year alignment, missing-day rule    │
│  § 193 BGB:    Weekend/holiday → next Werktag                        │
│  § 222(2) ZPO: Same (civil procedure)                                │
│  § 4 VwZG:     4-day delivery fiction (Einschreiben)                 │
│  § 41(2) VwVfG: 4-day Bekanntgabefiktion (VA by post)                │
│  § 180 ZPO:    Delivery fiction via mailbox insertion                │
│  Feiertagsgesetze der 16 Länder: State-specific holiday rules        │
└──────────────────────────────────────────────────────────────────────┘
```

**Key Finding:** `reference_date + timedelta(days=N)` is pure math. `datetime.timedelta` handles all calendar transitions (leap years, month boundaries, year boundaries) correctly. Everything beyond this is legal rule application.

**Sources:**
- § 187 Abs. 1 BGB (gesetze-im-internet.de, accessed 2026-07-14)
- § 188 BGB (gesetze-im-internet.de, accessed 2026-07-14)
- § 193 BGB (gesetze-im-internet.de, accessed 2026-07-14)
- Python `datetime` documentation

---

## RQ-02 — What reference events exist in German law?

| Event | Legal Definition | Statute | Auto-Detectable from Text? |
|-------|-----------------|---------|---------------------------|
| Zustellung | Formal delivery with proof | ZPO §§ 166-195, VwZG §§ 3-5 | **NO** — requires Zustellungsurkunde |
| Bekanntgabe | When a VA becomes known | VwVfG § 41, § 43 | **NO** — date determined by delivery |
| Zugang | When Willenserklärung reaches recipient's sphere | BGB § 130 | **NO** — factual question |
| Erhalt | Informal/factual receipt | No single statute | **NO** — factual |
| Ausstellung | Date document was issued | Various | **PARTIALLY** — may state "ausgestellt am..." |
| Bescheiddatum | Date printed on a Bescheid | Various | **YES** — typically on the document |
| Veröffentlichung | Publication date | Various | **YES** — stated in publication |
| Antragstellung | Date of filing | Various | **PARTIALLY** — may be referenced |
| Datum des Schreibens | Date letter was written | — | **YES** — typically at top |
| Eingang bei Gericht | Receipt by court | ZPO § 130a(5) | **NO** — determined by court system |
| Aufgabe zur Post | Date of mailing | VwZG § 4(2) | **PARTIALLY** — may be referenced |
| User-Defined | Any user-provided date | — | **N/A** — manual entry |

**Sources:**
- ZPO § 166 Abs. 1, ZPO §§ 166-195 (gesetze-im-internet.de, 2026-07-14)
- VwVfG § 41 Abs. 1, § 43 Abs. 1 (gesetze-im-internet.de, 2026-07-14)
- BGB § 130 Abs. 1 (gesetze-im-internet.de, 2026-07-14)

---

## RQ-03 — What can be automatically suggested vs. must be user-confirmed?

**DSGVO Art. 22 Abs. 1:**
> "Die betroffene Person hat das Recht, nicht einer ausschließlich auf einer automatisierten Verarbeitung [...] beruhenden Entscheidung unterworfen zu werden, die ihr gegenüber rechtliche Wirkung entfaltet oder sie in ähnlicher Weise erheblich beeinträchtigt."

Source: dejure.org/gesetze/DSGVO/22.html (verified against EUR-Lex 32016R0679), accessed 2026-07-14

**What M6-A CAN suggest (without user):**
- Detected dates from document text (M5 output)
- Duration amount + unit from relative candidates (M5 output)
- Warning: "REFERENCE_NOT_CONFIRMED"

**What M6-A MUST NOT auto-confirm:**
- Auto-selecting the reference date
- Auto-classifying event as "Zustellung"
- Auto-applying § 187 BGB (day exclusion)
- Auto-applying Feiertagsregeln
- Displaying date as "Fristende"
- Omitting the disclaimer

**Architecture Decision:** M6-A implements a **confirmation gate**: every reference event → reference date mapping must pass through user confirmation before any arithmetic is displayed.

---

## RQ-04 — How should user confirmation work?

### Confirmation State Machine

```
UNCONFIRMED → (user clicks "Bestätigen") → CONFIRMED
CONFIRMED   → (user changes reference date) → CONFIRMED (with updated date, previous version preserved)
CONFIRMED   → (user explicitly revokes) → REVOKED
```

### Required Audit Data Per Confirmation

| Field | Type | Purpose |
|-------|------|---------|
| `confirmed_by` | str | Human identifier |
| `confirmed_at` | datetime (UTC) | Audit timestamp |
| `confirmation_method` | enum | AUTO_SUGGESTED, MANUALLY_ENTERED, CORRECTED |
| `source_document_id` | UUID | Origin document |
| `source_text` | str | Raw text basis |
| `source_offset_start` | int | Position in document text |
| `source_offset_end` | int | Position in document text |
| `reference_event_type` | enum | User-selected event category |
| `confirmed_date` | date | The confirmed reference date |

### Immutability Requirements

- Confirmation events are **append-only**
- Revocation creates a new event, doesn't delete the old one
- Full audit trail from document import → extraction → confirmation → calculation

---

## RQ-05 — Which duration formats belong in the first build?

| Duration | Arithmetic | Edge Cases | M6-A Status |
|----------|-----------|------------|-------------|
| **Days** | `date + timedelta(days=N)` | None | **IN SCOPE** |
| **Weeks** | `date + timedelta(weeks=N)` = 7×N days | None | **IN SCOPE** |
| Months | Requires `dateutil.relativedelta` or custom logic | Variable length, missing days | **DEFERRED** |
| Years | Same as months | Leap year boundary | **DEFERRED** |
| Business Days | Requires holiday DB + location | 16 Feiertagsgesetze | **DEFERRED** |
| Working Days | Same as business days | State-dependent | **DEFERRED** |

**Source:** § 188 Abs. 3 BGB (gesetze-im-internet.de, 2026-07-14) — variable-length month problem.

---

## RQ-06 — What date semantics are used?

| Aspect | Decision |
|--------|----------|
| Type | `datetime.date` (not `datetime.datetime`) |
| Timezone | None needed (calendar-date arithmetic) |
| Format | ISO 8601: `YYYY-MM-DD` |
| Valid range | 1900-01-01 to 2099-12-31 (inherited from M5) |
| Leap years | Handled correctly by Python `datetime` |
| Year transitions | Handled correctly by Python `datetime` |

---

## RQ-07 — How is the result designated?

### Preferred Terminology

| Concept | German (UI) | English (API) |
|---------|-------------|---------------|
| Calculated result | **Berechnungsvorschau** | `calculated_candidate` |
| Input date | **Referenzdatum** | `reference_date` |
| Event | **Bezugsereignis** | `reference_event` |
| Duration | **Dauer (Tage/Wochen)** | `duration` |
| Confirmation | **Bestätigung** | `confirmation` |

### Prohibited Terms (MUST NOT appear)

**German:** Frist, Fristende, Rechtsfrist, Verbindliche Frist, Fälligkeit, Ablaufdatum, Letzter Tag, Stichtag, Gesetzliche Frist

**English:** deadline, binding deadline, legal deadline, final due date, expiry date, last day

---

## RQ-08 — Which rule areas are deferred beyond M6-A?

| # | Rule | Statute | Category |
|---|------|---------|----------|
| 1 | Fristbeginn (Tag nicht mitgerechnet) | § 187 Abs. 1 BGB | Fristbeginn |
| 2 | Fristbeginn (Tagesbeginn) | § 187 Abs. 2 BGB | Fristbeginn |
| 3 | Fristende (Wochen/Monate/Jahre) | § 188 Abs. 2 BGB | Fristende |
| 4 | Fristende (fehlender Tag) | § 188 Abs. 3 BGB | Fristende |
| 5 | Wochenende/Feiertage → Werktag | § 193 BGB, § 222 Abs. 2 ZPO | Feiertage |
| 6 | Zustellungsfiktion (4 Tage) | § 4 Abs. 2 VwZG | Fiktion |
| 7 | Bekanntgabefiktion (4 Tage) | § 41 Abs. 2 VwVfG | Fiktion |
| 8 | Bekanntgabefiktion (2 Wochen) | § 41 Abs. 4 VwVfG | Fiktion |
| 9 | Ersatzzustellung Briefkasten | § 180 ZPO | Fiktion |
| 10 | Niederlegung | § 181 ZPO | Fiktion |
| 11 | Rückwirkung (demnächst) | § 167 ZPO | Fiktion |
| 12 | Zugangsfiktion | § 130 BGB | Fiktion |
| 13 | Feiertage (16 Landesgesetze) | FeiertagsG der Länder | Feiertage |
| 14 | Hemmung der Verjährung | § 203 ff. BGB | Unterbrechung |
| 15 | Wiedereinsetzung | § 233 ZPO, § 32 VwVfG | Rechtsbehelf |

---

## RQ-09 — Future source metadata versioning (sketch only)

**NOT FOR IMPLEMENTATION IN M6-A.** Forward-looking sketch for a future `LegalRuleSource` schema with fields: `rule_id`, `norm_citation`, `norm_title`, `legal_area`, `scope`, `publication_date`, `last_amended`, `source_url`, `source_type`, `issuing_authority`, `version_tag`, `jurisdiction`. Every legal rule applied to a deadline MUST in future be traceable to a specific Norm/Paragraph/Version.

---

## RQ-10 — Language that prevents false security

### Mandatory in ALL M6-A output:

| Requirement | Placement |
|-------------|-----------|
| `human_review_required: true` | Every API response |
| `legal_validity_assessed: false` | Every API response |
| "Berechnungsvorschau" label | Every UI |
| "KEINE rechtlich verbindliche Fristberechnung" | Every UI |
| `LEGAL_CALCULATION_NOT_PERFORMED` warning | Every API response |

---

## Source Matrix

| # | Title | Authority | Norm | Legal Area | Version/Accessed | Primary? |
|---|-------|-----------|------|------------|------------------|----------|
| 1 | BGB § 187 Fristbeginn | Bundesrepublik Deutschland | § 187 Abs. 1-2 | Zivilrecht | gesetze-im-internet.de, 2026-07-14 | YES |
| 2 | BGB § 188 Fristende | Bundesrepublik Deutschland | § 188 Abs. 1-3 | Zivilrecht | gesetze-im-internet.de, 2026-07-14 | YES |
| 3 | BGB § 189-192 | Bundesrepublik Deutschland | §§ 189-192 | Zivilrecht | gesetze-im-internet.de, 2026-07-14 | YES |
| 4 | BGB § 193 Sonn-/Feiertag | Bundesrepublik Deutschland | § 193 | Zivilrecht | gesetze-im-internet.de, 2026-07-14 | YES |
| 5 | BGB § 130 Zugang | Bundesrepublik Deutschland | § 130 Abs. 1 | Zivilrecht | gesetze-im-internet.de, 2026-07-14 | YES |
| 6 | ZPO § 166 Zustellung | Bundesrepublik Deutschland | § 166 | Zivilprozessrecht | gesetze-im-internet.de, 2026-07-14 | YES |
| 7 | ZPO §§ 167, 177-181 | Bundesrepublik Deutschland | §§ 167, 177-181 | Zivilprozessrecht | gesetze-im-internet.de, 2026-07-14 | YES |
| 8 | ZPO § 222 Fristberechnung | Bundesrepublik Deutschland | § 222 Abs. 1-3 | Zivilprozessrecht | gesetze-im-internet.de, 2026-07-14 | YES |
| 9 | VwVfG § 41 Bekanntgabe | Bundesrepublik Deutschland | § 41 Abs. 1-5 | Verwaltungsrecht | gesetze-im-internet.de, 2026-07-14 | YES |
| 10 | VwVfG § 43 Wirksamkeit | Bundesrepublik Deutschland | § 43 | Verwaltungsrecht | gesetze-im-internet.de, 2026-07-14 | YES |
| 11 | VwZG §§ 3-4 | Bundesrepublik Deutschland | §§ 3-4 | Verwaltungsrecht | gesetze-im-internet.de, 2026-07-14 | YES |
| 12 | DSGVO Art. 22 | Europäische Union | Art. 22 | Datenschutzrecht | EUR-Lex 32016R0679, 2026-07-14 | YES |
| 13 | PrivateLegalNavigator Constitution | Project | §§ 1-12 | — | .specify/memory/constitution.md | N/A |

---

## Risk Register

| Risk | Severity | Mitigation |
|------|----------|-----------|
| User treats calculated date as binding, misses real deadline | HIGH | Mandatory disclaimers, `human_review_required: true`, no "Frist" terminology, warning badges |
| Art. 22 DSGVO violation — automated decision with legal effect | HIGH | Confirmation gate: no calculation without user confirmation, human-in-the-loop always |
| Days-only arithmetic produces weekend/holiday date, user relies on it | MEDIUM | Warning: "Keine Feiertage berücksichtigt. Rechtliche Frist kann abweichen." |
| User selects wrong reference event type | MEDIUM | Event type selection is user-controlled, clear warnings |
| False sense of security from "confirmed" label | MEDIUM | "Bestätigt" only means reference date confirmed — NOT that calculation is legally binding |
