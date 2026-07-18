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
| FR-M4-01 | Klassifikation läuft automatisch und synchron nach Upload + Textextraktion im `POST /cases/{id}/documents`-Endpoint |
| FR-M4-02 | Regelbasierte Klassifikation (Keywords, lokal, kein ML) — Patterns als Python-Dataclasses in `domain/classifier.py` definiert |
| FR-M4-03 | Confidence-Score zwischen 0.0 und 1.0, berechnet nach Ratio-Modell (gematchte Patterns / alle Patterns des Gewinnertyps) |
| FR-M4-04 | Confidence < 0.5 → "sonstiges" (bei 0 Matches → 0.0 → "sonstiges") |
| FR-M4-05 | Gematchte Patterns werden gespeichert |
| FR-M4-06 | `doc_type`, `classification_confidence` und `matched_patterns` im Document-Response (`POST` + `GET`) enthalten; kein separater Endpoint nötig |
| FR-M4-07 | DocumentClassifier ist als Port (ABC) modelliert |
| FR-M4-08 | Späterer Austausch durch ML-Classifier möglich |
| FR-M4-09 | Tie-Breaking bei Mehrfachmatches: Typ mit höchstem Ratio-Score gewinnt; bei Gleichstand entscheidet Definitionsreihenfolge |
| FR-M4-10 | Bei leerer/fehlgeschlagener Textextraktion: Klassifikation ergibt `sonstiges` mit `confidence=0.0` und leerer `matched_patterns` — Upload bleibt erfolgreich |
| FR-M4-11 | Klassifikation muss innerhalb von 100 ms für typische Dokumente (< 50 KB Text) abschliessen (lokale Regex, keine asynchrone Verarbeitung) |
| FR-M4-12 | Jede Klassifikation wird geloggt: doc_type, confidence, Anzahl gematchter Patterns (INFO-Level, Python logging) |

## Abgrenzung

Nicht in M4:
- ML-basierte Klassifikation
- Training auf echten Daten
- Benutzerkorrektur der Klassifikation
- Multi-Label-Klassifikation
- Re-Klassifikation bestehender Dokumente (Klassifikation läuft genau einmal beim Upload; Dokumente sind immutabel)

## Clarifications

### Session 2026-07-18

- Q: How is the confidence score calculated? → A: Ratio-based model: confidence = matched_patterns_of_winning_type / total_patterns_of_winning_type. If no patterns match, confidence = 0.0 → falls into "sonstiges" via FR-M4-04.
- Q: How and where are classification rules/patterns defined? → A: Python Dataclasses in `domain/classifier.py`. No external config files for M4.
- Q: Is classification synchronous or async? How does the user access classification details (US3)? → A: Synchronous in `POST /cases/{id}/documents`. `matched_patterns`, `doc_type`, and `classification_confidence` are all returned in the document response. No separate endpoint needed.
- Q: How is the winning type determined when patterns from multiple types match? → A: Highest ratio-score wins. Tie → first type in definition order.
- Q: What happens when text extraction yields empty/no text? → A: Classification produces "sonstiges" with confidence=0.0 and empty matched_patterns. Upload remains successful.
