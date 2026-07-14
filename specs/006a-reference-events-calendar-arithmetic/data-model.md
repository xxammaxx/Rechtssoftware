# Data Model — M6-A Reference Events and Calendar Arithmetic

## Overview

M6-A introduces three new domain concepts:
1. **ReferenceEventCandidate** — a possible reference point detected from document text
2. **ConfirmedReferenceEvent** — a user-confirmed reference date with audit trail
3. **CalendarCalculationCandidate** — the result of arithmetic addition

These extend M5's existing `DeadlineCandidate` and `DeadlineExtractionResult` without modifying them.

---

## Persistenzentscheidung

### Variant B (Selected): Confirmation Persistent, Calculation On-Demand

| What is stored | What is computed |
|---------------|-----------------|
| Confirmed reference events | Calendar calculation candidates |
| Confirmation audit trail | Calculation steps |
| Provenance of reference date | Result warnings |

**Rationale:**
- Auditierbarkeit: Jede Bestätigung ist nachvollziehbar
- Reproduzierbarkeit: Berechnungen sind aus bestätigtem Datum + M5-Dauer jederzeit reproduzierbar
- Keine Stale Results: Bei Änderung des Bezugsdatums wird neu berechnet
- Kleinste Schemaerweiterung: Nur eine neue Tabelle (confirmed_reference_events)
- CASCADE DELETE: Bei Dokumentlöschung werden Bestätigungen automatisch gelöscht

**Comparison of variants:**
- **Variant A (Fully On-Demand):** Keine Bestätigung gespeichert → keine Auditierbarkeit → abgelehnt
- **Variant B (Confirmation Persistent, Calculation On-Demand):** Bestätigung gespeichert, Berechnung bei Bedarf neu → **GEWÄHLT**
- **Variant C (Both Persistent):** Historisch exakt reproduzierbar, aber Stale-Results-Risiko und größere Komplexität → für M6-A überdimensioniert

---

## Domain Entities

### ReferenceEventCandidate

A possible reference event detected in document text. Represents a point in time that could serve as the reference for a relative deadline.

```python
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from uuid import UUID

class EventType(StrEnum):
    """Semantic categories of reference events.
    
    These describe what the event IS, not what legal significance it has.
    """
    DELIVERY = "delivery"           # Zustellung
    ANNOUNCEMENT = "announcement"   # Bekanntgabe
    RECEIPT = "receipt"             # Zugang / Erhalt
    ISSUE_DATE = "issue_date"       # Ausstellungsdatum / Bescheiddatum
    PUBLICATION = "publication"     # Veröffentlichung
    APPLICATION = "application"     # Antragstellung
    USER_DEFINED = "user_defined"   # Nutzerdefiniert
    UNKNOWN = "unknown"             # Nicht klassifiziert

class ConfirmationStatus(StrEnum):
    """Lifecycle state of a reference event confirmation."""
    UNCONFIRMED = "unconfirmed"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    REVOKED = "revoked"
    SUPERSEDED = "superseded"

class SourceType(StrEnum):
    """Origin of the reference date."""
    AUTO_DETECTED = "auto_detected"      # System detected from document text
    USER_MANUAL = "user_manual"          # User entered manually
    USER_CORRECTED = "user_corrected"    # System suggested, user modified

class ConfirmationMethod(StrEnum):
    """How the reference date was established."""
    AUTO_SUGGESTED = "auto_suggested"    # System suggested, user accepted
    MANUALLY_ENTERED = "manually_entered" # User typed date directly
    CORRECTED = "corrected"              # System suggested, user modified

@dataclass
class ReferenceEventCandidate:
    """A candidate reference event that could anchor a relative deadline.
    
    Attributes:
        candidate_id: Unique identifier for this candidate
        document_id: The document this was detected in
        deadline_candidate_id: The M5 DeadlineCandidate this relates to (if any)
        event_type: Semantic category of the event
        suggested_date: The date detected or suggested
        source_type: Where this candidate came from (auto-detected, user, etc.)
        source_reference: Reference to the originating data
        evidence_text: The original text that was the basis
        start_offset: Character offset in the document text
        end_offset: Character offset in the document text
        confirmation_status: Current lifecycle state
    """
    candidate_id: UUID
    document_id: UUID
    deadline_candidate_id: UUID | None = None
    event_type: EventType = EventType.UNKNOWN
    suggested_date: date | None = None
    source_type: SourceType = SourceType.AUTO_DETECTED
    source_reference: str = ""          # max 100 chars
    evidence_text: str = ""             # max 2000 chars (not persisted)
    start_offset: int = 0
    end_offset: int = 0
    confirmation_status: ConfirmationStatus = ConfirmationStatus.UNCONFIRMED
```

