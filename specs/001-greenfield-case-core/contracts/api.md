# API Contracts — M1 Case Core

## Health Check

```
GET /health
```

**Response 200:**
```json
{"status": "ok"}
```

---

## Fall anlegen

```
POST /api/v1/cases
Content-Type: application/json
```

**Request:**
```json
{"title": "SYNTHETISCH – Testfall"}
```

**Response 201:**
```json
{
  "case_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "SYNTHETISCH – Testfall",
  "status": "open",
  "created_at": "2026-07-12T10:00:00Z",
  "updated_at": "2026-07-12T10:00:00Z"
}
```

**Response 422 (Validation Error):**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Der Titel darf nicht leer sein und maximal 200 Zeichen haben."
  }
}
```

---

## Fälle auflisten

```
GET /api/v1/cases
```

**Response 200:**
```json
{
  "items": [
    {
      "case_id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "SYNTHETISCH – Testfall",
      "status": "open",
      "created_at": "2026-07-12T10:00:00Z",
      "updated_at": "2026-07-12T10:00:00Z"
    }
  ],
  "count": 1
}
```

**Leere Liste:**
```json
{"items": [], "count": 0}
```

---

## Falldetail abrufen

```
GET /api/v1/cases/{case_id}
```

**Response 200:**
```json
{
  "case_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "SYNTHETISCH – Testfall",
  "status": "open",
  "created_at": "2026-07-12T10:00:00Z",
  "updated_at": "2026-07-12T10:00:00Z"
}
```

**Response 404:**
```json
{
  "error": {
    "code": "CASE_NOT_FOUND",
    "message": "Der angeforderte Fall wurde nicht gefunden."
  }
}
```

---

## Fehlerformat

Alle Fehlerantworten folgen diesem Schema:

```json
{
  "error": {
    "code": "MACHINE_READABLE_CODE",
    "message": "Menschenlesbare Beschreibung"
  }
}
```

**Fehlercodes:**
| HTTP-Status | Code | Beschreibung |
|-------------|------|-------------|
| 422 | `VALIDATION_ERROR` | Eingabevalidierung fehlgeschlagen |
| 404 | `CASE_NOT_FOUND` | Fall existiert nicht |
| 500 | `DATABASE_ERROR` | Datenbankfehler (keine Details exponiert) |
| 500 | `INTERNAL_ERROR` | Unerwarteter Fehler (keine Details exponiert) |
