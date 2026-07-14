# API Contract — M5 Deadline Candidate Extraction

## Endpoint

```
POST /api/v1/cases/{case_id}/documents/{document_id}/deadline-candidates
```

## Request

Kein Request-Body erforderlich. Die Analyse erfolgt auf dem bereits
extrahierten `text_content` des Dokuments.

### Pfad-Parameter

| Parameter | Typ | Beschreibung |
|-----------|-----|-------------|
| `case_id` | UUID | ID des Falls |
| `document_id` | UUID | ID des Dokuments |

## Response

### 200 OK — Erfolg

```json
{
  "document_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "candidates": [
    {
      "kind": "explicit_date",
      "raw_text": "bis spätestens 31. Juli 2026",
      "start_offset": 120,
      "end_offset": 151,
      "normalized_date": "2026-07-31",
      "amount": null,
      "unit": null,
      "reference_required": false,
      "certainty": "exact",
      "rule_id": "DEADLINE_DATE_TEXTUAL_DE_V1"
    }
  ],
  "warnings": [
    {
      "code": "LEGAL_CALCULATION_NOT_PERFORMED",
      "message": "Es wurde keine rechtliche Frist berechnet. Nur Textstellen erkannt."
    }
  ],
  "human_review_required": true
}
```

### Feld-Beschreibung

| Feld | Typ | Beschreibung |
|------|-----|-------------|
| `document_id` | UUID | Dokument-ID |
| `candidates` | Array | Liste der Fristkandidaten (leer wenn keine gefunden) |
| `candidates[].kind` | Enum | `explicit_date`, `relative_period`, `qualitative_reference` |
| `candidates[].raw_text` | String | Originaler Textausschnitt aus dem Dokument |
| `candidates[].start_offset` | Integer | Zeichenposition (Start) im extrahierten Text |
| `candidates[].end_offset` | Integer | Zeichenposition (Ende) im extrahierten Text |
| `candidates[].normalized_date` | String\|null | ISO-Datum (YYYY-MM-DD) oder null |
| `candidates[].amount` | Integer\|null | Numerischer Betrag für relative Zeiträume |
| `candidates[].unit` | String\|null | Zeiteinheit für relative Zeiträume |
| `candidates[].reference_required` | Boolean | `true` wenn ein Bezugspunkt benötigt wird |
| `candidates[].certainty` | Enum | `exact`, `unresolved`, `ambiguous` |
| `candidates[].rule_id` | String | Stabile Regel-ID |
| `warnings` | Array | Immer mindestens `LEGAL_CALCULATION_NOT_PERFORMED` |
| `warnings[].code` | Enum | Stabiler Warncode |
| `warnings[].message` | String | Deutsche Beschreibung |
| `human_review_required` | Boolean | Immer `true` |

### 404 Not Found — Dokument oder Case nicht gefunden

```json
{
  "error": {
    "code": "DOCUMENT_NOT_FOUND",
    "message": "Das Dokument wurde nicht gefunden."
  }
}
```

### 413 Content Too Large — Text zu groß

```json
{
  "error": {
    "code": "TEXT_TOO_LARGE",
    "message": "Der Dokumenttext ist zu groß (max. 500.000 Zeichen)."
  }
}
```

### 500 Internal Server Error — Regex-Timeout

```json
{
  "error": {
    "code": "EXTRACTION_TIMEOUT",
    "message": "Die Fristextraktion hat das Zeitlimit überschritten."
  }
}
```

## Pydantic-Schemas

```python
from pydantic import BaseModel, Field
from datetime import date
from uuid import UUID
from enum import StrEnum

class DeadlineCandidateKindSchema(StrEnum):
    EXPLICIT_DATE = "explicit_date"
    RELATIVE_PERIOD = "relative_period"
    QUALITATIVE_REFERENCE = "qualitative_reference"

class DeadlineCertaintySchema(StrEnum):
    EXACT = "exact"
    UNRESOLVED = "unresolved"
    AMBIGUOUS = "ambiguous"

class DeadlineWarningCodeSchema(StrEnum):
    LEGAL_CALCULATION_NOT_PERFORMED = "LEGAL_CALCULATION_NOT_PERFORMED"
    NO_DEADLINE_CANDIDATE = "NO_DEADLINE_CANDIDATE"
    MULTIPLE_DEADLINE_CANDIDATES = "MULTIPLE_DEADLINE_CANDIDATES"
    RELATIVE_REFERENCE_REQUIRED = "RELATIVE_REFERENCE_REQUIRED"
    AMBIGUOUS_DATE = "AMBIGUOUS_DATE"

class DeadlineCandidateResponse(BaseModel):
    kind: DeadlineCandidateKindSchema
    raw_text: str
    start_offset: int
    end_offset: int
    normalized_date: date | None = None
    amount: int | None = None
    unit: str | None = None
    reference_required: bool = False
    certainty: DeadlineCertaintySchema
    rule_id: str

class DeadlineWarningResponse(BaseModel):
    code: DeadlineWarningCodeSchema
    message: str

class DeadlineExtractionResponse(BaseModel):
    document_id: UUID
    candidates: list[DeadlineCandidateResponse] = Field(default_factory=list)
    warnings: list[DeadlineWarningResponse] = Field(default_factory=list)
    human_review_required: bool = True
```

## Sicherheitsanforderungen

- Keine Dokumenttexte in Fehlerantworten
- Keine Stacktraces, keine Dateipfade, keine SQL
- Alle Fehler über zentrale Exception-Handler
- Regex-Timeout max. 5 Sekunden
- Maximale Textlänge 500.000 Zeichen
- Keine externen Requests
- Nur 127.0.0.1
