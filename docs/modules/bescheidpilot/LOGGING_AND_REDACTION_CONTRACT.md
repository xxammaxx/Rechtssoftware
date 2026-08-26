# Logging and Redaction Contract

BescheidPilot darf keine sensiblen Bescheiddaten in Logs, Debug-Ausgaben,
Fehlerberichte oder Telemetrie schreiben.

## Verboten

- vollstaendige Bescheidtexte
- OCR-Rohtexte
- Antwortentwuerfe
- Namen
- Adressen
- Geburtsdaten
- Aktenzeichen
- Kundennummern
- BG-Nummern
- Telefonnummern
- E-Mail-Adressen
- IBANs
- Fristen mit Personenbezug

## Erlaubt

- technische Statusmeldungen
- Teststatus
- anonyme Zaehler
- Fehlercodes
- redigierte Ausgaben (via `src/core/redaction.py`)
- synthetische Testdaten, wenn klar als Fixture markiert

## Pflicht

- Redaction vor Ausgabe (`redact_sensitive_text()`)
- keine Rohtexte in Exceptions
- keine sensiblen Daten in CI-Logs
- keine sensiblen Daten in Website-Daten
- keine Telemetrie mit personenbezogenen Daten

## Redaction-Modul

`src/core/redaction.py` bietet:

- `redact_sensitive_text(text)` — regex-basierte Redaction
- `contains_sensitive_pattern(text)` — Sensitive-Pattern-Detektion
- `safe_log(text)` — log-sichere Ausgabe

Erkannte Muster:
Email, Telefon, IBAN, Aktenzeichen, BG-Nummer,
SV-Nummer, Adresse, PLZ+Ort, Geburtsdatum, Name (mit Anrede),
Fristangaben, Bescheidmarker

## Enforcement

- `scripts/guardrail_check.py` — `sensitive_log_risks` Kategorie
- `tests/test_no_sensitive_logs.py` — 18 Guardrail-Tests
- Redaction durch `src/core/redaction.py`
- GitHub Actions: `.github/workflows/local-only-guardrails.yml`

## Status

Aktuell ist nur der Guardrail-Harness nachgewiesen. Ein vollstaendiger
Produkt-Golden-Path ist noch nicht implementiert.

Der No-Sensitive-Logs-Guardrail ist `GREEN_PARTIAL` fuer den aktuellen
Python-Harness. Der Local-only-Gesamtstatus bleibt `YELLOW`.

*Zuletzt aktualisiert: 2026-06-06*
