# Data Model — M1 Case Core

## Entity: Case

| Feld | Typ | Constraints |
|------|-----|-------------|
| case_id | UUID (String) | Primärschlüssel, serverseitig generiert, unveränderlich |
| title | String | 1–200 Zeichen, getrimmt, nicht leer |
| status | Enum: "open" | Nur "open" in M1 |
| created_at | ISO 8601 UTC | timezone-aware, automatisch gesetzt |
| updated_at | ISO 8601 UTC | timezone-aware, automatisch aktualisiert |

## SQLite Schema

```sql
CREATE TABLE IF NOT EXISTS cases (
    case_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status);
CREATE INDEX IF NOT EXISTS idx_cases_created_at ON cases(created_at);
```

## Invarianten

1. `case_id` wird serverseitig als UUIDv4 generiert
2. `title` wird vor Speicherung getrimmt und validiert
3. `status` ist bei Neuanlage immer "open"
4. `created_at` und `updated_at` sind immer UTC
5. `PRAGMA foreign_keys = ON` wird bei jeder Verbindung gesetzt
