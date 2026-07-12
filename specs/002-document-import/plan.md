# Plan — M2 Lokaler Dokumentimport und sichere Dateiverwaltung

## Ziel

Erweiterung des Backends um einen Dokument-Upload-Endpunkt mit sicherer
lokaler Dateiablage. Dokumente werden Fällen zugeordnet und können über
die API abgerufen werden.

## Architekturansatz

Erweiterung des modularen Monolithen um eine File-Storage-Abstraktion:

```
API: POST /api/v1/cases/{case_id}/documents (Upload)
     GET  /api/v1/cases/{case_id}/documents (Liste)
     GET  /api/v1/cases/{case_id}/documents/{doc_id} (Download)

Application: DocumentService
             FileStorage-Port (ABC)
             DocumentRepository-Port (ABC)

Domain: Document-Entity

Infrastructure: LocalFileStorage (Dateisystem)
                SqliteDocumentRepository
```

## Datenhaltung

- **Metadaten**: SQLite `documents`-Tabelle (document_id, case_id, filename, mime_type, size_bytes, storage_path, created_at)
- **Dateien**: Dateisystem unter `PLN_DATA_DIR/documents/{uuid}.bin`
- Keine Binärdaten in der Datenbank

## Sicherheit

- Nur PDF-MIME-Types (`application/pdf`) akzeptiert
- Maximale Dateigröße: 20 MB (20971520 Bytes)
- UUID-basierte Speicherpfade (kein Path Traversal)
- Keine Ausführung von Uploads
- MIME-Type-Prüfung via python-magic oder file header
- Uploads nur für existierende Cases

## Projektstruktur (neu)

```
src/private_legal_navigator/
├── domain/
│   └── document.py              → NEU: Document-Entity
├── application/
│   ├── document_repository.py   → NEU: DocumentRepository-Port
│   ├── file_storage.py          → NEU: FileStorage-Port
│   └── document_service.py      → NEU: DocumentService
├── infrastructure/
│   ├── local_file_storage.py    → NEU: FileStorage-Impl
│   └── sqlite_document_repository.py → NEU: DocumentRepository-Impl
└── api/
    └── document_routes.py       → NEU: Upload/Download-Routen
```
