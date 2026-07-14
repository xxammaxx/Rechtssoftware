# Spec — M5 Deterministische Fristkandidaten-Erkennung

## Feature
M5 — Deterministische Erkennung von Fristkandidaten aus lokal extrahiertem Dokumenttext

## User Stories

### US1 — Explizites Datum erkennen (P1)
Als Nutzer möchte ich explizite Datumsangaben mit Fristkontext erkennen,
damit ich relevante Stellen im Dokument schneller prüfen kann.

**Acceptance Criteria:**
- Numerische Daten im Format TT.MM.JJJJ werden erkannt und als ISO-Datum normalisiert
- Ausgeschriebene Monatsnamen ("31. Juli 2026") werden erkannt
- Kalendarisch ungültige Daten (31.02.2026) werden nicht als gültig ausgegeben
- Jede Fundstelle enthält Originaltext, Position und Regel-ID

### US2 — Relative Fristformulierung erkennen (P2)
Als Nutzer möchte ich Formulierungen wie "innerhalb von zwei Wochen"
erkennen, damit ich weiß, dass ein zusätzlicher Bezugspunkt erforderlich ist.

**Acceptance Criteria:**
- Relative Formulierungen werden mit `kind=RELATIVE_PERIOD` markiert
- `reference_required=true` wird gesetzt
- Kein Enddatum wird erfunden
- Absolute Datumsbezüge in relativen Kontexten ("bis zum 31.07.2026") werden
  als EXPLICIT_DATE erkannt

### US3 — Evidence anzeigen (P1)
Als Nutzer möchte ich Originaltext, Zeichenposition und Regelherkunft
sehen, damit ich die Erkennung nachvollziehen kann.

**Acceptance Criteria:**
- `raw_text` enthält den Originaltext aus dem Dokument
- `start_offset` und `end_offset` zeigen die Position im extrahierten Text
- `rule_id` verweist auf die auslösende Regel
- Alle Offsets können im extrahierten Text verifiziert werden

### US4 — Unsicherheit erkennen (P1)
Als Nutzer möchte ich Warnungen bei fehlenden, mehreren oder
uneindeutigen Kandidaten erhalten, damit keine falsche Sicherheit entsteht.

**Acceptance Criteria:**
- Jede Antwort enthält zwingend den Warncode `LEGAL_CALCULATION_NOT_PERFORMED`
- Relative Kandidaten ohne Bezugspunkt erzeugen `RELATIVE_REFERENCE_REQUIRED`
- Mehrere Kandidaten erzeugen `MULTIPLE_DEADLINE_CANDIDATES`
- Keine Kandidaten erzeugen `NO_DEADLINE_CANDIDATE`
- Ungültige Kalenderdaten werden nicht als gültig ausgegeben

---

## Funktionale Anforderungen

| ID | Anforderung |
|----|-------------|
| FR-M5-01 | M5 MUSS vorhandenen lokal extrahierten Dokumenttext analysieren |
| FR-M5-02 | M5 MUSS numerische deutsche Datumsangaben im Format TT.MM.JJJJ erkennen |
| FR-M5-03 | M5 MUSS ausgeschriebene deutsche Monatsnamen mit vierstelligem Jahr erkennen |
| FR-M5-04 | M5 MUSS erkannte absolute Daten als ISO-Datum JJJJ-MM-TT normalisieren |
| FR-M5-05 | M5 DARF ungültige Kalenderdaten nicht als gültige Kandidaten ausgeben |
| FR-M5-06 | M5 MUSS relative Fristformulierungen erkennen, ohne ein Enddatum zu erfinden |
| FR-M5-07 | Relative Kandidaten MÜSSEN `reference_required=true` ausgeben |
| FR-M5-08 | Jeder Kandidat MUSS den Originaltext (`raw_text`) enthalten |
| FR-M5-09 | Jeder Kandidat MUSS Start- und Endposition (`start_offset`, `end_offset`) im analysierten Text enthalten |
| FR-M5-10 | Jeder Kandidat MUSS eine stabile Regel-ID (`rule_id`) enthalten |
| FR-M5-11 | Kandidaten MÜSSEN deterministisch nach ihrer Textposition (`start_offset`) sortiert sein |
| FR-M5-12 | Überlappende identische Treffer MÜSSEN dedupliziert werden |
| FR-M5-13 | Mehrere Kandidaten MÜSSEN den Warncode `MULTIPLE_DEADLINE_CANDIDATES` erzeugen |
| FR-M5-14 | Keine Kandidaten MÜSSEN den Warncode `NO_DEADLINE_CANDIDATE` erzeugen |
| FR-M5-15 | Unaufgelöste relative Angaben MÜSSEN den Warncode `RELATIVE_REFERENCE_REQUIRED` erzeugen |
| FR-M5-16 | Jede Antwort MUSS den zwingenden Warncode `LEGAL_CALCULATION_NOT_PERFORMED` enthalten |
| FR-M5-17 | M5 DARF keine externe Netzwerkverbindung benötigen |
| FR-M5-18 | M5 DARF keine vollständigen Dokumenttexte loggen |
| FR-M5-19 | M5 MUSS eine maximale Textlänge von 500.000 Zeichen vor der Regex-Verarbeitung durchsetzen |
| FR-M5-20 | M5 MUSS ausschließlich synthetische Testdaten verwenden |
| FR-M5-21 | M5 MUSS eine Regex-Timeout-Sicherung (5 Sekunden) implementieren |
| FR-M5-22 | M5 MUSS das `DeadlineExtractor`-Port (ABC) im Application-Layer definieren |
| FR-M5-23 | M5 MUSS das Antwortfeld `human_review_required: true` enthalten |
| FR-M5-24 | Alle Enums MÜSSEN `StrEnum` als Basisklasse verwenden |

