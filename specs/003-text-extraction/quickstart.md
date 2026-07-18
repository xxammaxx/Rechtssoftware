# Quickstart — M3 Dokumenttextgewinnung

## Voraussetzungen

- Python 3.11+
- `.venv` mit installierten Abhängigkeiten (`pip install -e ".[dev]"`)
- pymupdf installiert (enthalten in `.[dev]`)

## Setup

```bash
# Arbeitsverzeichnis ist Repo-Root
cd C:\Rechtssoftware

# Sicherstellen, dass .venv aktiv ist
.venv/Scripts/python.exe -m pytest --version
```

## Tests ausführen

### Unit-Tests (Domain + Services)

```bash
.venv/Scripts/python.exe -m pytest tests/unit/ -v
```

Erwartet: 30+ Tests, alle grün.

Speziell für M3 relevante Tests:

```bash
# PdfTextExtractor — Textextraktion und Fehlerfälle
.venv/Scripts/python.exe -m pytest tests/unit/test_pdf_text_extractor.py -v

# DocumentService — Upload mit Textextraktion
.venv/Scripts/python.exe -m pytest tests/unit/test_document_service.py -v

# Document-Entity — extraction_error-Feld
.venv/Scripts/python.exe -m pytest tests/unit/test_domain_document.py -v
```

### Integration-Tests (SQLite-Repository)

```bash
.venv/Scripts/python.exe -m pytest tests/integration/ -v
```

Erwartet: Dokument-Repository speichert und lädt `extraction_error` korrekt.

### API-Tests (End-to-End über FastAPI/ASGI)

```bash
.venv/Scripts/python.exe -m pytest tests/api/test_documents_api.py -v
```

Erwartet:
- Upload eines PDFs → 201, Text-Endpunkt liefert `extraction_error: null`
- Text-Endpunkt für nicht-existierendes Dokument → 404

### Vollständige Testsuite + Coverage

```bash
.venv/Scripts/python.exe -m pytest --cov=src/private_legal_navigator --cov-fail-under=90
```

Erwartet: Coverage ≥ 90%, alle Tests grün.

## Validierungsszenarien

### Szenario 1: PDF mit Text hochladen und Text abrufen

```bash
# App starten
.venv/Scripts/python.exe -m private_legal_navigator &
```

```bash
# Fall anlegen
$caseId = Invoke-RestMethod -Uri http://127.0.0.1:8000/api/v1/cases -Method Post -Body '{"title":"SYNTHETISCH – Testfall"}' -ContentType "application/json"
Write-Output $caseId.case_id
```

```bash
# PDF mit Text hochladen
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/cases/$caseId/documents" `
  -Method Post -Form @{file = Get-Item -LiteralPath "tests/fixtures/sample.pdf"}
```

```bash
# Text abrufen
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/cases/$caseId/documents/$docId/text"
# Erwartet: text_content enthält Text, extraction_error ist null
```

### Szenario 2: Korrupte PDF — Upload gelingt, extraction_error gesetzt

```bash
# Beliebiges Binärfile als PDF hochladen
$bytes = [byte[]]::new(100)
$caseId = "<case_id>"
$resp = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/cases/$caseId/documents" `
  -Method Post -Form @{file = @{name="corrupt.pdf"; content=[byte[]]::new(100)}}
Write-Output $resp.document_id
```

```bash
# Text-Endpunkt zeigt Fehler
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/cases/$caseId/documents/$docId/text"
# Erwartet: text_content == "", extraction_error enthält Fehlermeldung
```

### Szenario 3: Dokumentenliste enthält kein extraction_error

```bash
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/cases/$caseId/documents"
# Erwartet: Response enthält kein extraction_error-Feld
```

## Datenmodell-Prüfung

```bash
# Direkte SQLite-Abfrage
sqlite3 ~/.private-legal-navigator/pln.db "SELECT document_id, text_content, extraction_error FROM documents;"
```

Erwartet: `extraction_error` ist NULL bei erfolgreicher Extraktion, enthält Fehlertext bei Fehlschlag.

## Grenzen / Bekannte Einschränkungen

- OCR wird nicht unterstützt (gescannte PDFs ohne Textlayer → `text_content = ""`)
- App muss aktiv sein (kein Hintergrunddienst)
- Nur PDFs (keine anderen Formate)
- Extraktion erfolgt synchron — große PDFs blockieren den Request
