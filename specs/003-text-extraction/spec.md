# Spec — M3 Dokumenttextgewinnung

## Feature
M3 — Dokumenttextgewinnung mit lokalem PDF-Text

## User Stories

### US1 — PDF-Text extrahieren (P1)
Als Nutzer möchte ich, dass hochgeladene PDFs automatisch auf Text durchsucht
werden, damit ich den Inhalt durchsuchen und später analysieren kann.

### US2 — Extrahierten Text abrufen (P1)
Als Nutzer möchte ich den extrahierten Text eines Dokuments über die API
abrufen können.

## Funktionale Anforderungen

| ID | Anforderung |
|----|-------------|
| FR-M3-01 | PDF-Text wird nach Upload automatisch extrahiert |
| FR-M3-02 | Extraktion erfolgt vollständig lokal (pymupdf) |
| FR-M3-03 | Text wird in der documents-Tabelle gespeichert |
| FR-M3-04 | Text kann über GET .../documents/{id}/text abgerufen werden |
| FR-M3-05 | PDFs ohne extrahierbaren Text liefern leeren String |
| FR-M3-06 | TextExtractor ist als Port (ABC) modelliert |
| FR-M3-07 | PdfTextExtractor ist die erste Implementierung |
| FR-M3-08 | OCR-Integration als späterer Adapter vorbereitet |
| FR-M3-09 | Keine Cloud-OCR, keine externen Dienste |

## Abgrenzung

Nicht in M3:
- OCR (kommt als optionaler Adapter in späterem Lauf)
- Volltextsuche über alle Dokumente
- Textanalyse oder -klassifikation (M4)
- Bild-OCR
