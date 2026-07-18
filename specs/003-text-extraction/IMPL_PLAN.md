# Implementation Plan — M3 Dokumenttextgewinnung

## Technical Context

| Attribut | Wert |
|----------|------|
| **Feature** | M3 — Dokumenttextgewinnung mit lokalem PDF-Text |
| **Risk Tier** | LOW_LOCAL |
| **Feature Dir** | `specs/003-text-extraction/` |
| **Branch** | `main` (kein separater Feature-Branch) |
| **Abhängigkeiten** | pymupdf (bereits in `pyproject.toml`) |
| **Bestehende Assets** | Document-Entity, TextExtractor-Port, PdfTextExtractor-Adapter, DocumentService, SqliteDocumentRepository, API-Routen, Pydantic-Schemas |

### Unbekannte / NEEDS CLARIFICATION

1. **pymupdf-Exception-Typen**: Welche Exceptions wirft `pymupdf.open()` bei korrupten vs. verschlüsselten PDFs? Benötigt für differenzierte Fehlermeldungen in `extraction_error`.
2. **Migrationsstrategie**: Wie wird `extraction_error`-Spalte in bestehende SQLite-Datenbanken eingefügt? Bestehende Zeilen sollen `extraction_error = NULL` erhalten.

---

## Constitution Check

| # | Prinzip | Relevanz | Status |
|---|---------|----------|--------|
| 1 | Local-only als Standard | pymupdf ist rein lokal | ✅ Erfüllt |
| 2 | Privacy by Design | Keine PII in extraction_error-Logs | ✅ Erfüllt (Fehlermeldungen enthalten keine Dokumentinhalte) |
| 3 | Keine automatische Rechtsentscheidung | N/A | ✅ Nicht betroffen |
| 4 | Human Review | N/A (reine Textextraktion) | ✅ Nicht betroffen |
| 5 | Modulare Architektur | API → Application → Domain → Infrastructure | ✅ Wird eingehalten |
| 6 | Kleine vertikale Slices | Ein vollständiger Pfad von API bis Persistenz | ✅ Genau dies |
| 7 | Red Tests vor Implementierung | Tests schreiben vor Code-Änderungen | ⚠️ Red Tests müssen existieren |
| 8 | Lokale Gates als Primärwahrheit | Tests lokal ausführbar | ✅ Erfüllt |
| 9 | Keine Remote-CI | kein GitHub Actions | ✅ Erfüllt |
| 10 | Evidence vor Erfolgsmeldung | Tests + Coverage | ⚠️ Zu beachten |
| 11 | Dokumentation als Living Truth Mirror | Datenmodell, Contracts, Quickstart | ⚠️ Wird aktualisiert |
| 12 | Synthetische Testdaten | Test-PDFs mit "SYNTHETISCH" | ✅ Bereits erfüllt |

**Gate**: Alle Constitution-Verletzungen müssen vor Phase 1 begründet ausgenommen sein.

---

## Gates

| Gate | Bedingung | Status |
|------|-----------|--------|
| G1 | Alle bestehenden Tests passieren (vor Änderungen) | ⏳ Vor Implementierung prüfen |
| G2 | Keine neuen externen Abhängigkeiten | ✅ pymupdf bereits vorhanden |
| G3 | Keine Cloud/Remote-APIs | ✅ pymupdf lokal |
| G4 | Dokumentation wird aktualisiert (data-model, contracts, quickstart) | ⏳ Phase 1 |
| G5 | Red Tests existieren vor Implementierung | ⏳ Phase 0 |
| G6 | extraction_error-Feld enthält keine Dokumentinhalte (kein PII-Leak) | ⚠️ Zu validieren |

---

## Phasen

### Phase 0: Research

**Ziel**: Alle NEEDS CLARIFICATION in `research.md` auflösen.

Forschungsthemen:
1. pymupdf-Exception-Typen bei korrupten/verschlüsselten PDFs
2. SQLite ALTER TABLE ADD COLUMN Verhalten (rückwärtskompatibel)
3. Bestehende Tests analysieren (welche müssen angepasst werden)

**Output**: `research.md`

### Phase 1: Design & Contracts

**Ziel**: Vollständige Designspezifikation.

Schritte:
1. Datenmodell aktualisieren (`data-model.md`) — bereits aus Clarification
2. API-Contracts für M3 erstellen (`contracts/api.md`)
3. Quickstart-Validierungsguide (`quickstart.md`)
4. Constitution Re-evaluation post-design

**Output**: 
- `data-model.md` (aktualisiert)
- `contracts/api.md`
- `quickstart.md`

### Phase 2: Tasks (später)

**Ziel**: Task-Breakdown für Implementierung.
