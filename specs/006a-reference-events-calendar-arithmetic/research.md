# Research — M6-A Reference Events and Calendar Arithmetic

## Research Status: RESEARCH_PASS_WITH_NOTES

All 10 research questions answered. Primary normative sources (EUR-Lex, gesetze-im-internet.de) are the authoritative references. Secondary sources (dejure.org) are used for orientation only. Product and compliance boundaries are explicitly distinguished. Legal basis and GDPR applicability are identified as context-dependent.

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

**DSGVO Art. 22 Abs. 1 (EUR-Lex 32016R0679):**
> "Die betroffene Person hat das Recht, nicht einer ausschließlich auf einer automatisierten Verarbeitung [...] beruhenden Entscheidung unterworfen zu werden, die ihr gegenüber rechtliche Wirkung entfaltet oder sie in ähnlicher Weise erheblich beeinträchtigt."

**Source:** EUR-Lex 32016R0679, Art. 22(1) (OFFICIAL_PRIMARY_NORM), accessed 2026-07-14. Also consulted via dejure.org (SECONDARY_SOURCE) for convenience.

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

**Architecture Decision:** M6-A implements a **confirmation gate**: every reference event → reference date mapping must pass through user confirmation before any arithmetic is displayed. This is a **product safety measure** — not a statutory requirement under Art. 22 DSGVO. The confirmation gate provides structural assurance that the system cannot produce output that might be mistaken for an automated legal decision. Whether Art. 22 applies at all depends on the deployment context and whether the system is used to produce decisions with legal effect.

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
| `confirmed_by` | str (optional) | Human-readable label (no authentication in single-user context) |
| `confirmed_at` | datetime (UTC) | Audit timestamp |
| `confirmation_method` | enum | AUTO_SUGGESTED, MANUALLY_ENTERED, CORRECTED |
| `source_document_id` | UUID | Origin document |
| `evidence_start_offset` | int | Position in document text (start) |
| `evidence_end_offset` | int | Position in document text (end) |
| `reference_event_type` | enum | User-selected event category |
| `confirmed_date` | date | The confirmed reference date |

**Note:** Evidence text is NOT duplicated. The original document text is referenced
by `document_id` + `start_offset` + `end_offset`. The text snippet can be
reconstructed on demand from the source document. This avoids duplicating
potentially personal data from legal documents into the confirmation journal.

### Confirmation Lifecycle

- Confirmation records are **versioned during the active document lifecycle** — new
  state transitions (confirm, change, revoke) create new records; previous records
  are preserved as SUPERSEDED or REVOKED for traceability.
- This is NOT an "immutable forever" guarantee: deleting the parent document
  cascades to delete all associated confirmation records (CASCADE DELETE).
- The history provides **cooperative integrity** for the user's own reference.
  It does NOT provide cryptographic tamper resistance (documented as INV-M6A-24).
- Revocation creates a new event; the old one remains visible in history as SUPERSEDED.

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

## Source Classification Methodology

Sources are classified according to the following hierarchy:

| Type | Description | Examples |
|------|-------------|----------|
| `OFFICIAL_PRIMARY_NORM` | Official legal text published by the legislator or authorized government body | EUR-Lex, gesetze-im-internet.de, Bundesgesetzblatt, official Landesrecht portals |
| `OFFICIAL_GUIDANCE` | Official guidance from supervisory authorities or government bodies | BfDI, EDPB, Datenschutzkonferenz (DSK), Landesdatenschutzbehörden |
| `SECONDARY_SOURCE` | Private legal information platforms without official status | dejure.org, legal databases, commentaries, textbooks, Wikipedia |
| `TECHNICAL_PRIMARY_DOCUMENTATION` | Official documentation for software/libraries | Python `datetime` documentation (docs.python.org) |
| `INTERNAL_PRODUCT_POLICY` | Project-internal governance documents | Constitution, ADRs |

**Counting rule:** Each unique official document (law, regulation, directive) counts as one source.
Multiple paragraphs of the same law are not counted as separate independent sources.

---

## Official Primary Norm Sources (Normative)

| # | Norm | Authority | Legal Area | Source Type | Accessed |
|---|------|-----------|------------|-------------|----------|
| 1 | BGB (Bürgerliches Gesetzbuch) | Bundesrepublik Deutschland | Zivilrecht | OFFICIAL_PRIMARY_NORM | gesetze-im-internet.de, 2026-07-14 |
| 2 | ZPO (Zivilprozessordnung) | Bundesrepublik Deutschland | Zivilprozessrecht | OFFICIAL_PRIMARY_NORM | gesetze-im-internet.de, 2026-07-14 |
| 3 | VwVfG (Verwaltungsverfahrensgesetz) | Bundesrepublik Deutschland | Verwaltungsrecht | OFFICIAL_PRIMARY_NORM | gesetze-im-internet.de, 2026-07-14 |
| 4 | VwZG (Verwaltungszustellungsgesetz) | Bundesrepublik Deutschland | Verwaltungsrecht | OFFICIAL_PRIMARY_NORM | gesetze-im-internet.de, 2026-07-14 |
| 5 | DSGVO (Datenschutz-Grundverordnung) | Europäische Union | Datenschutzrecht | OFFICIAL_PRIMARY_NORM | EUR-Lex 32016R0679, 2026-07-14 |

**Total official primary norm sources: 5** (covering §§ 130, 166-195, 187-193, 222 BGB/ZPO; §§ 41, 43 VwVfG; §§ 3-4 VwZG; Artt. 2, 5, 6, 15, 17, 22, 25, 30 DSGVO)

## Technical Primary Documentation

| # | Source | Type |
|---|--------|------|
| 1 | Python `datetime` module documentation | TECHNICAL_PRIMARY_DOCUMENTATION |

## Secondary Sources (Orientation Only)

| # | Source | Type | Usage |
|---|--------|------|-------|
| 1 | dejure.org | SECONDARY_SOURCE | Convenience reference for text lookup; normative claims verified against official sources |

## Internal Product Policy

| # | Source | Type |
|---|--------|------|
| 1 | PrivateLegalNavigator Constitution | INTERNAL_PRODUCT_POLICY |

**Summary:** 5 official primary norm sources, 1 technical primary documentation, 1 secondary source, 1 internal project source. Total: 8 unique source documents.

---

## Risk Register

| Risk | Severity | Mitigation |
|------|----------|-----------|
| User treats calculated date as binding, misses real deadline | HIGH | Mandatory disclaimers, `human_review_required: true`, no "Frist" terminology, warning badges |
| Risk of automated decision with legal effect (Art. 22 DSGVO) | DEPLOYMENT_DEPENDENT | Confirmation gate + mandatory human review ensure no calculation occurs without explicit user action. Art. 22 applicability depends on whether the specific deployment context involves automated decisions with legal effect. The product is designed as a non-binding calculation preview — not as an automated decision-making system. |
| Days-only arithmetic produces weekend/holiday date, user relies on it | MEDIUM | Warning: "Keine Feiertage berücksichtigt. Rechtliche Frist kann abweichen." |
| User selects wrong reference event type | MEDIUM | Event type selection is user-controlled, clear warnings |
| False sense of security from "confirmed" label | MEDIUM | "Bestätigt" only means reference date confirmed — NOT that calculation is legally binding |
