# Spec — M4 Dokumentklassifikation und Unsicherheitsmodell

## Feature
M4 — Regelbasierte Dokumentklassifikation mit Unsicherheitsmodell

## User Stories

### US1 — Dokumenttyp automatisch erkennen (P1)
Als Nutzer möchte ich, dass hochgeladene Dokumente automatisch klassifiziert
werden (Bescheid, Rechnung, Mahnung etc.), damit ich den Dokumenttyp nicht
manuell erfassen muss.

### US2 — Klassifikationssicherheit einsehen (P1)
Als Nutzer möchte ich wissen, wie sicher die Klassifikation ist, damit ich
bei unsicheren Ergebnissen manuell prüfen kann.

### US3 — Klassifikationsdetails abrufen (P2)
Als Nutzer möchte ich sehen, welche Muster zur Klassifikation geführt haben,
damit die Entscheidung nachvollziehbar ist.

## Dokumenttypen (M4)

| Typ | Beschreibung |
|-----|-------------|
| bescheid | Behördlicher Bescheid |
| rechnung | Rechnung / Zahlungsaufforderung |
| mahnung | Mahnung / Vollstreckung |
| vertrag | Vertrag / Vereinbarung |
| widerspruch | Widerspruch / Einspruch |
| sonstiges | Nicht klassifizierbar |

## Funktionale Anforderungen

| ID | Anforderung |
|----|-------------|
| FR-M4-01 | Klassifikation läuft automatisch nach Upload + Textextraktion |
| FR-M4-02 | Regelbasierte Klassifikation (Keywords, lokal, kein ML) |
| FR-M4-03 | Confidence-Score zwischen 0.0 und 1.0 |
| FR-M4-04 | Confidence < 0.5 → "sonstiges" |
| FR-M4-05 | Gematchte Patterns werden gespeichert |
| FR-M4-06 | Klassifikation in Document-Response enthalten |
| FR-M4-07 | DocumentClassifier ist als Port (ABC) modelliert |
| FR-M4-08 | Späterer Austausch durch ML-Classifier möglich |

## Abgrenzung

Nicht in M4:
- ML-basierte Klassifikation
- Training auf echten Daten
- Benutzerkorrektur der Klassifikation
- Multi-Label-Klassifikation
