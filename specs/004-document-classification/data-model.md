# Data Model — M4 Document Classification

## Neue Felder: documents-Tabelle

```sql
ALTER TABLE documents ADD COLUMN doc_type TEXT NOT NULL DEFAULT 'sonstiges';
ALTER TABLE documents ADD COLUMN classification_confidence REAL NOT NULL DEFAULT 0.0;
ALTER TABLE documents ADD COLUMN matched_patterns TEXT NOT NULL DEFAULT '[]';
```

Hinweis: `matched_patterns` wird als JSON-Array in einer TEXT-Spalte gespeichert (siehe research.md R02). Speicherformat: `["pattern1", "pattern2"]`. Empty array `[]` ist der Default für nicht klassifizierte/leere Dokumente.

## Domain: ClassificationResult

```python
@dataclass
class ClassificationResult:
    doc_type: str          # "bescheid" | "rechnung" | ...
    confidence: float      # 0.0 - 1.0
    matched_patterns: list[str]  # Welche Keywords haben gematcht
```

**Invarianten:**
- `confidence` muss im Bereich `[0.0, 1.0]` liegen
- Bei `confidence < 0.5` wird `doc_type` automatisch auf `"sonstiges"` gesetzt (Threshold exclusiv: genau 0.5 bleibt bestehen)
- Bei leerem Text oder 0 Matches: `doc_type="sonstiges"`, `confidence=0.0`, `matched_patterns=[]`

## Entity-Erweiterung: Document

| Feld | Typ | Änderung |
|------|-----|----------|
| doc_type | str | NEU: klassifizierter Dokumenttyp |
| classification_confidence | float | NEU: 0.0–1.0 |
| matched_patterns | list[str] | NEU: gematchte Pattern-Strings (als JSON TEXT in DB) |

## Classification Algorithm

**Confidence (Ratio-Modell):**
```
confidence = count_matched_patterns_of_winning_type / total_patterns_of_winning_type
```

**Tie-Breaking:**
1. Typ mit höchstem Ratio-Score gewinnt
2. Bei Gleichstand: erster Typ in Definitionsreihenfolge (Reihenfolge in `PATTERNS`-Dict)

**Beispiel:**
- bescheid: 15 Patterns, 8 gematcht → Ratio = 8/15 = 0.53
- rechnung: 15 Patterns, 3 gematcht → Ratio = 3/15 = 0.20
- Gewinner: bescheid (0.53), Confidence = 0.53

## API

Klassifikation ist Teil der DocumentResponse:

```json
{
  "document_id": "...",
  "doc_type": "bescheid",
  "classification_confidence": 0.85,
  "matched_patterns": ["bescheid", "steuerbescheid", "festsetzung"],
  ...
}
```
