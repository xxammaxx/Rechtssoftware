# Lokale Release-Verifikation — PrivateLegalNavigator

Dieses Dokument beschreibt, wie ein lokaler Release Candidate gebaut,
installiert und verifiziert wird.

## Build

### Voraussetzungen

- Python 3.11+ mit installierten Build-Tools
- `setuptools`, `wheel` im Build-Environment

### Bau des Wheels

```powershell
# Aus dem Repository-Wurzelverzeichnis:
cd C:\Rechtssoftware

# Wheel bauen (keine Netzwerkinstallation)
python -m pip wheel . --no-deps --no-build-isolation --wheel-dir dist\rc
```

Ergebnis: `dist\rc\private_legal_navigator-0.1.0-py3-none-any.whl`

## Clean Install

### Neue virtuelle Umgebung

```powershell
py -3.14 -m venv C:\Pfad\Neue-Installation\.venv
```

### Installation aus dem Wheel

```powershell
# Zuerst Laufzeitabhängigkeiten installieren
C:\Pfad\Neue-Installation\.venv\Scripts\python.exe -m pip install `
    fastapi>=0.115.0 jinja2>=3.1 python-multipart>=0.0.9 `
    uvicorn[standard]>=0.30.0 pymupdf>=1.24.0

# Dann das Anwendungspaket (ohne Abhängigkeiten)
C:\Pfad\Neue-Installation\.venv\Scripts\python.exe -m pip install `
    --no-deps --find-links C:\Rechtssoftware\dist\rc private-legal-navigator
```

### Installationsnachweis

```powershell
C:\Pfad\Neue-Installation\.venv\Scripts\python.exe -m pip check
C:\Pfad\Neue-Installation\.venv\Scripts\python.exe -c "import private_legal_navigator; print(private_legal_navigator.__file__)"
```

Der Import muss aus dem site-packages der neuen Umgebung stammen,
nicht aus dem Entwickler-Checkout.

## Verifikationsschritte

### 1. Smoke-Test

```powershell
# Anwendung starten
C:\Pfad\Neue-Installation\.venv\Scripts\python.exe -m private_legal_navigator

# In einem zweiten Terminal prüfen:
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ui/cases
curl http://127.0.0.1:8000/static/css/app.css
```

Erwartet: HTTP 200 für alle drei Endpunkte.

### 2. Leere Datenbank

Die Anwendung initialisiert automatisch eine leere SQLite-Datenbank
und erstellt die erforderlichen Tabellen.

### 3. Migration bestehender Datenbank

Eine bestehende Datenbank aus einer Vorgängerversion wird automatisch
migriert ("CREATE TABLE IF NOT EXISTS"-Ansatz). Der `is_revoke`-Column
wird ergänzt, falls nicht vorhanden.

### 4. Vollständiger Testdurchlauf

```powershell
# In der Entwicklungsumgebung:
cd C:\Rechtssoftware
.\.venv\Scripts\Activate.ps1
python -m pytest -ra --cov=src/private_legal_navigator --cov-fail-under=90
```

### 5. SHA-256-Verifikation

```powershell
Get-FileHash -LiteralPath "dist\rc\private_legal_navigator-0.1.0-py3-none-any.whl" -Algorithm SHA256
```

## Release-Artefakte

Nach erfolgreichem Build:

| Datei | Beschreibung |
|-------|-------------|
| `dist/rc/*.whl` | Installierbares Wheel-Paket |
| `dist/rc/SHA256SUMS.txt` | Prüfsummen |
| `evidence/.../release-manifest/RC-MANIFEST.json` | Release-Manifest |
| `evidence/.../release-manifest/BUILD-INFO.txt` | Build-Informationen |

## Wichtige Hinweise

- **Kein Remote-Push erforderlich** — der Release Candidate ist ein
  lokales Artefakt.
- **Keine Versionsänderung** ohne dokumentierte Release-Policy.
- **Keine automatische Rechtsentscheidung** — die Preview ist
  unverbindlich.
- **Local-only** — die Anwendung bindet ausschließlich an 127.0.0.1.
