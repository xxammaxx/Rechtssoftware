# Spec — M5 Deterministische Fristkandidaten-Erkennung

## Feature
M5 — Deterministische Erkennung von Fristkandidaten aus lokal extrahiertem Dokumenttext

## Clarifications

### Session 2026-07-18

- Q: Logging-Strategie: Welche Informationen über einen Extraktionsdurchlauf dürfen geloggt werden? → A: Diagnostic Level — Kandidatenanzahl, Warnungscodes, rule_ids, Extraktionsdauer, Erfolg/Fehler-Status, sowie raw_text gekürzt auf max. 50 Zeichen. Keine vollständigen Dokumenttexte, keine Stacktraces, keine Dateipfade.
- Q: R5-Fristkontext-Präfix: Wie wird die Integration in die Rule Engine umgesetzt? → A: Post-Processing-Enrichment — R1/R2 erkennen Daten normal; separater Durchlauf prüft auf vorausgehende Präfixe und erweitert raw_text des Kandidaten.
- Q: Nebenläufigkeitsmodell: Soll der Extractor Thread-safety unterstützen? → A: Thread-safe by Design — zustandsloser, reentranter Extractor ohne shared mutable state.
- Q: Certainty-Mapping für relative Perioden (R3/R4): Welcher Wert? → A: `certainty=unresolved` — ohne Bezugspunkt nicht aufgelöst, analog zu qualitativen Referenzen (R6).
- Q: Timeout-Recovery: Was passiert bei einem Regex-Timeout während der Extraktion? → A: Vollständiger Abbruch — HTTP 500 `EXTRACTION_TIMEOUT`, keine Partialergebnisse in candidates. Die Extraktion gilt als nicht vertrauenswürdig.
- Q: R5-Präfix-Proximität: Wie viele Zeichen vor einem Datum werden auf Präfixe geprüft? → A: 50 Zeichen rückwärts vom Match-Start. Konsistent mit dem Logging-Limit (FR-M5-25).
- Q: Deduplizierungs-Schwellwert: Wann gelten zwei Treffer als "überlappend identisch"? → A: Containment-basiert — wenn die Offsets eines Kandidaten die eines anderen vollständig umschließen. Priorität: EXPLICIT_DATE > RELATIVE_PERIOD > QUALITATIVE_REFERENCE.
- Q: Unerwartete Regex-Exceptions: Wie verhält sich die Engine bei re.error oder anderen internen Regex-Fehlern (nicht Timeout)? → A: Alle unerwarteten Exceptions werden gefangen → HTTP 500 `INTERNAL_ERROR`. Kein neuer Error-Code; `INTERNAL_ERROR` deckt dies ab.
- Q: Logging-Destination: Wohin sollen die Diagnostic Logs geschrieben werden? → A: Bestehender Application-Logger `logging.getLogger("private_legal_navigator")` auf INFO-Level.
- Q: R5-Enrichment + Logging-Trunkierung: Wird der raw_text vor oder nach R5-Enrichment auf 50 Zeichen gekürzt? → A: Nach R5-Enrichment. Der enrichierte raw_text (inkl. Präfix) wird auf 50 Zeichen gekürzt.
- Q: R5-Präfixe: Sind die Präfix-Muster exhaustiv oder exemplarisch? → A: Exhaustiv — die Liste in R5 ist vollständig und durch einen Regex abgedeckt. Keine versteckten zusätzlichen Präfixe.
- Q: 500K-Zeichen-Limit: Vor oder nach Whitespace-Normalisierung? → A: Vor jeglicher Normalisierung/Preprocessing. Der rohe text_content-String wird geprüft.
- Q: Timeout-Sicherung: Ist die 5-Sekunden-Grenze Wandzeit (wall-clock) oder CPU-Zeit? → A: Wandzeit (wall-clock). Der threading.Timer misst die verstrichene Echtzeit.
- Q: Mixed-Kinds-Szenario: Soll ein Test mit allen drei Kandidaten-Typen in einem Dokument abgedeckt sein? → A: Ja — ein Erfolgsszenario mit EXPLICIT_DATE + RELATIVE_PERIOD + QUALITATIVE_REFERENCE im selben Dokument muss als Testfall existieren.