### ConfirmedReferenceEvent

A user-confirmed reference date. This is the persistent entity — confirmation is an explicit, auditable action.

```python
from datetime import datetime

@dataclass
class ConfirmedReferenceEvent:
    """An explicitly confirmed reference date with full audit trail.
    
    Once confirmed, this enables calendar arithmetic.
    The confirmation is immutable — changes create new records.
    
    Attributes:
        confirmation_id: Unique identifier for this confirmation
        candidate_id: The candidate this confirmation refers to (null if manual)
        document_id: The document context
        event_type: User-selected event category
        confirmed_date: The user-confirmed reference date
        source_type: Where the date came from
        confirmation_method: How the user confirmed
        confirmed_at: Timestamp of confirmation (UTC)
        confirmed_by: Human identifier (future: user ID)
        supersedes_confirmation_id: Previous confirmation this replaces (null if first)
    """
    confirmation_id: UUID
    candidate_id: UUID | None
    document_id: UUID
    event_type: EventType
    confirmed_date: date
    source_type: SourceType
    confirmation_method: ConfirmationMethod
    confirmed_at: datetime
    confirmed_by: str = ""              # max 100 chars
    evidence_note: str = ""             # max 2000 chars (transient, not persisted)
    supersedes_confirmation_id: UUID | None = None
```

### Duration

The time amount and unit extracted from a relative deadline candidate.

```python
class DurationUnit(StrEnum):
    """Supported duration units for arithmetic calculation."""
    DAY = "day"
    WEEK = "week"
    # NOT SUPPORTED in M6-A:
    # MONTH = "month"
    # YEAR = "year"
    # BUSINESS_DAY = "business_day"
    # WORKING_DAY = "working_day"
    # HOUR = "hour"

@dataclass(frozen=True)
class Duration:
    """A duration amount with unit for arithmetic calculation.
    
    Only DAY and WEEK are supported in M6-A.
    Frozen to ensure immutability.
    """
    amount: int
    unit: DurationUnit
    
    @property
    def calendar_days(self) -> int:
        """Convert to calendar days for arithmetic."""
        if self.unit == DurationUnit.WEEK:
            return self.amount * 7
        return self.amount
    
    def __post_init__(self) -> None:
        if self.amount <= 0:
            raise ValueError("Duration amount must be positive")
        if self.amount > 36500:
            raise ValueError("Duration exceeds maximum (36500 days / ~100 years)")
```

### CalendarCalculationCandidate

The result of arithmetic addition — a non-binding calculation preview.

