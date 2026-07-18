# Research — M5 Deadline Candidate Extraction

## Design Decisions

### 1. Extraction Approach: Deterministic Regex

| | |
|---|---|
| **Decision** | Deterministische Regex-basierte Extraktion (kein ML/LLM) |
| **Rationale** | M5 erfordert deterministische, nachvollziehbare Ergebnisse ohne externe Abhängigkeiten. Regex erfüllt alle Anforderungen: lokal, deterministisch, testbar, kein externer Service. |
| **Alternatives considered** | • ML-basiert (z.B. spaCy NER) — nicht deterministisch, benötigt Modelle, zu schwergewichtig<br>• LLM-basiert — nicht deterministisch, benötigt Network oder große lokale Modelle, Verstoß gegen Constitution Art. 1 (Local-only)<br>• Hybrid (Regex + ML-Validierung) — zu komplex für M5, könnte in M7 evaluiert werden |
| **Constraint** | Constitution Art. 1 (Local-only), Art. 3 (Keine automatische Rechtsentscheidung), FR-M5-17 (keine Netzwerkverbindung) |

### 2. Storage: Analyse-on-demand

| | |
|---|---|
| **Decision** | Keine Persistenz der Deadline Candidates (Analyse-on-demand) |
| **Rationale** | Ergebnisse bleiben aus `Document.text_content` jederzeit reproduzierbar. Kein vorzeitiges Schema, kein CASCADE-Problem. Minimaler Datenschutz-Footprint. |
| **Alternatives considered** | • Persistenz in SQLite — erfordert Schema-Migration, erzeugt Daten, die bei Dokumentlöschung bereinigt werden müssen<br>• In-Memory-Cache — kurze Lebensdauer, aber unnötige Komplexität für erste Implementierung |
| **Constraint** | Constitution Art. 2 (Privacy by Design), FR-M5-20 (keine Produktivdaten) |

### 3. R5-Implementierung: Post-Processing-Enrichment

| | |
|---|---|
| **Decision** | Separater Enrichment-Durchlauf nach R1/R2 (Post-Processing) |
| **Rationale** | Saubere Trennung von Erkennung und Dekoration. R1/R2 können isoliert getestet werden. Vermeidet komplexe Lookbehind-Konstruktionen in den Datums-Regexes. |
| **Alternatives considered** | • Lookbehind-integriert in R1/R2 — schwer lesbar, wartbar, testbar<br>• Separate Metadata-Dekoration — unnötige Indirektion, Enrichment ist einfacher |
| **Constraint** | FR-M5-28 (als Klarstellung aufgenommen) |

### 4. Nebenläufigkeit: Thread-safe by Design

| | |
|---|---|
| **Decision** | Extractor ist zustandslos und reentrant (kein shared mutable state) |
| **Rationale** | Der Extractor ist von Natur aus zustandslos (Input: Text → Output: Result). Explizite Dekoration als thread-safe verhindert spätere Regressionen. |
| **Alternatives considered** | • Single-thread-Ann scheduled.  — für local-only ausreichend, aber erschwert spätere Änderungen<br>• Lock-basiert — unnötig bei zustandslosem Design |
| **Constraint** | FR-M5-26 (als Klarstellung aufgenommen) |

### 5. Datumsvalidierung: Regex + strptime

| | |
|---|---|
| **Decision** | Regex für Mustererkennung, `datetime.strptime()` für kalendarische Validierung |
| **Rationale** | Datums-Regexes erkennen Muster, sind aber nicht in der Lage, kalendarische Korrektheit zu prüfen (30. Februar). `strptime` ist die kanonische Python-Validierung. |
| **Alternatives considered** | • Reine Regex — kann 31.02.2026 nicht als ungültig erkennen<br>• `calendar`-Modul — möglich, aber strptime ist einfacher und ausreichend |
| **Constraint** | FR-M5-05 (ungültige Kalenderdaten zurückweisen) |

### 6. Monatsnamen: Hardcoded German Dict

