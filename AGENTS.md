# AGENTS.md — PrivateLegalNavigator

## Arbeitsprinzipien für Agenten

1. **Local-only**: Verarbeitung bleibt vollständig lokal. Keine Cloud-KI, keine Cloud-OCR, keine Cloud-Verarbeitung.
2. **Keine Telemetrie**: Keine Analytics, kein Error Tracking, keine Nutzungsdaten.
3. **Datenschutz**: Keine personenbezogenen Daten in Logs, kein Request-Body-Logging.
4. **Keine automatische Rechtsentscheidung**: Die Software bewertet keine Rechtslagen automatisch.
5. **Keine automatische Kommunikation**: Keine automatischen Schreiben an Behörden oder Dritte.
6. **Human Review**: Jede rechtlich relevante Ausgabe erfordert menschliche Prüfung.
7. **Lokale Tests als Primärwahrheit**: Der Zustand von Repo, Code, Tests und lokaler Runtime hat Vorrang vor Dokumentation oder Erinnerung.
8. **Kein Remote-CI ohne Freigabe**: GitHub Actions, Remote-CI, Auto-Merge sind ohne ausdrückliche Freigabe verboten.
9. **Kein Push oder Merge ohne Freigabe**: Lokale Commits sind erlaubt; Remote-Operationen nicht.
10. **Spec-Kit-gesteuert**: Der Entwicklungsprozess folgt dem Spec-Kit-Ablauf (constitution → specify → clarify → plan → tasks → analyze → implement).

## Sicherheitsgrenzen

- Backend bindet standardmäßig nur an 127.0.0.1
- Keine externen Laufzeitrequests
- Parametrisierte SQL-Abfragen (keine Stringverkettung)
- Keine Secrets im Repository
- Keine produktiven oder personenbezogenen Testdaten
- Testdaten beginnen mit dem Präfix "SYNTHETISCH –"

## Architektur

Modularer Monolith mit FastAPI und SQLite. Schichten: API → Application → Domain → Infrastructure.
