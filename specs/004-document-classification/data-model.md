# Data Model — M4 Document Classification

## Neue Felder: documents-Tabelle

```sql
ALTER TABLE documents ADD COLUMN doc_type TEXT NOT NULL DEFAULT 'sonstiges';
ALTER TABLE documents ADD COLUMN classification_confidence REAL NOT NULL DEFAULT 0.0;
```

## Domain: ClassificationResult

```python
@dataclass
class ClassificationResult:
    doc_type: str          # "bescheid" | "rechnung" | ...
    confidence: float      # 0.0 - 1.0
    matched_patterns: list[str]  # Welche Keywords haben gematcht
```

## Entity-Erweiterung: Document

| Feld | Typ | Änderung |
|------|-----|----------|
| doc_type | str | NEU: klassifizierter Dokumenttyp |
| classification_confidence | float | NEU: 0.0–1.0 |

## API

Klassifikation ist Teil der DocumentResponse:

```json
{
  "document_id": "...",
  "doc_type": "bescheid",
  "classification_confidence": 0.85,
  ...
}
```
