# Data Model — M3 Text Extraction

## Erweiterung: documents-Tabelle

Neues Feld `text_content`:

```sql
ALTER TABLE documents ADD COLUMN text_content TEXT NOT NULL DEFAULT '';
```

## Entity-Erweiterung: Document

| Feld | Typ | Änderung |
|------|-----|----------|
| text_content | str | NEU: Extrahierter Text (leer wenn kein Text) |

## API Contract

```
GET /api/v1/cases/{case_id}/documents/{document_id}/text
```

**Response 200:**
```json
{
  "document_id": "660e8400-...",
  "text_content": "Extrahierter Text aus dem PDF...",
  "text_length": 1234
}
```

**Response 404:**
```json
{"error": {"code": "DOCUMENT_NOT_FOUND", "message": "..."}}
```