| | |
|---|---|
| **Decision** | Hardcoded deutsches Monats-Dictionary (Januar–Dezember), kein `locale`-Modul |
| **Rationale** | `locale`-Modul ist nicht deterministisch (abhängig von System-Environment). Hardcoded ist deterministisch, testbar und benötigt keine externen Abhängigkeiten. |
| **Alternatives considered** | • `locale`-Modul — nicht deterministisch, Systemabhängigkeit<br>• `babel`-Bibliothek — externe Abhängigkeit, für einen einzelnen Monatsdict zu schwergewichtig |
| **Constraint** | FR-M5-17 (keine externen Abhängigkeiten), Abgrenzung (kein locale-Modul) |

### 7. Logging: Diagnostic Level

| | |
|---|---|
| **Decision** | Diagnostic Logging: Kandidatenanzahl, Warnungscodes, rule_ids, Dauer, Status; raw_text auf max. 50 Zeichen gekürzt |
| **Rationale** | Ermöglicht Debugging ohne Privacy-Verletzung. Keine vollständigen Dokumenttexte, keine Stacktraces, keine Dateipfade. |
| **Alternatives considered** | • Minimal (nur Dauer + Status) — zu wenig Information für Debugging<br>• Vollständig raw_text — Privacy-Verstoß (FR-M5-18)<br>• Kein Logging — nicht debugbar |
| **Constraint** | FR-M5-18, FR-M5-25 (als Klarstellung aufgenommen) |

### 9. Timeout-Recovery: Vollständiger Abbruch

| | |
|---|---|
| **Decision** | Bei Regex-Timeout: vollständiger Abbruch, keine Partialergebnisse. HTTP 500 `EXTRACTION_TIMEOUT`. |
| **Rationale** | Partialergebnisse wären irreführend (unvollständige Kandidatenliste). Constitution §3 (Keine automatische Rechtsentscheidung) verbietet die Auslieferung unvollständiger, potentiell irreführender Daten. |
| **Alternatives considered** | • Partial-Ergebnisse mit Warnung — Nutzer könnte unvollständige Liste als vollständig interpretieren<br>• Leere Ergebnisliste — versteckt den Timeout-Zustand |
| **Constraint** | FR-M5-21 (Timeout), Clarification Session 2026-07-18 |

### 10. R5-Präfix-Proximität: 50 Zeichen

| | |
|---|---|
| **Decision** | R5 durchsucht max. 50 Zeichen rückwärts vom Match-Start des EXPLICIT_DATE-Kandidaten |
| **Rationale** | 50 Zeichen decken die längsten Spec-Beispiele ab ("bis spätestens 31. Juli 2026" = 31 Zeichen). Konsistent mit dem 50-Zeichen-Logging-Limit (FR-M5-25). |
| **Alternatives considered** | • 20 Zeichen — zu kurz für "bis spätestens" + Datum<br>• 100 Zeichen — erhöht False-Positive-Risiko (Präfix in vorherigem Satz)<br>• Satzzeichenbegrenzung — dynamisch, aber komplexer |
| **Constraint** | FR-M5-28 (R5-Enrichment), Clarification Session 2026-07-18 |

### 11. Deduplizierungs-Strategie: Containment-basiert

| | |
|---|---|
| **Decision** | Deduplizierung prüft auf vollständiges Offset-Containment (ein Kandidat umschließt den anderen). Priorität: EXPLICIT_DATE > RELATIVE_PERIOD > QUALITATIVE_REFERENCE. |
| **Rationale** | Containment ist präziser als partielle Überlappung — vermeidet fälschliche Löschung benachbarter Kandidaten. Die Prioritätsreihenfolge stellt sicher, dass der informativste Kandidat (explizites Datum) erhalten bleibt. |
| **Alternatives considered** | • Exakte Offset-Identität — zu strikt, verpasst Containment-Fälle<br>• Partielle Überlappung — zu aggressiv, löscht legitime Nachbarkandidaten |
| **Constraint** | FR-M5-12 (Deduplizierung), Clarification Session 2026-07-18 |

