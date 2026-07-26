# Installationsanleitung für Windows

**PrivateLegalNavigator v1.0.0-rc.1**

Diese Anleitung beschreibt die Installation auf Windows 10 oder neuer.

---

## Voraussetzungen

- **Betriebssystem:** Windows 10 oder Windows 11
- **Python:** Version 3.11, 3.12, 3.13 oder 3.14
- **Internetverbindung:** Nur für den Download erforderlich

### Python installieren (falls nicht vorhanden)

1. Öffnen Sie https://www.python.org/downloads/ in Ihrem Browser
2. Laden Sie Python 3.11 oder 3.12 herunter
3. Führen Sie den Installer aus
4. **Wichtig:** Haken Sie bei der Installation **"Add Python to PATH"** an
5. Klicken Sie auf "Install Now"

Nach der Installation können Sie mit folgendem Befehl im Terminal prüfen, ob Python verfügbar ist:

```
py -3.11 --version
```

---

## Installation

### Schritt 1: Release herunterladen

1. Öffnen Sie die GitHub-Releases-Seite des Projekts
2. Laden Sie die neueste `PrivateLegalNavigator-v1.0.0-rc.1.zip` herunter
3. Entpacken Sie das ZIP-Archiv in einen Ordner Ihrer Wahl (z. B. `C:\Downloads\PrivateLegalNavigator`)

Das entpackte Verzeichnis enthält:
- `install.ps1` — Installationsskript
- `start.ps1` — Startskript
- `stop.ps1` — Stoppskript
- `backup.ps1` — Backup-Skript
- `restore.ps1` — Wiederherstellungsskript
- `uninstall.ps1` — Deinstallationsskript
- `private_legal_navigator-1.0.0rc1-py3-none-any.whl` — Das Installationspaket

### Schritt 2: PowerShell öffnen

1. Drücken Sie `Windows-Taste`, tippen Sie `PowerShell`
2. Klicken Sie mit der rechten Maustaste auf "Windows PowerShell" und wählen Sie **"Als Administrator ausführen"**

   > **Hinweis:** Administratorrechte sind nicht erforderlich, aber falls Sie Probleme mit Ausführungsrichtlinien haben, können Sie im Administratormodus fortfahren.

### Schritt 3: Installationsskript ausführen

Wechseln Sie in das Verzeichnis mit den entpackten Dateien:

```powershell
cd C:\Downloads\PrivateLegalNavigator
```

Führen Sie die Installation aus:

```powershell
.\install.ps1
```

Das Skript durchläuft 7 Schritte automatisch:

| Schritt | Beschreibung |
|---------|-------------|
| 1/7 | Python finden |
| 2/7 | Release-Paket finden |
| 3/7 | Installationsverzeichnis vorbereiten |
| 4/7 | Virtuelle Umgebung erstellen |
| 5/7 | Package installieren |
| 6/7 | Abhängigkeiten prüfen |
| 7/7 | Datenverzeichnis vorbereiten |

Nach erfolgreicher Installation erhalten Sie eine Zusammenfassung mit Installations- und Datenverzeichnis.

---

## Installationsverzeichnis

Die Software wird installiert nach:

```
%LOCALAPPDATA%\PrivateLegalNavigator
```

Dies entspricht in der Regel:

```
C:\Benutzer\<IhrBenutzername>\AppData\Local\PrivateLegalNavigator
```

| Inhalt | Pfad |
|--------|------|
| Programmdateien | `%LOCALAPPDATA%\PrivateLegalNavigator\.venv\` |
| Daten (Datenbank, Dokumente) | `%LOCALAPPDATA%\PrivateLegalNavigator\data\` |
| Logs | `%LOCALAPPDATA%\PrivateLegalNavigator\logs\` |
| Backups | `%LOCALAPPDATA%\PrivateLegalNavigator\backups\` |

---

## Nach der Installation

Starten Sie die Anwendung mit:

```powershell
.\start.ps1
```

Die Anwendung öffnet automatisch Ihren Browser unter http://127.0.0.1:8000.

Ausführliche Informationen zum ersten Start finden Sie in der Anleitung [FIRST-START.md](FIRST-START.md).

---

## Optionen für die Installation

Sie können das Installationsskript mit Parametern anpassen:

```powershell
# Anderes Installationsverzeichnis
.\install.ps1 -InstallDir "D:\MeineProgramme\PrivateLegalNavigator"

# Keine Desktop-Verknüpfung erstellen
.\install.ps1 -CreateDesktopShortcut:$false

# Bestimmtes Wheel-Paket verwenden
.\install.ps1 -WheelPath "C:\Downloads\private_legal_navigator-1.0.0rc1-py3-none-any.whl"
```

---

## Fehlerbehebung bei der Installation

| Problem | Lösung |
|---------|--------|
| "Python 3.11 oder neuer nicht gefunden" | Python von python.org installieren, "Add Python to PATH" aktivieren |
| "Wheel-Datei nicht gefunden" | Prüfen, ob das ZIP vollständig entpackt wurde |
| Installation fehlgeschlagen | Fehlermeldung notieren, Log prüfen, erneut versuchen |

Siehe auch [TROUBLESHOOTING.md](TROUBLESHOOTING.md) für weitere Hilfe.

---

## Keine Administratorrechte nötig

Die Installation erfolgt vollständig im Benutzerverzeichnis. Es werden keine systemweiten Änderungen vorgenommen. Alle Dateien liegen unter `%LOCALAPPDATA%\PrivateLegalNavigator`.
