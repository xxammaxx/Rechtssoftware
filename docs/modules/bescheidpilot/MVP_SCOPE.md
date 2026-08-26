# MVP Scope

## Ziel

Der MVP beweist einen einzigen lokalen Golden Path für einen synthetischen Beispielbescheid:

```text
Text rein -> Frist/Handlung/Fundstelle -> Entwurf -> Human Review -> lokaler Export
```

## Im Scope

- lokale Texteingabe
- strukturierte Frist- und Handlungskandidaten
- genaue Fundstellen und sichtbare Unsicherheit
- lokal erzeugter, prüfbarer Antwortentwurf
- verpflichtende menschliche Prüfung
- expliziter lokaler Export
- Offline- und Network-Deny-Evidence
- ein synthetischer Vertical-Slice-Fall
- später zwanzig realistische oder rechtmäßig anonymisierte Validierungsfälle
- erstes Berater-/Förderfeedbackgespräch zur Problemvalidierung (Issue #53; Outreach Welle 1 — T-002 BAG Schuldnerberatung, T-004 Caritas, T-003 AWO — wurde manuell versendet. Es liegt noch kein dokumentiertes Feedbackgespräch vor. Keine Marktvalidierung.)

## Nicht im Scope

- automatische Rechtsberatung oder Rechtsentscheidung
- garantierte Fristberechnung
- automatische Behördenkommunikation
- Cloud-OCR, Cloud-KI oder Remote-Fallback
- Kollaboration oder Cloud-Synchronisierung
- unbeaufsichtigte Massenverarbeitung
- produktive Nutzung mit echten Bescheiden vor Pilotfreigabe
- Zahlungs- oder Organisationsverwaltung

## Scope Gate

Ein Feature wird nur aufgenommen, wenn es den Golden Path, einen zwingenden Local-only-Guardrail oder Pilot-Evidence direkt unterstützt. Alles andere erhält `Later` oder `Out of Scope`.
