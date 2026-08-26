# Local OCR Contract

BescheidPilot darf sensible Bescheide, Bilder, PDFs und OCR-Texte nur lokal
verarbeiten.

## Erlaubt

- lokale OCR (z.B. Tesseract, lokale Modelle)
- lokale Textextraktion aus PDFs
- lokale Bildvorverarbeitung
- lokale PDF-Text-Extraktion
- lokale Heuristiken
- lokale Modelle
- manuelle Texteingabe als MVP-Fallback

## Verboten

- Cloud-OCR (Google Cloud Vision, Azure Computer Vision, AWS Textract, etc.)
- Remote-OCR-Fallbacks
- Upload von Bildern an externe Dienste
- Upload von PDFs an externe Dienste
- Upload von OCR-Text an externe Dienste
- API-Key-Pflicht fuer OCR im Kernworkflow
- externe Trainingsnutzung mit Bescheiddaten
- automatische Uebertragung von Dokumenten

## Nachweisbare Cloud-OCR-Denylist

Folgende Anbieter und Dienste duerfen im Produktcode nicht aktiv referenziert
werden:

- Google Cloud Vision (`google.cloud.vision`)
- Google Document AI (`google.cloud.documentai`)
- Azure Computer Vision (`azure.cognitiveservices.vision`)
- Azure Form Recognizer (`azure.ai.formrecognizer`)
- Azure Document Intelligence (`azure.ai.documentintelligence`)
- AWS Textract (`boto3.client("textract")`)
- OCR.space API (`api.ocr.space`)
- ABBYY Cloud OCR
- Adobe PDF Services

## Nachweisbare API-Key-Denylist

Folgende Umgebungsvariablen duerfen im Produktcode nicht abgefragt werden:

- `GOOGLE_APPLICATION_CREDENTIALS`
- `GOOGLE_CLOUD_PROJECT`
- `AZURE_COGNITIVE_SERVICES_KEY`
- `AZURE_FORM_RECOGNIZER_KEY`
- `AZURE_DOCUMENT_INTELLIGENCE_KEY`
- `AZURE_COMPUTER_VISION_KEY`
- `OCR_SPACE_API_KEY`
- `ABBYY_API_KEY`
- `ADOBE_CLIENT_ID` / `ADOBE_CLIENT_SECRET`
- `OCR_API_KEY`
- `OCR_BASE_URL`
- `REMOTE_OCR_URL`
- `CLOUD_OCR_URL`

## Nachweisbare Code-Muster-Denylist

Folgende Muster im Produktcode sind blockierend:

- `ImageAnnotatorClient`, `DocumentProcessorServiceClient`
- `DocumentAnalysisClient`, `ComputerVisionClient`
- `boto3.client("textract")`
- `upload_document()`, `upload_image()`, `upload_pdf()`
- `multipart/form-data` Content-Type
- Dokument-Upload via `requests.post(...files=...)`

## Enforcement

- `scripts/guardrail_check.py` — statischer Produktcode-Scan mit `cloud_ocr_risks`
- `tests/test_no_cloud_ocr.py` — dynamische Guardrail-Tests
- `tests/test_network_deny.py` — Network-Deny fuer Upload-Pfade
- GitHub Actions: `.github/workflows/local-only-guardrails.yml`

## Status

Aktuell ist nur der Guardrail-Harness nachgewiesen. Ein vollstaendiges lokales
OCR-Modul ist noch nicht implementiert.

Der No-Cloud-OCR-Guardrail ist `GREEN_PARTIAL` fuer den aktuellen
Python-Harness. Der Local-only-Gesamtstatus bleibt `YELLOW`.

*Zuletzt aktualisiert: 2026-06-06*
