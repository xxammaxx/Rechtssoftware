# ADR-001 — Lokaler modularer Monolith mit FastAPI + SQLite

## Status
Accepted

## Kontext

PrivateLegalNavigator ist ein Greenfield-Projekt zur lokalen Unterstützung bei
eigenen rechtlichen und behördlichen Angelegenheiten. Der erste Meilenstein (M1)
erfordert eine stabile technische Grundlage mit Fallverwaltung (CRUD) und lokaler
Persistenz.

**Randbedingungen:**
- Ausschließlich lokale Verarbeitung (INV-01 bis INV-06)
- Keine Cloud-Abhängigkeiten
- Ein einzelner lokaler Nutzer
- Windows-Entwicklungsumgebung
- Python als primäre Sprache
- Keine produktiven Daten im ersten Lauf

## Entscheidung

Wir implementieren einen **modularen Monolithen** mit:

- **FastAPI** als API-Schicht (läuft auf `127.0.0.1`)
- **SQLite** (stdlib `sqlite3`) als lokale Persistenz
- **Vier sauber getrennte Schichten**: API → Application → Domain → Infrastructure
- **App Factory Pattern** für Testbarkeit
- **Versionierte API** unter `/api/v1`

## Alternativen

### 1. Flache FastAPI-Struktur (alles in `main.py`)

| Vorteil | Nachteil |
|---------|----------|
| Schnellster Start | Untestbare Schichtenvermischung |
| Weniger Dateien | Kein Domain-Layer |
| | Schwer erweiterbar für spätere Features |

**Verworfen**: Keine klaren Grenzen für spätere Dokumentimport- und Analyse-Features.

### 2. Microservices

| Vorteil | Nachteil |
|---------|----------|
| Unabhängig deploybar | Massive Überkomplexität für lokalen Einzelnutzer |
| | Container-Orchestrierung nötig |
| | Verteilte Transaktionen |
| | Netzwerk-Overhead lokal sinnlos |

**Verworfen**: Enterprise-Overkill für einen lokalen Einzelnutzer.

### 3. Serverseitige HTML-Anwendung (Jinja2 + HTMX)

| Vorteil | Nachteil |
|---------|----------|
| Kein separates Frontend nötig | Vermischt API und UI |
| | Erschwert späteres API-First-Frontend |
| | Weniger flexibel für SPAs |

**Verworfen**: API-First erlaubt spätere Frontend-Wahl (Desktop, Web, Mobile).

### 4. Desktop-Wrapper (Electron/PyQt)

| Vorteil | Nachteil |
|---------|----------|
| Native Desktop-Erfahrung | Zusätzliche Build-Komplexität |
| | Python-Backend + JS-Frontend-Kopplung |
| | Höhere Einstiegshürde |

**Verworfen**: Kann später ergänzt werden. API-First erlaubt jedes Frontend.

## Konsequenzen

### Positiv
- Klare Schichtengrenzen für Testbarkeit
- Domain-Layer ohne Framework-Abhängigkeiten
- App Factory ermöglicht isolierte API-Tests
- Späteres Frontend kann über versionierte API angebunden werden
- SQLite ist transparent, portabel und ausreichend

### Negativ
- Etwas mehr Boilerplate als flache Struktur
- Repository-Port/Adapter-Pattern für einfache CRUD-Operationen mag
  übertrieben wirken (rechtfertigt sich durch spätere Erweiterbarkeit)

## Sicherheitsfolgen

- Backend bindet nur an 127.0.0.1 — kein Netzwerkzugriff von außen
- SQLite liegt in konfigurierbarem lokalen Verzeichnis
- Keine Secrets, keine Authentifizierung in M1 nötig
- Parametrisierte SQL-Abfragen verhindern Injection

## Datenschutzfolgen

- Alle Daten bleiben lokal auf dem Rechner
- Keine Telemetrie, kein externer Request
- Keine Falldaten in Logs oder Fehlerausgaben
- Testdaten ausschließlich synthetisch

## Rollback

Bei fundamentalem Architekturproblem in späteren Meilensteinen:
- FastAPI durch andere API-Bibliothek ersetzen (API-Schicht isoliert)
- SQLite durch andere DB ersetzen (Repository-Port macht Austausch möglich)
- Domain-Layer bleibt unverändert (keine Infrastruktur-Abhängigkeit)

## Spätere Neubewertung

Eine Neubewertung ist sinnvoll, wenn:
- Mehrere Nutzer gleichzeitig unterstützt werden sollen
- Die Datenmenge SQLite-Grenzen überschreitet
- Ein Frontend-Framework festgelegt wird, das die API-Schicht beeinflusst
