# Local-only Architecture

## Produktvertrag

**Der Bescheid verlässt das Gerät nicht.**

BescheidPilot verarbeitet Bescheide vollständig lokal auf dem Gerät. Es werden keine Bescheide, Bilder, OCR-Texte, Fristen, Zusammenfassungen oder Antwortentwürfe an Server, Cloud-KI-Dienste, Telemetrie-Systeme oder externe APIs hochgeladen.

Der aktuelle Nachweisstatus wird auf der Evidence-Seite dokumentiert.

## Zielarchitektur

```text
Lokale UI
  -> lokale Dokument-/Texterfassung
  -> lokale OCR (später)
  -> lokale Extraktion
  -> lokale Evidence-Zuordnung
  -> lokale Entwurfserzeugung
  -> Human Review
  -> expliziter lokaler Export
```

Vorgesehene technische Bausteine:

- Flutter für die lokale App
- Rust für deterministische lokale Kernlogik
- SQLite/SQLCipher erst nach eigenem Storage- und Threat-Model-Review
- lokale OCR erst nach Offline- und Datenflussnachweis
- lokale SLM/LLM-Integration erst nach Dependency-, Modell- und Ressourcenprüfung
- statische GitHub-Pages-Seite ohne Nutzerdokumente, Tracker oder App-Backend

## Verbotene Datenflüsse

- Dokument -> Upload/API
- Bild -> Cloud-OCR
- OCR-Text -> Remote-LLM
- Extraktion/Frist/Entwurf -> Telemetrie oder Crash-Reporting
- lokaler Fehler -> Remote-Fallback
- Entwurf -> automatische Behördenkommunikation

## Zulässige Netzwerkaktivität

Die produktive Dokumentverarbeitung benötigt keine Netzwerkaktivität. Repository-CI und die öffentliche statische Website dürfen GitHub-Infrastruktur verwenden, verarbeiten aber keine Bescheide oder abgeleitete sensible Nutzerdaten.

## Implementierter Network-Deny-Harness

Issue #11 ergänzt einen minimalen, ausführbaren Textanalysepfad:

```text
synthetischer lokaler Text
  -> src/core/local_analysis.py
  -> ausschließlich strukturelle Zählwerte
  -> kein I/O, kein Logging, kein Netzwerk
```

`src/core/network_guard.py` sperrt im Testkontext Socket-Erzeugung,
Verbindungsaufbau, DNS-Auflösung, `urllib` sowie Standardbibliothek-HTTP und
-HTTPS. `scripts/guardrail_check.py` behandelt bekannte Netzwerk-, Upload-,
Provider-, Cloud- und Telemetriemuster in Produktcode als blockierende Funde.

Nachweis:

```bash
python scripts/guardrail_check.py
python -m unittest discover -s tests -p "test_*.py" -v
```

Der Harness ist eine Testkontrolle und keine Betriebssystem-Sandbox.

## Implementierter Offline-Mode-Reality-Test

Issue #12 ergänzt den initialen Offline-Nachweis für denselben lokalen
Textanalysepfad. Der Test entfernt bekannte API-Key- und
Remote-Endpunkt-Variablen, sperrt Netzwerkzugriffe und führt die Analyse
erfolgreich aus.

Der Result-Contract enthält:

```text
execution_mode = offline
network_required = false
```

Zusätzliche negative Fixtures blockieren Produktcode, der Remote-Credentials
liest oder Internet, Netzwerk, Cloud beziehungsweise API-Keys als Voraussetzung
deklariert.

Dieser Nachweis gilt nur für den strukturellen Python-Harness. Er beweist noch
nicht den Offline-Betrieb des vollständigen Produkts.

## Implementierter No-Remote-LLM-Guardrail

Issue #13 ergänzt den initialen No-Remote-LLM-Nachweis für denselben lokalen
Textanalysepfad. Der Test beweist:

- Lokale Analyse benötigt keine Remote-LLM-API-Keys
- Remote-LLM-Provider-Fixtures werden vom statischen Scan blockiert
- Remote-Fallback-Konfigurationen werden als blockierende Funde erkannt
- Produktcode enthält keine aktiven Remote-LLM-SDK-Imports
- Sensible Bescheidtexte werden nicht an Remote-Provider-Funktionen übergeben

Der erweiterte `scripts/guardrail_check.py` deckt jetzt Provider wie
`cohere`, `perplexity`, `together`, `huggingface_hub` sowie API-Keys wie
`COHERE_API_KEY`, `HF_TOKEN`, `AZURE_OPENAI_API_KEY`, `BEDROCK_API_KEY`
und generische `LLM_API_KEY`/`LLM_BASE_URL` ab.

Der `Local AI Contract` (`docs/LOCAL_AI_CONTRACT.md`) dokumentiert erlaubte
und verbotene KI-Nutzung.

Dieser Nachweis gilt nur für den strukturellen Python-Harness. Ein
vollständiger Produkt-Golden-Path mit lokaler KI existiert noch nicht.

## Implementierter No-Cloud-OCR-Guardrail

Issue #14 ergänzt den initialen No-Cloud-OCR-Nachweis für denselben lokalen
Textanalysepfad. Der Test beweist:

- Lokale Analyse benötigt keine Cloud-OCR-API-Keys
- Cloud-OCR-Provider-Fixtures werden vom statischen Scan blockiert
- Cloud-OCR-Fallback-Konfigurationen werden als blockierende Funde erkannt
- Dokument-Upload-Funktionen werden im Produktcode blockiert
- Produktcode enthält keine aktiven Cloud-OCR-SDK-Imports
- Sensible OCR-Texte werden nicht an Remote-OCR-Funktionen übergeben

Der erweiterte `scripts/guardrail_check.py` deckt jetzt Cloud-OCR-Anbieter wie
Google Cloud Vision, Azure Form Recognizer, AWS Textract, OCR.space und ABBYY
sowie deren API-Keys und Dokument-Upload-Muster ab.

Der `Local OCR Contract` (`docs/LOCAL_OCR_CONTRACT.md`) dokumentiert erlaubte
und verbotene OCR-Nutzung.

Dieser Nachweis gilt nur für den strukturellen Python-Harness. Ein
vollständiges lokales OCR-Modul existiert noch nicht.

## Implementierter No-Sensitive-Logs-Guardrail

Issue #15 ergänzt den initialen No-Sensitive-Logs-Nachweis. Der Guardrail
umfasst:

- `src/core/redaction.py`: Regex-basierte Redaction fuer 13+ Muster
  (Email, Telefon, IBAN, Aktenzeichen, BG-Nummer, Adresse, Name,
  Geburtsdatum, Fristen, etc.)
- Sensitive-Log-Blockierung im statischen Scan (`sensitive_log_risks`)
- Erkennung von `print()`, `logging.*`, `console.*` mit sensiblen
  Variablennamen
- Exception-Redaction und Website-Daten-Prüfung

Dieser Nachweis gilt nur für den strukturellen Python-Harness. Ein
vollständiger Produkt-Golden-Path mit Logging existiert noch nicht.

## Aktueller Status

**YELLOW:** Vertrag und Architekturgrenzen sind dokumentiert. Der initiale
Network-Deny-Harness ist mit positiver Offline-Fixture und negativen
Netzwerk-Fixtures belegt. Der Offline-Mode-Reality-Test benötigt keine API-Keys
oder Remote-Konfiguration. Beide Harness-Nachweise sind `GREEN_PARTIAL`. Eine
produktive App und ein echter Golden Path existieren noch nicht; OCR-, Storage-,
Export-, Dependency- und Sensitive-Log-Gates bleiben offen.