## User Stories

### US1 — Explizites Datum erkennen (P1)
Als Nutzer möchte ich explizite Datumsangaben mit Fristkontext erkennen,
damit ich relevante Stellen im Dokument schneller prüfen kann.

**Acceptance Criteria:**
- Numerische Daten im Format TT.MM.JJJJ werden erkannt und als ISO-Datum normalisiert
- Ausgeschriebene Monatsnamen ("31. Juli 2026") werden erkannt
- Kalendarisch ungültige Daten (31.02.2026) werden nicht als gültig ausgegeben
- Jede Fundstelle enthält Originaltext (`raw_text`), Zeichenposition (`start_offset`, `end_offset`) und Regel-ID (`rule_id`)

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
| FR-M5-01 | M5 MUSS vorhandenen lokal extrahierten Dokumenttext (das `text_content`-Feld aus der M3-Extraktion) analysieren. Annahme: `text_content` ist ein gültiger String (nicht None, nicht `None`); M3 garantiert dies vor Aufruf von M5. |
| FR-M5-02 | M5 MUSS numerische deutsche Datumsangaben im Format TT.MM.JJJJ erkennen |
| FR-M5-03 | M5 MUSS ausgeschriebene deutsche Monatsnamen mit vierstelligem Jahr erkennen |
| FR-M5-04 | M5 MUSS erkannte absolute Daten als ISO-Datum JJJJ-MM-TT normalisieren |
| FR-M5-05 | M5 DARF ungültige Kalenderdaten nicht als gültige Kandidaten ausgeben |
| FR-M5-06 | M5 MUSS relative Fristformulierungen erkennen, ohne ein Enddatum zu erfinden |
| FR-M5-07 | Relative Kandidaten MÜSSEN `reference_required=true` ausgeben |
| FR-M5-08 | Jeder Kandidat MUSS den Originaltext (`raw_text`) enthalten |
| FR-M5-09 | Jeder Kandidat MUSS Start- und Endposition (`start_offset`, `end_offset`) im analysierten Text enthalten |
| FR-M5-10 | Jeder Kandidat MUSS eine stabile Regel-ID (`rule_id`) enthalten. Das Suffix `_V1` kennzeichnet die erste Version; bei Änderungen wird `_V2`, `_V3` usw. verwendet (keine rückwärtskompatiblen Änderungen innerhalb derselben Version). |
| FR-M5-11 | Kandidaten MÜSSEN deterministisch nach ihrer Textposition (`start_offset`) sortiert sein |
| FR-M5-12 | Überlappende identische Treffer MÜSSEN dedupliziert werden (Containment-basiert: ein Kandidat umschließt den anderen vollständig; Priorität EXPLICIT_DATE > RELATIVE_PERIOD > QUALITATIVE_REFERENCE) |
| FR-M5-13 | Mehrere Kandidaten MÜSSEN den Warncode `MULTIPLE_DEADLINE_CANDIDATES` erzeugen |
| FR-M5-14 | Keine Kandidaten MÜSSEN den Warncode `NO_DEADLINE_CANDIDATE` erzeugen |
| FR-M5-15 | Unaufgelöste relative Angaben MÜSSEN den Warncode `RELATIVE_REFERENCE_REQUIRED` erzeugen |
| FR-M5-16 | Jede Antwort MUSS den zwingenden Warncode `LEGAL_CALCULATION_NOT_PERFORMED` enthalten |
| FR-M5-17 | M5 DARF keine externe Netzwerkverbindung benötigen |
| FR-M5-18 | M5 DARF keine vollständigen Dokumenttexte loggen |
| FR-M5-19 | M5 MUSS eine maximale Textlänge von 500.000 Zeichen vor der Regex-Verarbeitung durchsetzen. Die Prüfung erfolgt auf den rohen `text_content`-String vor jeglicher Normalisierung/Preprocessing. Ein Text, der nach Whitespace-Stripping unter 30 Zeichen fällt, wird von FR-M5-32 (leere Kandidatenliste) abgedeckt. |
| FR-M5-20 | M5 MUSS ausschließlich synthetische Testdaten verwenden |
| FR-M5-21 | M5 MUSS eine Regex-Timeout-Sicherung (5 Sekunden Wandzeit / wall-clock) implementieren. Bei Überschreitung: vollständiger Abbruch, keine Partialergebnisse (HTTP 500 `EXTRACTION_TIMEOUT`). |
| FR-M5-22 | M5 MUSS das `DeadlineExtractor`-Port (ABC) im Application-Layer definieren |
| FR-M5-23 | M5 MUSS das Antwortfeld `human_review_required: true` enthalten |
| FR-M5-24 | Alle Enums MÜSSEN `StrEnum` als Basisklasse verwenden |
| FR-M5-25 | M5 DARF zu Diagnosezwecken Kandidatenanzahl, Warnungscodes, rule_ids und Extraktionsdauer loggen; raw_text DARF auf max. 50 Zeichen gekürzt werden. Die Kürzung erfolgt nach R5-Enrichment (d.h. der enrichierte raw_text inkl. Präfix wird gekürzt). Keine vollständigen Dokumenttexte in Logs. Logging über `logging.getLogger("private_legal_navigator")` auf INFO-Level. |
| FR-M5-26 | Der `DeterministicDeadlineExtractor` MUSS zustandslos und thread-safe sein (kein shared mutable state). |
| FR-M5-27 | Relative Perioden (R3/R4) MÜSSEN `certainty=unresolved` ausgeben. |
| FR-M5-28 | R5 (Fristkontext-Präfix) MUSS als Post-Processing-Enrichment implementiert werden: R1/R2 erkennen Daten, ein separater Durchlauf erweitert raw_text um vorausgehende Präfixe. |
| FR-M5-29 | Timeout-Verhalten und Textgrößenlimit interagieren wie folgt: (a) Ein Text >500K Zeichen wird abgewiesen (HTTP 413 TEXT_TOO_LARGE), bevor eine Regex-Verarbeitung beginnt. (b) Ein Text ≤500K Zeichen, der einen Timeout auslöst, führt zu HTTP 500 EXTRACTION_TIMEOUT (vollständiger Abbruch). Es gibt keinen Szenario-Pfad, in dem beide Fehler gleichzeitig auftreten. |
| FR-M5-30 | Der Timeout-Test (T5.8) MUSS mit einem konstruierten Input, der katastrophales Backtracking auslöst (z.B. viele aufeinanderfolgende Punkte/Leerzeichen), die 5-Sekunden-Grenze verifizieren: Extraktion schlägt mit EXTRACTION_TIMEOUT fehl, candidates-Liste ist leer. |
| FR-M5-31 | Ein Erfolgsszenario mit gemischten Kandidaten-Typen (EXPLICIT_DATE + RELATIVE_PERIOD + QUALITATIVE_REFERENCE im selben Dokument) MUSS als Testfall abgedeckt sein. |
| FR-M5-32 | Ein sehr kurzer Text (<30 Zeichen) ohne Datumsmuster MUSS eine leere Kandidatenliste mit NO_DEADLINE_CANDIDATE-Warning zurückgeben (analog zu FR-M5-14). |

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

