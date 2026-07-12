# API Contracts — M2 Document Import

## Dokument hochladen

```
POST /api/v1/cases/{case_id}/documents
Content-Type: multipart/form-data

Field: file (PDF, max 20 MB)
```

**Response 201:**
```json
{
  "document_id": "660e8400-e29b-41d4-a716-446655440001",
  "case_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "bescheid.pdf",
  "mime_type": "application/pdf",
  "size_bytes": 12345,
  "created_at": "2026-07-12T10:00:00Z"
}
```

**Response 404 (Case nicht gefunden):**
```json
{"error": {"code": "CASE_NOT_FOUND", "message": "..."}}
```

**Response 400 (kein PDF):**
```json
{"error": {"code": "INVALID_FILE_TYPE", "message": "Nur PDF-Dateien sind erlaubt."}}
```

**Response 413 (zu groß):**
```json
{"error": {"code": "FILE_TOO_LARGE", "message": "Die Datei überschreitet die maximale Größe von 20 MB."}}
```

---

## Dokumente eines Falls auflisten

```
GET /api/v1/cases/{case_id}/documents
```

**Response 200:**
```json
{
  "items": [
    {
      "document_id": "660e8400-...",
      "case_id": "550e8400-...",
      "filename": "bescheid.pdf",
      "mime_type": "application/pdf",
      "size_bytes": 12345,
      "created_at": "2026-07-12T10:00:00Z"
    }
  ],
  "count": 1
}
```

---

## Dokument herunterladen

```
GET /api/v1/cases/{case_id}/documents/{document_id}
```

**Response 200:**
- Content-Type: application/pdf
- Content-Disposition: inline; filename="bescheid.pdf"
- Body: Binärdaten

**Response 404:**
```json
{"error": {"code": "DOCUMENT_NOT_FOUND", "message": "..."}}
```

---

## Fehlercodes (neu)

- `CASE_NOT_FOUND` — Fall existiert nicht
- `DOCUMENT_NOT_FOUND` — Dokument existiert nicht
- `INVALID_FILE_TYPE` — Kein PDF
- `FILE_TOO_LARGE` — Über 20 MB
