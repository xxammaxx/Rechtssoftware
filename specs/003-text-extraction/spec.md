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
| FR-M3-01 | PDF-Text wird während des Uploads **nach** erfolgreicher Dateipersistierung synchron extrahiert. Der Upload schlägt nicht fehl, wenn die Extraktion fehlschlägt. |
| FR-M3-02 | Extraktion erfolgt vollständig lokal (pymupdf) |
| FR-M3-03 | Text wird in der documents-Tabelle gespeichert |
| FR-M3-04 | Text kann über GET .../documents/{id}/text abgerufen werden |
| FR-M3-05 | PDFs ohne extrahierbaren Text (erfolgreich geparst, aber kein Textlayer) liefern leeren String — kein `extraction_error` |
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

## Edge Cases / Fehlerbehandlung

| ID | Anforderung |
|----|-------------|
| EC-M3-01a | Bei korrupten PDFs (ungültiges Format) schlägt die Extraktion fehl — extraction_error: "PDF ist korrupt" |
| EC-M3-01b | Bei verschlüsselten/passwortgeschützten PDFs schlägt die Extraktion fehl — extraction_error: "PDF ist verschlüsselt" |
| EC-M3-01c | Bei leeren Dateien (0 Bytes) schlägt die Extraktion fehl — extraction_error: "Datei ist leer". Der Upload wird bereits durch die bestehende Validierung (size_bytes > 0) abgelehnt, bevor die Extraktion startet. |
| EC-M3-02 | Der Upload selbst wird dadurch **nicht** abgelehnt — das Dokument wird mit leerem `text_content` und einem `extraction_error`-Feld gespeichert |
| EC-M3-03 | `extraction_error` ist ein optionales String-Feld (null bei erfolgreicher Extraktion). Format: Kurze, beschreibende Fehlermeldung auf Deutsch, maximal 200 Zeichen, kein Zeilenumbruch. Keine Dokumentinhalte oder PII (siehe EC-M3-04). |
| EC-M3-04 | Fehler werden serverseitig geloggt (logging.ERROR) über den Modul-Logger (`logging.getLogger(__name__)`). `extraction_error`-Meldungen und Log-Einträge dürfen **keine Dokumentinhalte oder personenbezogenen Daten** enthalten (Privacy by Design, Constitution §2) |
| EC-M3-05 | PDFs ohne Textlayer (z. B. gescannte Dokumente) gelten als erfolgreich extrahiert mit leerem Text — kein `extraction_error` |

## Weitere Annahmen

- **Unicode/Zeichenkodierung**: pymupdf extrahiert Text mit nativer Unicode-Unterstützung. Deutsche Umlaute (ä, ö, ü, ß) und andere UTF-8-Zeichen werden ohne Einschränkung unterstützt. Keine separate Anforderung erforderlich.
- **Große PDFs (nahe 20 MB)**: Die Extraktion erfolgt synchron — bei großen PDFs kann der Request entsprechend länger dauern. Es gibt kein separates Timeout für die Extraktion. Das bestehende Upload-Limit von 20 MB gilt (siehe Document.MAX_SIZE_BYTES).
- **Erneuter Upload**: Jeder Upload erzeugt ein neues Dokument. Die Textextraktion läuft bei jedem Upload erneut. Ein erneuter Upload eines Dokuments mit fehlgeschlagener Extraktion führt zu einer neuen Extraktion.
- **Gemischte Inhalte (Seiten mit/ohne Text)**: pymupdf extrahiert Text seitenweise. Seiten ohne Textlayer liefern leeren String; Seiten mit Text werden normal extrahiert. Das Gesamtergebnis ist die Verkettung aller Seiten — keine gesonderte Behandlung nötig.
- **Performance**: Es gelten keine spezifischen Performance-Erwartungen für die Textextraktion. Die synchrone Extraktion innerhalb des HTTP-Requests wird als akzeptabel vorausgesetzt (LOW_LOCAL, Einzelplatzanwendung).
- **pymupdf-Version**: Die Abhängigkeit ist in `pyproject.toml` spezifiziert. Die aktuelle zum Zeitpunkt der Implementierung verfügbare Version wird verwendet.
- **Upload-Limit**: Das bestehende 20-MB-Limit aus Document.MAX_SIZE_BYTES gilt. PDFs über 20 MB werden vor der Extraktion abgelehnt.
- **Abhängigkeitsausfall**: Sollte pymupdf durch ein Update nicht mehr kompatibel sein, wird die Extraktion mit einem `Exception`-Catch abgefangen und als `extraction_error` gemeldet. Eine Versionsfixierung in `pyproject.toml` verhindert unerwartete Updates.

## Clarifications

### Session 2026-07-18

- Q: When pymupdf fails to extract text (corrupted PDF, encrypted, internal error), what should the upload endpoint do? → A: Upload succeeds, error recorded (Option C). Dokument wird gespeichert, `text_content` ist leer, ein optionales `extraction_error`-Feld beschreibt den Fehler. Fehler werden zusätzlich serverseitig geloggt.
- Q: Should `extraction_error` messages and log entries be constrained to exclude document content/PII? → A: Yes — explicit constraint added to EC-M3-04: `extraction_error`-Meldungen und Log-Einträge dürfen keine Dokumentinhalte oder personenbezogenen Daten enthalten (Privacy by Design, Constitution §2)
