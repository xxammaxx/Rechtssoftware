# Research — M2 Lokaler Dokumentimport und sichere Dateiverwaltung

## Übersicht

Dieses Dokument fasst die technischen Recherchen und Entscheidungen für die
M2-Implementierung zusammen. Alle Klärungen wurden in der `/speckit.clarify`-Session
(2026-07-18) getroffen.

## Entscheidungen

### 1. MIME-Type-Validierung

| Aspekt | Wert |
|--------|------|
| **Decision** | Magic-Bytes-Header-Prüfung (reines Python) |
| **Rationale** | Prüfung der ersten 5 Bytes auf `%PDF`-Signatur. Keine native Systembibliothek (libmagic) erforderlich. Vollständig portabel. |
| **Alternatives considered** | python-magic (libmagic-Bindings) — verifiziert genauer, erfordert aber native DLL unter Windows (`python-magic-bin`); Content-Type-Header allein — trivial zu umgehen |
| **Referenz** | FR-M2-003, specs/002-document-import/spec.md |

### 2. Failure Atomicity (Upload)

| Aspekt | Wert |
|--------|------|
| **Decision** | File-first mit kompensierendem Delete |
| **Rationale** | Datei zuerst auf Disk schreiben, dann DB-Insert. Schlägt der DB-Insert fehl, wird die Datei gelöscht und ein Fehler zurückgegeben. Minimiert Risiko von Orphan-Files. |
| **Alternatives considered** | DB-first (DB-Rollback bei File-Fehler); Two-Phase-Commit (Overkill für SQLite); keine Behandlung (akzeptiert Orphan-Risiko) |
| **Referenz** | FR-M2-016 |

### 3. Logging-Strategie

| Aspekt | Wert |
|--------|------|
| **Decision** | Metadata-only Logging |
| **Rationale** | Logging von Operationstyp, document_id, case_id, HTTP-Status, Dauer. Keine Dateinamen, Pfade oder personenbezogene Daten. Erfüllt Constitution §1 (Local-only) und §2 (Privacy by Design). |
| **Alternatives considered** | Minimal (nur Status, keine IDs — schwer debuggbar); Full Audit (alle Felder — Datenschutzbedenken); Kein App-Logging (reine Uvicorn-Logs — zu wenig Kontext) |
| **Referenz** | FR-M2-017 |

### 4. Paginierung (List-Endpunkt)

| Aspekt | Wert |
|--------|------|
| **Decision** | Keine Paginierung — alle Dokumente auf einmal |
| **Rationale** | Single-User-Lokal-Anwendung mit erwartet niedriger Dokumentenzahl pro Fall. Das `items`/`count`-Envelope-Design erlaubt nachträgliche, nicht-breaking Erweiterung um Paginierung. |
| **Alternatives considered** | Vollständige Paginierung (offset/limit) — Zukunftssicher, aber derzeit kein Bedarf |
| **Referenz** | FR-M2-018 |

### 5. Technologie-Erweiterungen

| Aspekt | Wert |
|--------|------|
| **Decision** | Bestehender Stack (FastAPI, sqlite3, Pydantic, pytest) ohne neue Abhängigkeiten |
| **Rationale** | MIME-Prüfung via Magic Bytes benötigt keine zusätzlichen Bibliotheken. Dateispeicher via `pathlib` (stdlib). Alle Anforderungen mit stdlib + bestehenden Dependencies umsetzbar. |
| **Alternatives considered** | python-magic, aiofiles (für async file I/O — nicht nötig bei Uvicorn Single-Worker) |
| **Referenz** | specs/002-document-import/plan.md (Technical Context) |

## Best Practices

### PDF-Magic-Bytes

Ein gültiges PDF beginnt mit `%PDF` (Position 0–3, Hex: `25 50 44 46`).
Zusätzliche Prüfung: Position 5–7 kann der Versionstring folgen (z. B. `1.4`).
Für M2 reicht die Prüfung der ersten 5 Bytes (`%PDF-` oder `%PDF\n` etc.).

### Sicherer Dateiupload

- UUID-basierte Dateinamen verhindern Path Traversal (siehe `LocalFileStorage._resolve()`)
- `Path(storage_path).name` extrahiert nur den Dateinamen (keine Verzeichnisse)
- Dateien werden im `documents/`-Unterverzeichnis von `PLN_DATA_DIR` gespeichert
- Keine Ausführungsbits (Windows: nicht zutreffend; POSIX: `os.chmod` auf 0o644)

### Dateigrößenlimitierung

- 20 MB Limit (20 × 1024 × 1024 = 20971520 Bytes)
- Prüfung auf Domain-Ebene (`Document._validate_size`)
- Prüfung auf API-Ebene (FastAPI `UploadFile` liest vollständig — bei sehr großen Dateien Streaming in Erwägung ziehen)

## Offene Punkte

Keine — alle technischen Entscheidungen für M2 sind getroffen.
