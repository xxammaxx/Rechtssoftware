# Data Model — M2 Document Import

## Entity: Document

| Feld | Typ | Constraints |
|------|-----|-------------|
| document_id | UUID | Primärschlüssel, serverseitig generiert |
| case_id | UUID | Fremdschlüssel → cases.case_id |
| filename | String | Originaldateiname (max 255 Zeichen) |
| mime_type | String | application/pdf (nur PDF in M2) |
| size_bytes | Integer | Dateigröße in Bytes (>0, ≤20MB) |
| storage_path | String | Relativer Pfad im Dokumentenverzeichnis |
| created_at | ISO 8601 UTC | timezone-aware |

## SQLite Schema

```sql
CREATE TABLE IF NOT EXISTS documents (
    document_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    storage_path TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (case_id) REFERENCES cases(case_id)
);

CREATE INDEX IF NOT EXISTS idx_documents_case_id ON documents(case_id);
```

## Dateisystem

```
PLN_DATA_DIR/
├── private_legal_navigator.db    (SQLite)
└── documents/
    ├── {uuid1}.bin                (gespeicherte Datei)
    └── {uuid2}.bin
```

- Dateiname im Dateisystem: `{document_id}.bin` (keine Originalnamen)
- Keine Verzeichnisstruktur basierend auf Nutzereingaben
- Keine Ausführungsbits
