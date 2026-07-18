# API Contract — M4 Document Classification

## Overview

Classification extends the existing document endpoints with `doc_type`, `classification_confidence`, and `matched_patterns` fields. No new endpoints are required.

## Affected Endpoints

### POST /api/v1/cases/{case_id}/documents

Upload a document. Classification runs synchronously after text extraction.

**Request**: Same as M3 (multipart upload with `file` field).

**Response** (201 Created):
```json
{
  "document_id": "uuid",
  "case_id": "uuid",
  "filename": "bescheid.pdf",
  "mime_type": "application/pdf",
  "size_bytes": 12345,
  "created_at": "2026-07-18T12:00:00Z",
  "doc_type": "bescheid",
  "classification_confidence": 0.85,
  "matched_patterns": ["bescheid", "festsetzung"]
}
```

### GET /api/v1/cases/{case_id}/documents

List documents for a case.

**Response** (200 OK):
```json
{
  "items": [
    {
      "document_id": "uuid",
      "case_id": "uuid",
      "filename": "bescheid.pdf",
      "mime_type": "application/pdf",
      "size_bytes": 12345,
      "created_at": "2026-07-18T12:00:00Z",
      "doc_type": "bescheid",
      "classification_confidence": 0.85,
      "matched_patterns": ["bescheid", "festsetzung"]
    }
  ],
  "count": 1
}
```

### GET /api/v1/cases/{case_id}/documents/{document_id}/text

Get extracted text and classification.

**Response** (200 OK):
```json
{
  "document_id": "uuid",
  "text_content": "extracted text...",
  "text_length": 1234
}
```
Note: Classification fields are not included in this response (see FR-M4-06 — classification is in DocumentResponse, not DocumentTextResponse).

## Field Definitions

| Field | Type | Always Present | Description |
|-------|------|----------------|-------------|
| `doc_type` | string | ✅ Yes | Classified document type: `bescheid`, `rechnung`, `mahnung`, `vertrag`, `widerspruch`, or `sonstiges` |
| `classification_confidence` | float | ✅ Yes | Confidence score 0.0–1.0 (ratio-model: matched/total patterns of winning type) |
| `matched_patterns` | string[] | ✅ Yes | List of regex pattern strings that matched (empty `[]` for sonstiges/unrecognized) |

## Error Responses (classification-specific)

No new error codes. Classification failures result in `sonstiges` with `confidence=0.0`. The upload remains successful (201).

| Condition | doc_type | confidence | matched_patterns |
|-----------|----------|------------|-----------------|
| Normal classification | `bescheid`/etc. | 0.0–1.0 | Pattern strings |
| Empty/no text extracted | `sonstiges` | 0.0 | `[]` |
| No patterns match | `sonstiges` | 0.0 | `[]` |
| Exactly 0.5 confidence | Winning type | 0.5 | Pattern strings (threshold is exclusive `< 0.5`) |