> **Annahmen & Abhängigkeiten:**
> - Python `re.finditer()` liefert Matches in der Reihenfolge ihres Auftretens (links nach rechts). Dies ist die deterministische Basis für die Sortierung (FR-M5-11).
> - `re.finditer()` liefert standardmäßig keine überlappenden Matches. Sollten Lookahead-basierte Überlappungen erforderlich werden, sind diese explizit zu dokumentieren.
> - Der Eingabetext wird als UTF-8 (bzw. ASCII-kompatibel für deutsche Texte) angenommen. Andere Kodierungen führen i.d.R. zu keiner Erkennung, da die Regex nur lateinische Schriftzeichen und Ziffern adressiert.

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
Monatsliste: Januar–Dezember (hardcoded, kein locale-Modul). Version: 1.0 (DE).
Zukünftige Sprachunterstützung (z.B. englische Monate) erfolgt durch zusätzliche
Regel-Versionen (DEADLINE_DATE_TEXTUAL_EN_V1), nicht durch Änderung der DE_V1-Liste.
Validierung: datetime.date(year, month, day); Jahr auf 1900–2099 begrenzt (analog zu R1).
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

### R5 — Fristkontext-Präfix (Post-Processing-Enrichment)
```
Für explizite Daten: Erkennt die folgenden Präfixe mittels Regex
`(bis\s+(zum|spätestens|einschließlich)|spätestens\s+am|zum)\s+`:
"bis zum", "bis spätestens", "spätestens am", "bis einschließlich", "zum"
Diese liefern zusätzlichen Kontext, erzeugen aber keine eigenen Kandidaten.
Der Präfix wird im raw_text des Datums-Kandidaten eingeschlossen.
Existieren keine EXPLICIT_DATE-Kandidaten (leere Liste), hat R5 keine Wirkung.

Implementierung: Separater Durchlauf nach R1/R2. Für jeden EXPLICIT_DATE-Kandidaten
wird der vorausgehende Text (max. 50 Zeichen rückwärts vom Match-Start) auf
Präfix-Muster geprüft. Bei Fund wird raw_text um den Präfix erweitert,
start_offset entsprechend angepasst.
Regel-ID: DEADLINE_CONTEXT_PREFIX_DE_V1 (Decorator, kein eigenständiger Kandidat)
```

