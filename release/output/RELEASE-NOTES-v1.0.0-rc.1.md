# PrivateLegalNavigator v1.0.0-rc.1 — Release Notes

**Datum:** 2026-07-26
**Status:** Release Candidate
**Klassifikation:** GREEN_V1_RC_INSTALLABLE

---

## Was ist PrivateLegalNavigator?

PrivateLegalNavigator ist eine lokale, datenschutzorientierte Anwendung zur
Unterstuetzung bei eigenen rechtlichen und behoerdlichen Angelegenheiten.

**Keine Cloud. Keine Telemetrie. Keine automatische Rechtsentscheidung.**

Alle Daten bleiben vollstaendig auf dem eigenen Rechner.

---

## Neuerungen in v1.0.0-rc.1

### Erstmals installierbar und releasefaehig

Dies ist der erste Release Candidate, der folgende Meilensteine vereint:

- **M1:** Case-Management (Faelle anlegen, auflisten, abrufen)
- **M2:** Dokument-Upload (nur PDF, MIME-Type-Pruefung, 20 MB Limit)
- **M3:** PDF-Textextraktion (pymupdf, vollstaendig lokal)
- **M4:** Regelbasierte Dokumentklassifikation (Bescheid, Rechnung, Mahnung...)
- **M5:** Deterministische Fristkandidaten-Erkennung
- **M6-A:** Bezugsereignisse und Kalenderarithmetik
- **M6-UI:** Browser-Oberflaeche mit CSRF-Schutz und Idempotenz
- **M7-A:** Legal Source Foundation (GII-Import, FTS5-Volltextsuche, Citation Resolution)
- **M7-B:** Inkrementeller GII-Sync mit Sync-Historie (dry-run/apply/force)

### Verpackung (Packaging)

- Wheel und Source Distribution bauen reproduzierbar
- CLI-Entry-Point `private-legal-navigator` verfuegbar
- `pip install [wheel]` installiert vollstaendige Anwendung
- Entwicklungsumgebung nicht erforderlich
- twine check: PASSED

### Windows-Pilotpaket

- `install.ps1` — idempotente Installation (keine Admin-Rechte)
- `start.ps1` — Start mit Healthcheck, oeffnet Browser
- `stop.ps1` — sicheres Beenden (nur eigener Prozess)
- `backup.ps1` — konsistentes Backup mit SHA-256-Manifest
- `restore.ps1` — validierte Wiederherstellung
- `uninstall.ps1` — Daten behalten (Standard) oder Purge

### Sicherheitsverbesserungen

- Cross-Case-Isolation in Dokumentenabruf repariert (vom Security-Agent gefunden)
- Mypy-Fehler in sqlite_legal_source_repository.py behoben
- Alle 906 Tests bestehen (Python 3.11 + 3.14 verifiziert)
- Coverage: 78%
- Ruff: 0 Fehler, Mypy: 0 Fehler, pip check: PASS

### Dokumentation

- V1-DEFINITION-OF-DONE.md
- INSTALL-WINDOWS.md
- USER-GUIDE.md
- BACKUP-RESTORE.md
- UPGRADE.md
- UNINSTALL.md
- TROUBLESHOOTING.md
- KNOWN-LIMITATIONS.md
- FIRST-START.md

---

## Systemanforderungen

- Windows 10 oder neuer (64-bit)
- Python 3.11, 3.12, 3.13 oder 3.14
- Keine Administratorrechte
- Keine Internetverbindung nach Installation (ausser fuer GII-Sync)

---

## Bekannte Grenzen

- Keine Rechtsberatung oder verbindliche Fristberechnung
- Nur PDF-Dokumente (kein OCR fuer gescannte Dokumente)
- Nur lokale Nutzung (127.0.0.1)
- GII ist konsolidierte Quelle, nicht das amtliche Verkuendungsorgan
- Keine Cloud-Synchronisierung oder Mehrbenutzer-Unterstuetzung
- Keine Verschluesselung auf Anwendungsebene
- Human Review fuer jede rechtlich relevante Ausgabe erforderlich

---

## Tests

- **906 Tests** bestehen (Python 3.11 + 3.14)
- **78% Code-Coverage**
- Ruff: 0 Fehler
- Mypy (strict): 0 Fehler
- pip check: PASS
- twine check: PASS (Wheel + sdist)
- Installation aus Wheel: PASS (frische Umgebung)

---

## Artefakte

| Datei | SHA-256 |
|-------|---------|
| `private_legal_navigator-1.0.0rc1-py3-none-any.whl` | `40F388DEE41A5670...` |
| `private_legal_navigator-1.0.0rc1.tar.gz` | `E9EF887C0F4EB88D57...` |
| `PrivateLegalNavigator-v1.0.0-rc.1-windows.zip` | Siehe SHA256SUMS.txt |

---

## Upgrade von v0.2.x

1. Backup erstellen (backup.ps1 oder manuell)
2. Anwendung beenden (stop.ps1)
3. Neues install.ps1 ausfuehren (idempotent)
4. Anwendung starten — Schema-Migration erfolgt automatisch
5. Daten pruefen (Faelle, Dokumente, Snapshots)

---

## Installation

Siehe `release\windows\README-INSTALLATION.md` oder `INSTALLATION-KURZANLEITUNG.txt`

---

## Repository

https://github.com/xxammaxx/Rechtssoftware