---

## Bewusst nicht unterstützte Fälle

In M5 nicht automatisch auflösen:

- "innerhalb eines Monats nach Bekanntgabe"
- "binnen zwei Wochen nach Zustellung"
- "unverzüglich", "ohne schuldhaftes Zögern"
- "zum nächstmöglichen Zeitpunkt"
- "innerhalb der gesetzlichen Frist"
- Feiertagsverschiebungen, Wochenendverschiebungen
- Zustellungsfiktionen, Zugangsnachweise
- Rechtsbehelfsarten, Fristverlängerungen
- Wiedereinsetzung, Hemmung, Neubeginn

Solche Texte dürfen als ungelöste Kandidaten erscheinen
(`kind=RELATIVE_PERIOD` oder `kind=QUALITATIVE_REFERENCE`),
aber niemals mit einem berechneten Enddatum.

---

## Regelkatalog

### R1 — Explizite numerische Daten
```
Muster: TT.MM.JJJJ (mit optionalen Leerzeichen nach Punkten)
Beispiele: 31.07.2026, 31. 07. 2026, 1.7.2026
Regex:   (?<!\d)(0?[1-9]|[12]\d|3[01])\.\s*(0?[1-9]|1[0-2])\.\s*(19|20)\d{2}(?!\d)
Validierung: datetime.strptime(), ValueError → kein Kandidat, Warnung AMBIGUOUS_DATE
Regel-ID: DEADLINE_DATE_NUMERIC_DE_V1
```

### R2 — Ausgeschriebene Monatsnamen
```
Muster: T. Monat JJJJ
Beispiele: 31. Juli 2026, 1. August 2026, 31. Dezember 2026
Monatsliste: Januar–Dezember (hardcoded, kein locale-Modul)
Regel-ID: DEADLINE_DATE_TEXTUAL_DE_V1
```

### R3 — Relative Zeiträume mit Zahl
```
Muster: "innerhalb von N Einheit", "binnen N Einheit"
Beispiele: "innerhalb von zwei Wochen", "binnen 14 Tagen"
Einheiten: Tag(e/en), Woche(n), Monat(e/en), Jahr(e/en)
Ergebnis: kind=RELATIVE_PERIOD, amount=N, unit=Einheit, reference_required=true
Regel-ID: DEADLINE_RELATIVE_NUMERIC_DE_V1
```

### R4 — Relative Zeiträume mit Artikel
```
Muster: "innerhalb eines/einer Einheit", "binnen eines/einer Einheit"
Beispiele: "innerhalb eines Monats", "binnen einer Woche"
Ergebnis: kind=RELATIVE_PERIOD, amount=1, unit=Einheit, reference_required=true
Regel-ID: DEADLINE_RELATIVE_ARTICLE_DE_V1
```