```python
from dataclasses import dataclass
from typing import Any

class CalculationOperation(StrEnum):
    """Arithmetic operations for calendar calculation."""
    ADD_CALENDAR_DAYS = "ADD_CALENDAR_DAYS"
    ADD_CALENDAR_WEEKS = "ADD_CALENDAR_WEEKS"

@dataclass
class CalculationStep:
    """A single step in the arithmetic calculation.
    
    Attributes:
        step: Sequence number (1-based)
        operation: The arithmetic operation performed
        input_date: The date before the operation (ISO format)
        amount: Number of calendar days added
        output_date: The resulting date (ISO format)
    """
    step: int
    operation: CalculationOperation
    input_date: date
    amount: int
    output_date: date

@dataclass
class CalendarCalculationCandidate:
    """The result of calendar arithmetic — a non-binding calculation preview.
    
    This is NOT a legal deadline. It is a purely mathematical date calculation.
    
    Attributes:
        calculation_id: Unique identifier for this calculation
        confirmed_reference_event: The user-confirmed reference date
        duration: The duration used for calculation
        calculated_date: The resulting date
        calculation_steps: Step-by-step arithmetic trail
        adjustments_applied: Summary of what adjustments were (not) applied
        legal_validity_assessed: Always false — no legal assessment
        human_review_required: Always true — mandatory human review
        warnings: Warning codes describing limitations
    """
    calculation_id: UUID | None = None
    confirmed_reference_event: ConfirmedReferenceEvent | None = None
    duration: Duration | None = None
    calculated_date: date | None = None
    calculation_steps: list[CalculationStep] = field(default_factory=list)
    adjustments_applied: dict[str, bool] = field(default_factory=lambda: {
        "weekend_adjustment_applied": False,
        "holiday_adjustment_applied": False,
        "legal_rule_applied": False,
        "delivery_fiction_applied": False,
        "announcement_fiction_applied": False,
    })
    legal_validity_assessed: bool = False
    human_review_required: bool = True
    warnings: list[str] = field(default_factory=list)
```

---

## Warning Codes (Domain)

Extension of M5's `DeadlineWarningCode`:

```python
class CalculationWarningCode(StrEnum):
    """Warning codes specific to calendar calculation."""
    # Inherited from M5:
    LEGAL_CALCULATION_NOT_PERFORMED = "LEGAL_CALCULATION_NOT_PERFORMED"
    MULTIPLE_DEADLINE_CANDIDATES = "MULTIPLE_DEADLINE_CANDIDATES"
    
    # M6-A — Confirmation gates:
    REFERENCE_EVENT_NOT_CONFIRMED = "REFERENCE_EVENT_NOT_CONFIRMED"
    REFERENCE_EVENT_REJECTED = "REFERENCE_EVENT_REJECTED"
    REFERENCE_EVENT_REVOKED = "REFERENCE_EVENT_REVOKED"
    MULTIPLE_REFERENCE_EVENTS = "MULTIPLE_REFERENCE_EVENTS"
    
    # M6-A — Duration validation:
    REFERENCE_DATE_REQUIRED = "REFERENCE_DATE_REQUIRED"
    DURATION_NOT_AVAILABLE = "DURATION_NOT_AVAILABLE"
    UNSUPPORTED_DURATION_UNIT = "UNSUPPORTED_DURATION_UNIT"
    INVALID_DURATION_AMOUNT = "INVALID_DURATION_AMOUNT"
    DURATION_LIMIT_EXCEEDED = "DURATION_LIMIT_EXCEEDED"
    
    # M6-A — Safety disclaimers:
    NO_WEEKEND_OR_HOLIDAY_ADJUSTMENT = "NO_WEEKEND_OR_HOLIDAY_ADJUSTMENT"
    NO_DELIVERY_OR_ANNOUNCEMENT_RULE_APPLIED = "NO_DELIVERY_OR_ANNOUNCEMENT_RULE_APPLIED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    CALCULATION_PREVIEW_ONLY = "CALCULATION_PREVIEW_ONLY"
    CALCULATION_NOT_PERFORMED = "CALCULATION_NOT_PERFORMED"
```

---

## Datenbank-Schema (für zukünftigen Build)

```sql
-- Confirmed reference events (persistent per Variant B)
CREATE TABLE IF NOT EXISTS confirmed_reference_events (
    confirmation_id TEXT PRIMARY KEY,
    candidate_id TEXT,
    document_id TEXT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    confirmed_date TEXT NOT NULL,      -- ISO date: YYYY-MM-DD
    source_type TEXT NOT NULL DEFAULT '',
    confirmation_method TEXT NOT NULL,
    confirmed_at TEXT NOT NULL,        -- ISO datetime with timezone
    confirmed_by TEXT NOT NULL DEFAULT '',
    supersedes_confirmation_id TEXT,
    FOREIGN KEY (document_id) REFERENCES documents(document_id)
);

CREATE INDEX IF NOT EXISTS idx_confirmed_reference_events_document
    ON confirmed_reference_events(document_id);
```

