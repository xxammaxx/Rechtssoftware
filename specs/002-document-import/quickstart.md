# Quickstart — M2 Lokaler Dokumentimport und sichere Dateiverwaltung

## Voraussetzungen

- Python 3.11+
- Installierte Abhängigkeiten: `pip install -e ".[dev]"`
- App läuft: `.venv/Scripts/python.exe -m private_legal_navigator`
- Standard: http://127.0.0.1:8000

## 1. Tests ausführen

Alle M2-spezifischen Tests:

```powershell
# Unit-Tests (Domain + Service)
.venv/Scripts/python.exe -m pytest tests/unit/test_domain_document.py -v
.venv/Scripts/python.exe -m pytest tests/unit/test_document_service.py -v

# Integration-Tests (SQLite + FileStorage)
.venv/Scripts/python.exe -m pytest tests/integration/test_document_infrastructure.py -v

# API-Tests (Upload, List, Download)
.venv/Scripts/python.exe -m pytest tests/api/test_documents_api.py -v
```

Gesamte Test Suite inkl. Coverage:

```powershell
.venv/Scripts/python.exe -m pytest --cov=src/private_legal_navigator --cov-fail-under=90
```

## 2. Manueller Smoke-Test

### 2.1 App starten

```powershell
.venv/Scripts/python.exe -m private_legal_navigator
```

### 2.2 Fall anlegen

```powershell
$case = curl.exe -s -X POST http://127.0.0.1:8000/api/v1/cases `
  -H "Content-Type: application/json" `
  -d '{"title": "SYNTHETISCH – Testfall Dokumentimport"}'

$case_id = ($case | ConvertFrom-Json).case_id
Write-Output "Case ID: $case_id"
```

Erwartet: HTTP 201, JSON mit `case_id`, `title`, `status`, `created_at`, `updated_at`.

### 2.3 Synthetisches PDF erstellen

```powershell
# Minimales gültiges PDF (synthetisch, keine echten Daten)
$pdfContent = @"
%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
xref
0 4
...
trailer
<< /Size 4 /Root 1 0 R >>
startxref
...
%%EOF
"@

Set-Content -Path "test.pdf" -Value $pdfContent -NoNewline
```

Oder alternativ — falls ein echtes synthetisches PDF-Tool existiert, dort verwenden.

### 2.4 Dokument hochladen

```powershell
$upload = curl.exe -s -X POST "http://127.0.0.1:8000/api/v1/cases/$case_id/documents" `
  -F "file=@test.pdf;type=application/pdf"

$doc_id = ($upload | ConvertFrom-Json).document_id
Write-Output "Document ID: $doc_id"
```

Erwartet: HTTP 201, JSON mit `document_id`, `case_id`, `filename`, `mime_type`, `size_bytes`, `created_at`.

### 2.5 Dokumente auflisten

```powershell
curl.exe -s "http://127.0.0.1:8000/api/v1/cases/$case_id/documents"
```

Erwartet: HTTP 200, JSON mit `items`-Array (mindestens 1 Eintrag) und `count` ≥ 1.

### 2.6 Dokument herunterladen

```powershell
curl.exe -s -o "downloaded.pdf" `
  "http://127.0.0.1:8000/api/v1/cases/$case_id/documents/$doc_id"
```

Erwartet: HTTP 200, Content-Type: `application/pdf`, Datei `downloaded.pdf` ist lesbar.

### 2.7 Negative Tests

**Upload ohne PDF (falscher MIME-Type):**
```powershell
# Textdatei ohne PDF-Signatur
Set-Content -Path "test.txt" -Value "Das ist kein PDF" -NoNewline
curl.exe -s -X POST "http://127.0.0.1:8000/api/v1/cases/$case_id/documents" `
  -F "file=@test.txt;type=application/pdf"
```
Erwartet: HTTP 400, `INVALID_FILE_TYPE` oder `VALIDATION_ERROR`.

**Upload zu großes Dokument:**
```powershell
# 21 MB Dummy-Datei (überschreitet 20 MB Limit)
$fs = New-Object System.IO.FileStream "large.pdf", Create
$fs.SetLength(21MB)
$fs.Close()
curl.exe -s -X POST "http://127.0.0.1:8000/api/v1/cases/$case_id/documents" `
  -F "file=@large.pdf;type=application/pdf"
```
Erwartet: HTTP 413 (oder 400), `FILE_TOO_LARGE`.

**Download nicht-existierenden Dokuments:**
```powershell
curl.exe -s "http://127.0.0.1:8000/api/v1/cases/$case_id/documents/00000000-0000-0000-0000-000000000000"
```
Erwartet: HTTP 404, `DOCUMENT_NOT_FOUND`.

## 3. Erwartete Ergebnisse

| Test | Erwartetes Ergebnis |
|------|---------------------|
| Unit-Tests Domain | ✅ Alle grün |
| Unit-Tests Service | ✅ Alle grün |
| Integration-Tests Infrastructure | ✅ Alle grün |
| API-Tests | ✅ Alle grün |
| Upload PDF → 201 | ✅ Dokument-ID + Metadaten |
| Liste Dokumente → 200 | ✅ items + count |
| Download → 200 | ✅ PDF-Binärdaten |
| Upload Nicht-PDF → 4xx | ✅ Fehlercode |
| Upload > 20 MB → 4xx | ✅ Fehlercode |
| Unbekanntes Dokument → 404 | ✅ Fehlercode |

## Referenzen

- **Spec**: [spec.md](spec.md)
- **Datenmodell**: [data-model.md](data-model.md)
- **API-Contracts**: [contracts/api.md](contracts/api.md)
- **Plan**: [plan.md](plan.md)
- **Tasks**: [tasks.md](tasks.md)
