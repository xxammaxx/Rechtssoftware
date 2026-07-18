# API Contracts — M3 Dokumenttextgewinnung

## Dokument hochladen (mit Textextraktion)

```
POST /api/v1/cases/{case_id}/documents
Content-Type: multipart/form-data
```

**Request:**
```
file: @dokument.pdf (application/pdf)
```

**Response 201 (Erfolg):**
```json
{
  "document_id": "660e8400-...",
  "case_id": "550e8400-...",
  "filename": "bescheid.pdf",
  "mime_type": "application/pdf",
  "size_bytes": 123456,
  "created_at": "2026-07-18T10:00:00Z"
}
```

Die Textextraktion erfolgt synchron während des Uploads. Bei Extraktionsfehlern
wird der Upload trotzdem durchgeführt — der Fehler ist über `GET .../text`
einsehbar.

**Response 404 (Fall nicht gefunden):**
```json
{"error": {"code": "CASE_NOT_FOUND", "message": "Der angeforderte Fall wurde nicht gefunden."}}
```

**Response 400 (Validierungsfehler):**
```json
{"error": {"code": "VALIDATION_ERROR", "message": "Nur PDF-Dateien sind erlaubt."}}
```

---

## Extrahierten Text abrufen

```
GET /api/v1/cases/{case_id}/documents/{document_id}/text
```

**Response 200 (Text extrahiert):**
```json
{
  "document_id": "660e8400-...",
  "text_content": "Extrahierter Text aus dem PDF...",
  "text_length": 1234,
  "extraction_error": null
}
```

**Response 200 (kein Textlayer — z. B. gescanntes PDF):**
```json
{
  "document_id": "660e8400-...",
  "text_content": "",
  "text_length": 0,
  "extraction_error": null
}
```

**Response 200 (Extraktionsfehler — verschlüsselte PDF):**
```json
{
  "document_id": "660e8400-...",
  "text_content": "",
  "text_length": 0,
  "extraction_error": "PDF ist verschlüsselt"
}
```

**Response 200 (Extraktionsfehler — korrupte PDF):**
```json
{
  "document_id": "660e8400-...",
  "text_content": "",
  "text_length": 0,
  "extraction_error": "PDF ist korrupt"
}
```

**Response 404:**
```json
{"error": {"code": "DOCUMENT_NOT_FOUND", "message": "Das angeforderte Dokument wurde nicht gefunden."}}
```

---

## Fehlerformat (unverändert — siehe M1)

Alle Fehlerantworten folgen dem Schema aus M1:

```json
{
  "error": {
    "code": "MACHINE_READABLE_CODE",
    "message": "Menschenlesbare Beschreibung"
  }
}
```

**Fehlercodes (Erweiterung):**
- `DOCUMENT_NOT_FOUND` — Dokument existiert nicht (bereits M2)

---

## Datenmodell-Änderungen

### documents-Tabelle — neue Spalte

```sql
ALTER TABLE documents ADD COLUMN extraction_error TEXT DEFAULT NULL;
```

### Document-Entity — neues Feld

| Feld | Typ | Beschreibung |
|------|-----|-------------|
| extraction_error | str \| None | Fehlermeldung bei fehlgeschlagener Extraktion (null bei Erfolg) |

### Dokumenten-Liste (unverändert)

`GET /api/v1/cases/{case_id}/documents` — Response enthält **kein** `extraction_error`.
Dieses Feld ist nur über den dedizierten Text-Endpunkt abrufbar.