---

## Compliance-Annotationen

| DSGVO-Artikel | Umsetzung in M6-A |
|---------------|-----------------|
| Art. 5(1)(c) — Data Minimization | Nur bestätigte Bezugsdaten gespeichert; keine umliegenden personenbezogenen Daten |
| Art. 5(1)(e) — Storage Limitation | Bestätigungen an Dokument gebunden; CASCADE DELETE bei Dokumentlöschung |
| Art. 15 — Right of Access | Alle Bestätigungen pro Dokument abrufbar |
| Art. 17 — Right to Erasure | CASCADE DELETE über Dokument → alle Bestätigungen gelöscht |
| Art. 22 — Automated Decisions | Keine automatische Rechtsentscheidung; zwingende Nutzerbestätigung |
| Art. 25 — Data Protection by Design | Local-only; keine externen Requests; keine Bezugsdaten in Logs |
| Art. 30 — Records of Processing | Bestätigungs-Timestamp als Audit-Trail |

## DSGVO Art. 6 — Rechtsgrundlagen der Verarbeitung

**Verantwortlicher:** Die natürliche Person, die die Software auf ihrem lokalen Rechner nutzt (Local-Only-Tool).

**Verarbeitungszwecke und Rechtsgrundlagen:**

| Verarbeitung | Zweck | Rechtsgrundlage |
|-------------|-------|----------------|
| Speicherung des bestätigten Bezugsdatums (`confirmed_date`) | Kalenderarithmetik für eigene Fallverwaltung | Art. 6(1)(f) — Berechtigtes Interesse |
| Speicherung des Bestätigungs-Audit-Trails (`confirmed_at`, `confirmed_by`) | Nachvollziehbarkeit und Rechenschaftspflicht | Art. 6(1)(c) — Rechtliche Verpflichtung (Art. 5(2), Art. 30 DSGVO) |
| Speicherung des `event_type` | Semantische Kategorisierung des Bezugsereignisses | Art. 6(1)(f) — Berechtigtes Interesse |
| Transientes `evidence_note` (nicht persistiert) | Dokumentation der Bestätigungsgrundlage in der API-Antwort | Art. 6(1)(f) — Berechtigtes Interesse |

**Empfänger:** Keine. Daten verlassen den lokalen Rechner nicht.

**Speicherdauer:** Bis zur Löschung des referenzierten Dokuments (CASCADE DELETE) oder bis zur manuellen Löschung durch den Nutzer.

**Betroffenenrechte:** Auskunft (GET history endpoint), Löschung (CASCADE DELETE über Dokument), Berichtigung (Änderung = neuer Datensatz, alter bleibt SUPERSEDED).

---

## Datenfluss

```
M5 DeadlineCandidate (RELATIVE_PERIOD, amount=2, unit="Woche")
  │
  ▼
ReferenceEventCandidate (event_type=DELIVERY, suggested_date=2026-07-15, status=UNCONFIRMED)
  │
  │  Explicit user action: "Bestätigen"
  ▼
ConfirmedReferenceEvent (confirmed_date=2026-07-15, method=AUTO_SUGGESTED, confirmed_at=...)
  │
  │  User requests calculation preview
  ▼
Duration(amount=2, unit=WEEK, calendar_days=14)
  │
  ▼
CalendarArithmetic.add_calendar_days(date(2026-07-15), 14)
  │
  ▼
CalendarCalculationCandidate(
    calculated_date=date(2026-07-29),
    calculation_steps=[CalculationStep(1, ADD_CALENDAR_DAYS, date(2026-07-15), 14, date(2026-07-29))],
    legal_validity_assessed=false,
    human_review_required=true,
    adjustments_applied={weekend: false, holiday: false, legal_rule: false}
)
```
