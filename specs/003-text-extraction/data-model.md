# Data Model — M3 Text Extraction

## Erweiterung: documents-Tabelle

Neues Feld `text_content`:

```sql
ALTER TABLE documents ADD COLUMN text_content TEXT NOT NULL DEFAULT '';
ALTER TABLE documents ADD COLUMN extraction_error TEXT DEFAULT NULL;
```

## Entity-Erweiterung: Document

| Feld | Typ | Änderung |
|------|-----|----------|
| text_content | str | NEU: Extrahierter Text (leer wenn kein Text) |
| extraction_error | str \| None | NEU: Fehlermeldung bei fehlgeschlagener Extraktion (null bei Erfolg) |

## ExtractionResult (Port-Contract)

Rückgabetyp des `TextExtractor.extract()`-Ports:

| Feld | Typ | Beschreibung |
|------|-----|-------------|
| text | str | Extrahierter Text (leer bei Fehler oder ohne Text) |
| error | str \| None | Fehlermeldung bei fehlgeschlagener Extraktion (null bei Erfolg) |

```python
from typing import NamedTuple

class ExtractionResult(NamedTuple):
    text: str
    error: str | None
```

## API Contract

```
GET /api/v1/cases/{case_id}/documents/{document_id}/text
```

**Response 200:**
```json
{
  "document_id": "660e8400-...",
  "text_content": "Extrahierter Text aus dem PDF...",
  "text_length": 1234,
  "extraction_error": null
}
```

**Response 200 (bei Extraktionsfehler):**
```json
{
  "document_id": "660e8400-...",
  "text_content": "",
  "text_length": 0,
  "extraction_error": "PDF is encrypted or password-protected"
}
```

**Response 404:**
```json
{"error": {"code": "DOCUMENT_NOT_FOUND", "message": "..."}}
```
