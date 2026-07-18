# Research — M3 Dokumenttextgewinnung

## 1. pymupdf Exception Handling

### Untersuchung
pymupdf `open()` wirft bei fehlerhaften PDFs spezifische Exceptions:

| Szenario | Exception | MRO |
|----------|-----------|-----|
| Korrupte PDF (kein gültiges PDF) | `pymupdf.FileDataError("Failed to open stream")` | FileDataError → RuntimeError → Exception |
| Leere Bytes | `pymupdf.EmptyFileError("Cannot open empty stream.")` | EmptyFileError → FileDataError → RuntimeError → Exception |
| Verschlüsselte PDF | `pymupdf.FileDataError("Failed to open stream")` | (gleiche Klasse wie korrupte PDF) |

**Entscheidung:** `EmptyFileError` ist eine Subklasse von `FileDataError`. Ein Catch von `FileDataError` deckt alle drei Fälle ab. Ein separater Catch für `EmptyFileError` vor `FileDataError` erlaubt differenzierte Fehlermeldungen.

### Konsequenz für PdfTextExtractor
- Aktuelle Implementierung fängt `Exception` und gibt `""` zurück → **entspricht Option B** (Fehler versteckt)
- Neue Implementierung muss unterscheiden:
  - `FileDataError` (korrupt/verschlüsselt) → `ExtractionResult(text="", error="...")`
  - `Exception` (unerwartet) → `ExtractionResult(text="", error="...")`
  - Erfolg → `ExtractionResult(text="...", error=None)`

---

## 2. SQLite ALTER TABLE Migration

### Untersuchung
SQLite unterstützt `ALTER TABLE ... ADD COLUMN` mit folgenden Eigenschaften:
- Neue Spalte wird am Ende hinzugefügt
- `DEFAULT NULL` erlaubt — bestehende Zeilen erhalten automatisch NULL
- Voll rückwärtskompatibel — bestehende Queries ohne die Spalte funktionieren weiterhin
- `ALTER TABLE` kann in Transaktion ausgeführt werden
- Schema-Initialisierung ist idempotent mit `CREATE TABLE IF NOT EXISTS`

### Konsequenz
- `extraction_error TEXT DEFAULT NULL` kann mittels `ALTER TABLE` ergänzt werden
- Oder: Schema-Upgrade-Skript prüft auf Existenz der Spalte vor ALTER
- Bestehende Dokumente erhalten `extraction_error = NULL` (kein Fehler)

---

## 3. Analyse bestehender Tests

### Aktuelle Testabdeckung (70 Tests, alle grün)
| Test-Datei | Tests | Relevanz für M3 |
|------------|-------|-----------------|
| `test_pdf_text_extractor.py` | 3 | **Muss angepasst werden**: `extract()` wird Rückgabetyp ändern (ExtractionResult statt str) |
| `test_document_service.py` | 6 | **Muss angepasst werden**: Mock-Rückgabewerte für extract() ändern |
| `test_documents_api.py` | 9 | **Muss ergänzt werden**: extraction_error-Feld im Text-Response testen |
| `test_domain_document.py` | 8 | **Muss ergänzt werden**: extraction_error-Feld in Document-Konstruktor testen |
| `test_sqlite_repository.py` | 5 | **Keine Änderung**: extraction_error wird per ALTER TABLE ergänzt |
| `test_case_service.py` | 6 | **Keine Änderung** |
| `test_domain_case.py` | 10 | **Keine Änderung** |
| `test_cases_api.py` | 10 | **Keine Änderung** |
| `test_document_infrastructure.py` | 5 | **Keine Änderung** |

### Anzupassende Tests (18 betroffen)
1. `PdfTextExtractor` — Rückgabetyp ändert sich von `str` zu `ExtractionResult`
2. `DocumentService` — Mock muss ExtractionResult zurückgeben
3. `Document` — Konstruktor um `extraction_error` ergänzen
4. `DocumentTextResponse` — um `extraction_error` ergänzen
5. API-Integrationstests — extraction_error im Response validieren

---

## Entscheidungslog

| Entscheidung | Rationale | Alternativen |
|-------------|-----------|-------------|
| `TextExtractor.extract()` gibt `ExtractionResult` zurück statt `str` | Erlaubt structured result mit Fehlerinformation, ohne Exception-Flow für Erwartete Fehler | Exception werfen (wäre kein "expected" error für korrupte PDFs) |
| `ExtractionResult` als Named Tuple `(text: str, error: str \| None)` | Minimaler Footprint, immutable, typing-kompatibel | Dataclass, eigener Typ |
| Catch-Reihenfolge: `EmptyFileError` → `FileDataError` → `Exception` | Differenzierte Fehlermeldungen | Nur `Exception` (verliert Information) |
| `extraction_error` als `TEXT DEFAULT NULL` in SQLite | Rückwärtskompatibel, keine Datenmigration nötig | Separates Error-Log (Overengineered für M3) |
