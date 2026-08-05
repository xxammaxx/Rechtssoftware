# PrivateLegalNavigator v1.0.0-rc.2 — Release Notes

**Datum:** 2026-07-29
**Status:** Release Candidate (Windows Cold Test pending)
**Klassifikation:** AMBER_WINDOWS_COLD_TEST_REQUIRED
**Candidate Commit:** `b841ebae1dcea5a096a2b439b68dd34582e150ae`

---

## Was ist neu in v1.0.0-rc.2

### Windows-Lifecycle-Verbesserungen

- **Prozess-Ownership:** `server.json` dokumentiert PID, executable, startzeit, instance-ID
- **Fremdprozessschutz:** `stop.ps1` beendet ausschliesslich den Produktprozess
- **Backup-Integritaet:** SQLite-Backup-API, SHA-256-Manifest, Hash-Verifikation
- **Manipulationsschutz:** Geaenderte Backups werden abgelehnt
- **Restore-Rollback:** Bei Restore-Fehler bleibt vorheriger Zustand erhalten
- **Test-Harness:** `test-cold-install.ps1` mit 16 Gates (W01-W16)

### M7-B Sync-Verbesserungen

- 12/12 Installed-Wheel E2E Sync-Tests
- Backup/Restore durch `backup_helper.py` (93 %) und `restore_helper.py` (93 %)

### Test-Statistiken

- **1.021 Tests** bestehen (0 failed, 0 skipped)
- **79 % Code-Coverage** (insgesamt)
- **backup_helper.py:** 93 %
- **restore_helper.py:** 93 %
- **sync_service.py:** 77 % (-> [Coverage Exception](M7B-COVERAGE-EXCEPTION-RC2.md))
- Ruff: 0 Fehler | Mypy: 0 Fehler | pip check: PASS | twine check: PASS

---

## Systemanforderungen (unveraendert zu rc.1)

- Windows 10 oder neuer (64-bit) / Linux
- Python 3.11 oder 3.12
- Keine Administratorrechte
- Keine Internetverbindung nach Installation (ausser fuer GII-Sync)

---

## Bekannte Grenzen (unveraendert zu rc.1)

- Keine Rechtsberatung oder verbindliche Fristberechnung
- Nur PDF-Dokumente (kein OCR)
- Nur lokale Nutzung (127.0.0.1)
- M6-B.2 (Feiertagsdaten) nicht im Release enthalten
- sync_service.py Coverage 77 % (via [Exception](M7B-COVERAGE-EXCEPTION-RC2.md))

---

## Artefakte

| Datei | SHA-256 |
|-------|---------|
| `private_legal_navigator-1.0.0rc2-py3-none-any.whl` | `c0890257de25ae57715e1d7d4349785c7fd503f7de6ea5c67b50fc1b59f21499` |
| `private_legal_navigator-1.0.0rc2.tar.gz` | `8e186964f2476b28a5aa329a35ec48bd68b707404a8d90ea7e7de5c1e780ed0b` |
| `PrivateLegalNavigator-v1.0.0-rc.2-candidate.zip` | Windows-Testpaket (siehe SHA256SUMS.txt) |

---

## Installation

Siehe `release/windows/README-INSTALLATION.md` im Candidate-Paket.

---

## Repository

https://github.com/xxammaxx/Rechtssoftware

Branch: `release/v1.0.0-rc.2-reconciled`
Commit: `b841eba`
