# Privacy & Security Invariants — PrivateLegalNavigator

## Datenschutz-Invarianten

| ID | Invariante | Status |
|----|-----------|--------|
| INV-01 | Falldaten bleiben lokal | ✓ |
| INV-02 | Keine Cloud-Verarbeitung | ✓ |
| INV-03 | Keine Telemetrie | ✓ |
| INV-04 | Keine Analytics | ✓ |
| INV-05 | Keine sensiblen Daten in Logs | ✓ |
| INV-06 | Keine externen Laufzeitrequests | ✓ |

## Rechts- und Nutzungsgrenzen

| ID | Invariante | Status |
|----|-----------|--------|
| INV-07 | Nur Unterstützung bei eigenen Angelegenheiten | ✓ |
| INV-08 | Keine automatische Rechtsentscheidung | ✓ |
| INV-09 | Keine verbindliche Rechtsberatung | ✓ |
| INV-10 | Keine automatische Kommunikation | ✓ |
| INV-11 | Menschliche Prüfung erforderlich | ✓ |
| INV-12 | Unsicherheit nicht verbergen | ✓ |

## Technische Grenzen

| ID | Invariante | Status |
|----|-----------|--------|
| INV-13 | Backend bindet nur an 127.0.0.1 | ✓ |
| INV-14 | Lokale Tests sind Primärwahrheit | ✓ |
| INV-15 | Keine produktiven Daten in Tests | ✓ |
| INV-16 | Datenverzeichnis konfigurierbar (PLN_DATA_DIR) | ✓ |
| INV-17 | Fehler geben keine sensiblen Inhalte aus | ✓ |
| INV-18 | Parametrisierte SQL-Abfragen | ✓ |
| INV-19 | IDs nicht als Dateipfade interpretiert | ✓ |
| INV-20 | Architekturänderungen benötigen dokumentierte Entscheidung | ✓ |

## Security-Sweep-Ergebnis (M1)

| Check | Ergebnis |
|-------|----------|
| Externe URLs im Code | 0 Treffer |
| `.env`-Dateien im Repo | 0 Treffer |
| CORS-Konfiguration | Keine (Safe Default) |
| Secrets im Code | Keine |
| `.sqlite`-Dateien im Repo | Keine |
| Synth. Testdaten-Präfix | "SYNTHETISCH" verwendet |
| Host-Bindung | 127.0.0.1 (konfigurierbar) |

## Verifikation

```bash
# Host-Bindung prüfen
grep -r "127.0.0.1" src/

# Externe Requests prüfen
grep -rE "https?://" src/ --include="*.py" | grep -v "github.com"

# Secrets prüfen
grep -rE "(api_key|secret|token|password)" src/ --include="*.py"

# SQL-Injection prüfen
grep -r "f\".*SELECT\|f'.*SELECT\|+.*SELECT\|%.*SELECT" src/ --include="*.py"
```
