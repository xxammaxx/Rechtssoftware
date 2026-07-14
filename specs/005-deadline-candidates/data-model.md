# Data Model — M5 Deadline Candidate Extraction

## Design Decision: Analyse-on-demand (keine neue Persistenztabelle)

M5 persistiert keine Deadline Candidates. Gründe:
- Kleinster Vertical Slice — keine vorzeitige Schemaerweiterung
- Ergebnisse bleiben aus `Document.text_content` reproduzierbar
- M6 könnte ein anderes Datenmodell erfordern
- Kein Kaskadierungsproblem bei Dokumentlöschung

Die API-Antwort IST die Evidence. Der `DeadlineCandidate`-Dataclass ist so
gestaltet, dass `dataclasses.asdict()` eine JSON-serialisierbare Struktur liefert.

Falls zukünftige Versionen Persistenz benötigen, kann der Dataclass unverändert
in eine Datenbanktabelle überführt werden.

---

## Domain: DeadlineCandidate

```python
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum

class DeadlineCandidateKind(StrEnum):
    EXPLICIT_DATE = "explicit_date"
    RELATIVE_PERIOD = "relative_period"
    QUALITATIVE_REFERENCE = "qualitative_reference"

class DeadlineCertainty(StrEnum):
    EXACT = "exact"
    UNRESOLVED = "unresolved"
    AMBIGUOUS = "ambiguous"

@dataclass
class DeadlineCandidate:
    """A potential deadline reference found in document text.

    Attributes:
        kind: Type of deadline reference
        raw_text: Original text from the document
        start_offset: Character offset where the match starts
        end_offset: Character offset where the match ends
        normalized_date: ISO date (YYYY-MM-DD), None if unresolvable
        amount: Numeric amount for relative periods, None for explicit dates
        unit: Time unit for relative periods (Tag/Woche/Monat/Jahr)
        reference_required: True if a reference point is needed
        certainty: How certain the extraction is
        rule_id: Stable identifier for the rule that produced this candidate
    """
    kind: DeadlineCandidateKind
    raw_text: str
    start_offset: int
    end_offset: int
    normalized_date: date | None = None
    amount: int | None = None
    unit: str | None = None
    reference_required: bool = False
    certainty: DeadlineCertainty = DeadlineCertainty.EXACT
    rule_id: str = ""

    def __post_init__(self) -> None:
        if self.start_offset < 0:
            raise ValueError("start_offset must be >= 0")
        if self.end_offset < self.start_offset:
            raise ValueError("end_offset must be >= start_offset")
        if self.kind == DeadlineCandidateKind.EXPLICIT_DATE and self.normalized_date is None:
            raise ValueError("EXPLICIT_DATE must have normalized_date")
```

### Offset-Semantik

`start_offset` und `end_offset` beziehen sich auf den extrahierten Text,
wie er über `Document.text_content` (M3) verfügbar ist. Dies ist der
konkatenierte Text aller PDF-Seiten (getrennt durch `\n`).

**Bekannte Einschränkung:** Offsets können nicht direkt auf eine PDF-Seite
abgebildet werden, da die Seitengrenzen beim Extrahieren verloren gehen.
Dies ist für M5 akzeptabel — der Nutzer kann den erkannten Text im
extrahierten Volltext suchen.

---

## Domain: DeadlineWarning

```python
from dataclasses import dataclass
from enum import StrEnum

class DeadlineWarningCode(StrEnum):
    LEGAL_CALCULATION_NOT_PERFORMED = "LEGAL_CALCULATION_NOT_PERFORMED"
    NO_DEADLINE_CANDIDATE = "NO_DEADLINE_CANDIDATE"
    MULTIPLE_DEADLINE_CANDIDATES = "MULTIPLE_DEADLINE_CANDIDATES"
    RELATIVE_REFERENCE_REQUIRED = "RELATIVE_REFERENCE_REQUIRED"
    AMBIGUOUS_DATE = "AMBIGUOUS_DATE"

@dataclass
class DeadlineWarning:
    """A warning about the deadline extraction result."""
    code: DeadlineWarningCode
    message: str
```

### Warncode-Regeln

1. `LEGAL_CALCULATION_NOT_PERFORMED` — MUSS in JEDER Antwort enthalten sein (auch bei leeren Kandidatenlisten)
2. `NO_DEADLINE_CANDIDATE` — Wenn `len(candidates) == 0`
3. `MULTIPLE_DEADLINE_CANDIDATES` — Wenn `len(candidates) > 1`
4. `RELATIVE_REFERENCE_REQUIRED` — Wenn mindestens ein Kandidat `reference_required == True`
5. `AMBIGUOUS_DATE` — Wenn ein Datumsmuster gematcht wurde, aber `datetime.strptime()` einen `ValueError` wirft

---

## Datenschutz (Data Minimization)

- `raw_text` enthält NUR den gematchten Textausschnitt (Fristbezug), keine
  umliegenden personenbezogenen Daten
- Keine Speicherung von `surrounding_text`
- Keine Persistenz der Kandidaten (Analyse-on-demand)
- Bei zukünftiger Persistenz: CASCADE DELETE mit Dokument (Art. 17 DSGVO)

---

## Regel-Engine: Datenfluss

```
Document.text_content (str)
  │
  ▼
DeterministicDeadlineExtractor.extract(text)
  │
  ├── R1: NUMERIC_DATE_RE → finditer() → datetime.strptime() Validierung
  │       → DeadlineCandidate(kind=EXPLICIT_DATE, ...)
  │
  ├── R2: TEXTUAL_DATE_RE → finditer() → Monatsabgleich (hardcoded dict)
  │       → datetime.date() Konstruktion → DeadlineCandidate(kind=EXPLICIT_DATE, ...)
  │
  ├── R3: RELATIVE_NUMERIC_RE → finditer()
  │       → DeadlineCandidate(kind=RELATIVE_PERIOD, reference_required=True, ...)
  │
  ├── R4: RELATIVE_ARTICLE_RE → finditer()
  │       → DeadlineCandidate(kind=RELATIVE_PERIOD, reference_required=True, amount=1, ...)
  │
  └── R6: QUALITATIVE_RE → finditer()
          → DeadlineCandidate(kind=QUALITATIVE_REFERENCE, ...)
  
  → Deduplizierung (überlappende Offsets)
  → Sortierung nach start_offset
  → Warnung-Generierung
  → DeadlineExtractionResult
```

---

## API-Response: DeadlineExtractionResult

```python
@dataclass
class DeadlineExtractionResult:
    """Complete result of deadline candidate extraction."""
    document_id: str
    candidates: list[DeadlineCandidate]
    warnings: list[DeadlineWarning]
    human_review_required: bool = True
```

`human_review_required` ist immer `True`. Dieses Feld existiert als
explizite Sicherheits-Hard-Gate, sodass ein Frontend die Anzeige
unterdrücken kann, wenn dieser Wert nicht explizit auf `true` geprüft wurde.

---

## Compliance-Annotationen

| DSGVO-Artikel | Umsetzung in M5 |
|---------------|-----------------|
| Art. 5(1)(c) — Data Minimization | Nur gematchte Textausschnitte, keine umliegenden Daten |
| Art. 5(1)(e) — Storage Limitation | Keine Persistenz → keine Speicherfrist nötig |
| Art. 17 — Right to Erasure | Nicht anwendbar (keine separaten Daten) |
| Art. 22 — Automated Decisions | Nicht anwendbar (keine automatische Rechtsentscheidung) |
| Art. 25 — Data Protection by Design | Local-only, keine externen Requests |
