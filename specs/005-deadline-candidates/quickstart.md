# Quickstart — M5 Deadline Candidate Extraction

> Kurze Validierungsanleitung. Ausführliche Spezifikation: `spec.md`.
> API-Contract: `contracts/api.md`. Datenmodell: `data-model.md`.

## Voraussetzungen

- Python 3.11+
- Virtuelle Umgebung eingerichtet (`.venv/`)
- Abhängigkeiten installiert: `pip install -e ".[dev]"`
- Anwendung läuft: `.venv/Scripts/python.exe -m private_legal_navigator`

Die M5-Erweiterung benötigt **keine neuen Abhängigkeiten** (nur Python-Standardbibliothek: `datetime`, `re`, `threading`, `dataclasses`, `enum`).

## Tests ausführen

### Alle M5-Tests + Regression

```powershell
.venv/Scripts/python.exe -m pytest --cov=src/private_legal_navigator --cov-fail-under=90 -v
```

### Nur M5-bezogene Tests

```powershell
.venv/Scripts/python.exe -m pytest tests/ -v -k "deadline"
```

### Qualitätsgates

```powershell
.venv/Scripts/python.exe -m ruff check src tests
.venv/Scripts/python.exe -m mypy src
```

## API-Validierungsszenarien

> Annahme: Anwendung läuft auf `http://127.0.0.1:8000`

### 1. Neuen Fall mit Dokument anlegen

```powershell
# Fall anlegen
$CASE = curl.exe -s -X POST http://127.0.0.1:8000/api/v1/cases `
  -H "Content-Type: application/json" `
  -d '{"title": "SYNTHETISCH – M5 Testfall", "description": "Test für Fristkandidaten"}'
$CASE_ID = ($CASE | ConvertFrom-Json).id
Write-Host "Case ID: $CASE_ID"

# PDF-Dokument mit Fristbezügen hochladen
$DOC = curl.exe -s -X POST "http://127.0.0.1:8000/api/v1/cases/$CASE_ID/documents" `
  -F "file=@specs/005-deadline-candidates/contracts/testdata/sample-deadline.pdf"
$DOC_ID = ($DOC | ConvertFrom-Json).id
Write-Host "Doc ID: $DOC_ID"
```

### 2. Fristkandidaten extrahieren (Erfolgsfall)

```powershell
$RESULT = curl.exe -s -X POST "http://127.0.0.1:8000/api/v1/cases/$CASE_ID/documents/$DOC_ID/deadline-candidates"
$RESULT | ConvertFrom-Json | ConvertTo-Json -Depth 3
```

**Erwartet:**
- `candidates` enthält erkannte Datums- und Fristangaben
- `warnings` enthält mindestens `LEGAL_CALCULATION_NOT_PERFORMED`
- `human_review_required` ist `true`

### 3. Leere Kandidatenliste (Text ohne Fristbezüge)

Bei einem Dokument ohne Datumsangaben ist eine leere `candidates`-Liste mit
`NO_DEADLINE_CANDIDATE`-Warning zu erwarten.

### 4. Text zu groß (Fehlerfall 413)

Bei einem Dokument mit >500.000 Zeichen extrahiertem Text ist HTTP 413
mit `TEXT_TOO_LARGE` zu erwarten.

### 5. Dokument nicht gefunden (Fehlerfall 404)

```powershell
curl.exe -s -X POST "http://127.0.0.1:8000/api/v1/cases/$CASE_ID/documents/00000000-0000-0000-0000-000000000000/deadline-candidates"
```

**Erwartet:** HTTP 404, `DOCUMENT_NOT_FOUND`

## Erwartetes Verhalten — Übersicht

| Szenario | HTTP | candidates | warnings |
|----------|------|------------|----------|
| Erfolg: Daten gefunden | 200 | ≥1 Kandidat | LEGAL_CALCULATION_NOT_PERFORMED + ggf. MULTIPLE / RELATIVE |
| Erfolg: keine Daten | 200 | [] | LEGAL_CALCULATION_NOT_PERFORMED + NO_DEADLINE_CANDIDATE |
| Text zu groß | 413 | — | TEXT_TOO_LARGE |
| Regex-Timeout (vollst. Abbruch) | 500 | — | EXTRACTION_TIMEOUT — keine Partialergebnisse |
| Doc nicht gefunden | 404 | — | DOCUMENT_NOT_FOUND |
| Case nicht gefunden | 404 | — | CASE_NOT_FOUND |

## Deterministische Reproduktion

Da die M5-Engine **rein deterministisch** ist (Regex, kein ML/Zufall):
- Gleicher Input → immer gleicher Output
- Keine Seiteneffekte, keine Persistenz
- Ergebnisse sind vollständig aus `Document.text_content` reproduzierbar

## Bekannte Einschränkungen

- Offsets beziehen sich auf extrahierten Text, nicht auf PDF-Seiten (siehe `data-model.md`)
- R5-Fristkontext-Präfix durchsucht max. 50 Zeichen rückwärts vom Match-Start
- Deduplizierung ist Containment-basiert (ein Kandidat umschließt den anderen vollständig)
- Bei Timeout vollständiger Abbruch (keine Partialergebnisse in candidates)
- Keine Feiertags-/Wochenendlogik (siehe `spec.md` — "Bewusst nicht unterstützte Fälle")
