# Lokale Installation — PrivateLegalNavigator

## Voraussetzungen

- **Python 3.11 oder neuer** (getestet mit Python 3.14.6)
- **Git** (optional, für Repository-Zugriff)
- **Keine** Internetverbindung erforderlich (nach erstmaligem Download der Abhängigkeiten)

## Installation aus einem gebauten Wheel

### 1. Virtuelle Umgebung erstellen

```powershell
py -3.14 -m venv C:\Pfad\zur\Installation\.venv
```

### 2. Abhängigkeiten installieren

```powershell
C:\Pfad\zur\Installation\.venv\Scripts\python.exe -m pip install fastapi>=0.115.0 jinja2>=3.1 python-multipart>=0.0.9 uvicorn[standard]>=0.30.0 pymupdf>=1.24.0
```

### 3. Anwendungspaket installieren

```powershell
C:\Pfad\zur\Installation\.venv\Scripts\python.exe -m pip install --no-deps --find-links C:\Pfad\zum\dist\rc private-legal-navigator
```

### 4. Starten

```powershell
C:\Pfad\zur\Installation\.venv\Scripts\python.exe -m private_legal_navigator
```

Die Anwendung ist unter http://127.0.0.1:8000 erreichbar.

## Konfiguration über Umgebungsvariablen

| Variable | Beschreibung | Standard |
|----------|-------------|----------|
| `PLN_DATA_DIR` | Datenverzeichnis für SQLite-Datenbank | `~/.private-legal-navigator` |
| `PLN_HOST` | Binde-Adresse | `127.0.0.1` |
| `PLN_PORT` | Port | `8000` |
| `PLN_CSRF_SECRET` | Geheimer Schlüssel für CSRF-Token (bei Neustart ohne diese Variable wird ein neuer generiert) | Automatisch generiert |
| `PLN_ALLOWED_HOSTS` | Komma-getrennte Liste erlaubter Host-Header | Automatisch aus Host:Port |

## Beenden

Die Anwendung wird mit `Strg+C` im Terminal beendet.

## Wo werden Daten gespeichert?

- **Datenbank:** `{PLN_DATA_DIR}/private_legal_navigator.db`
- **Dokumente:** `{PLN_DATA_DIR}/documents/`
- **Standard-Datenverzeichnis:** `C:\Users\{Benutzername}\.private-legal-navigator\`

## Datenbanksicherung vor einem Update

```powershell
# Datenbankpfad ermitteln (Standard)
$dbPath = "$env:USERPROFILE\.private-legal-navigator\private_legal_navigator.db"

# Datum für Backup-Name
$date = Get-Date -Format "yyyy-MM-dd"

# Datenbank kopieren
Copy-Item -LiteralPath $dbPath -Destination "$dbPath.backup-$date"
```

## Logs

Die Anwendung loggt auf der Konsole. Es werden keine personenbezogenen
oder fallbezogenen Daten in Logs geschrieben (Privacy-Redaction).

## Rechtlicher Hinweis

Diese Software bietet **keine Rechtsberatung**. Alle Berechnungen
sind unverbindliche Vorschauen. Jede rechtlich relevante Entscheidung
erfordert menschliche Prüfung. Die Anwendung arbeitet **ausschließlich
lokal** und sendet keine Daten an externe Dienste.