### 12. Logging-Destination: Application-Logger

| | |
|---|---|
| **Decision** | Logging über `logging.getLogger("private_legal_navigator")` auf INFO-Level |
| **Rationale** | Nutzt existierende Logging-Infrastruktur. Keine neue Konfiguration. Betrieb kann Ziel (Datei/stdout) via logging-Konfiguration steuern. |
| **Alternatives considered** | • stdout direkt — nicht steuerbar, keine Log-Level<br>• Dedizierter Logger — granular, aber zusätzliche Konfiguration nötig |
| **Constraint** | FR-M5-25 (Diagnostic Logging), Clarification Session 2026-07-18 |

### 13. Unerwartete Regex-Exceptions: INTERNAL_ERROR

| | |
|---|---|
| **Decision** | Alle unerwarteten Regex-Exceptions werden gefangen → HTTP 500 `INTERNAL_ERROR` |
| **Rationale** | Spezifikation hat bereits generischen INTERNAL_ERROR-Code. Kein neuer Error-Code nötig. Konsistent mit FastAPI-Exception-Handling-Patterns. |
| **Alternatives considered** | • Neuer REGEX_FAILURE-Code — keine zusätzliche Nutzerinformation, da Ursache nicht unterscheidbar |
| **Constraint** | Fehlerfälle-Tabelle (Spec), Clarification Session 2026-07-18 |

### 8. Certainty-Mapping

| | |
|---|---|
| **Decision** | • R1/R2 (gültig) → `certainty=exact`<br>• R1/R2 (ungültig) → `certainty=ambiguous` (verworfen, Warning AMBIGUOUS_DATE)<br>• R3/R4 → `certainty=unresolved` (relative Perioden ohne Bezugspunkt)<br>• R6 → `certainty=unresolved` (qualitative Referenzen) |
| **Rationale** | "Exact" nur bei aufgelösten Daten. Relative und qualitative Angaben sind inhärent unaufgelöst. Konsistent über alle Regeln hinweg. |
| **Alternatives considered** | • `certainty=exact` für R3/R4 — suggeriert falsche Genauigkeit, da der Bezug fehlt |
| **Constraint** | FR-M5-27 (als Klarstellung aufgenommen) |

---

## Dependencies

| Dependency | Version | Purpose | Status |
|------------|---------|---------|--------|
| Python | 3.11+ | Runtime | Installiert |
| pydantic | ≥2.0 | API response schemas | Installiert |
| pytest | ≥8.0 | Testing framework | Installiert |
| pytest-cov | ≥5.0 | Coverage measurement | Installiert |
| ruff | — | Linter | Installiert |
| mypy | — | Type checker | Installiert |
| FastAPI | ≥0.110 | Web framework | Installiert (Host) |
| pymupdf | — | PDF text extraction (M3) | Installiert (keine neue Abhängigkeit) |

**Keine neuen externen Abhängigkeiten** für M5 — alle benötigten Module sind Python-Standard (`datetime`, `re`, `threading`, `dataclasses`, `enum`).

---

## Risk Assessment

| Risk | Impact | Prob. | Mitigation |
|------|--------|-------|------------|
| Catastrophic backtracking | Verlangsamung/Absturz | Medium | 5s Regex-Timeout (FR-M5-21), 500K Zeichen-Limit (FR-M5-19) |
| False positives (Aktenzeichen als Datum) | Nutzerverwirrung | Low | Negative Examples dokumentiert, Warnung AMBIGUOUS_DATE |
| Ungültige Kalenderdaten | Fehlerhafte Kandidaten | Low | strptime-Validierung (FR-M5-05) |
| Privacy-Leak durch Logging | DSGVO-Verstoß | Low | Diagnostic Logging mit 50-Zeichen-Kürzung (FR-M5-25) |
| R5-Offsets inkonsistent | Nicht reproduzierbare Positionen | Medium | start_offset wird bei R5-Enrichment angepasst |