### R5 — Fristkontext-Präfix
```
Für explizite Daten: Erkennt Präfixe wie "bis zum", "bis spätestens",
"spätestens am", "bis einschließlich", "zum"
Diese liefern zusätzlichen Kontext, erzeugen aber keine eigenen Kandidaten.
Der Präfix wird im raw_text des Datums-Kandidaten eingeschlossen.
```

### R6 — Qualitative Referenzen (nicht auflösbar)
```
Muster: "unverzüglich", "ohne schuldhaftes Zögern", "zum nächstmöglichen Zeitpunkt"
Ergebnis: kind=QUALITATIVE_REFERENCE, reference_required=true, normalized_date=null
Regel-ID: DEADLINE_QUALITATIVE_DE_V1
```

---

## Negative Beispiele (False Positives vermeiden)

| Kategorie | Beispiel | Warum kein Kandidat |
|-----------|----------|-------------------|
| Aktenzeichen | `Az. 31.07.2026-A` | Datum in nicht-Fristkontext |
| Seitennummern | `Seite 31.07.2026` | Kontextabhängig — in M5 akzeptiert, in M6 kontextuell filtern |
| Versionen | `Version 01.02.2026` | Kein negativer Lookbehind für Buchstaben |
| Paragraph | `§ 31.07.2026` | Nicht als Datum interpretierbar |
| Ungültiges Datum | `31.02.2026` | `datetime.strptime()` wirft `ValueError` |
| Ungültiges Jahr | `99.99.9999` | Jahr auf 1900–2099 begrenzt |
| Beträge | `31.07,26 €` | Komma statt Punkt, Jahr zu kurz |

---

## API-Contract

```
POST /api/v1/cases/{case_id}/documents/{document_id}/deadline-candidates
```

### Erfolgsantwort (200)

```json
{
  "document_id": "uuid",
  "candidates": [
    {
      "kind": "explicit_date",
      "raw_text": "bis spätestens 31. Juli 2026",
      "start_offset": 120,
      "end_offset": 151,
      "normalized_date": "2026-07-31",
      "amount": null,
      "unit": null,
      "reference_required": false,
      "certainty": "exact",
      "rule_id": "DEADLINE_DATE_TEXTUAL_DE_V1"
    }
  ],
  "warnings": [
    {
      "code": "LEGAL_CALCULATION_NOT_PERFORMED",
      "message": "Es wurde keine rechtliche Frist berechnet. Nur Textstellen erkannt."
    }
  ],
  "human_review_required": true
}
```

### Fehlerfälle

| Fall | HTTP | Error Code |
|------|------|------------|
| Dokument nicht gefunden | 404 | `DOCUMENT_NOT_FOUND` |
| Case nicht gefunden | 404 | `CASE_NOT_FOUND` |
| Kein Text extrahiert | 200 | Leere Kandidatenliste + `NO_DEADLINE_CANDIDATE` |
| Text zu groß (>500K Zeichen) | 413 | `TEXT_TOO_LARGE` |
| Regex-Timeout | 500 | `EXTRACTION_TIMEOUT` |
| Interner Fehler | 500 | `INTERNAL_ERROR` |

---

## Warncodes (stabil)

| Code | Bedeutung |
|------|-----------|
| `LEGAL_CALCULATION_NOT_PERFORMED` | Zwingend in jeder Antwort. Keine rechtliche Frist wurde berechnet. |
| `NO_DEADLINE_CANDIDATE` | Keine Fristkandidaten im Text gefunden |
| `MULTIPLE_DEADLINE_CANDIDATES` | Mehrere Fristkandidaten gefunden — manuelle Priorisierung erforderlich |
| `RELATIVE_REFERENCE_REQUIRED` | Mindestens ein relativer Kandidat benötigt einen Bezugspunkt |
| `AMBIGUOUS_DATE` | Ein Datumsmuster wurde gefunden, aber als kalendarisch ungültig verworfen |

---

## Abgrenzung

Nicht in M5:
- Keine verbindliche Rechtsfristberechnung
- Keine Feiertags- oder Wochenendlogik
- Keine Zustellungsfiktion
- Keine Rechtsberatung
- Keine Cloud-Dienste, keine externen APIs
- Kein Frontend
- Keine automatische Kommunikation
- Keine neuen Persistenztabellen (Analyse-on-demand)
- Keine ML- oder LLM-Nutzung
- Keine `locale`-Modul-Abhängigkeit