### R6 — Qualitative Referenzen (nicht auflösbar)
```
Muster: "unverzüglich", "ohne schuldhaftes Zögern", "zum nächstmöglichen Zeitpunkt"
Ergebnis: kind=QUALITATIVE_REFERENCE, reference_required=true, normalized_date=null
Regel-ID: DEADLINE_QUALITATIVE_DE_V1
Hinweis: Diese Muster werden erkannt (kind=QUALITATIVE_REFERENCE), aber nicht
automatisch aufgelöst. Siehe „Bewusst nicht unterstützte Fälle" für die vollständige
Liste der nicht auflösbaren Referenzen.
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
| Regex-Timeout | 500 | `EXTRACTION_TIMEOUT` — keine Partialergebnisse; Extraktion gilt als nicht vertrauenswürdig |
| Interner Fehler (z.B. unerwartete Regex-Exception) | 500 | `INTERNAL_ERROR` |

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
- Keine Mehrbenutzer- oder Concurrency-Anforderungen (Single-User-Tool, keine Request-Rate-Limits)
- Keine neuen Persistenztabellen (Analyse-on-demand)
- Keine ML- oder LLM-Nutzung
- Keine `locale`-Modul-Abhängigkeit
- Keine spezielle Unterstützung für nicht-deutsche Texte (z.B. kyrillische Daten). Nicht-deutsche Texte werden verarbeitet, erzeugen aber aufgrund der deutschen Sprachmuster in R1–R6 typischerweise leere Kandidatenlisten.
- Keine Behandlung von Texten, die ausschließlich aus Whitespace oder Sonderzeichen bestehen — diese erzeugen eine leere Kandidatenliste (FR-M5-14).
- DSGVO-konforme Datenminimierung und Privacy-by-Design gemäß der Konformitätstabelle in `data-model.md` §Datenschutz.
