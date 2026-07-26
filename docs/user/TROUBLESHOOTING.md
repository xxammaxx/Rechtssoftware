# Fehlerbehebung

**PrivateLegalNavigator v1.0.0-rc.1**

---

## 1. "Python 3.11 oder neuer nicht gefunden"

**Fehlermeldung beim Ausführen von `install.ps1`:**

```
FEHLER: Python 3.11 oder neuer nicht gefunden.
```

**Ursache:** Python ist nicht installiert oder nicht im Systempfad eingetragen.

**Lösung:**

1. Öffnen Sie https://www.python.org/downloads/
2. Laden Sie Python 3.11 oder 3.12 herunter
3. Führen Sie den Installer aus
4. **Wichtig:** Haken Sie bei der Installation **"Add Python to PATH"** an
5. Klicken Sie auf "Install Now"
6. Starten Sie die PowerShell neu und versuchen Sie es erneut

**Prüfen nach der Installation:**

```powershell
py -3.11 --version
```

Sollte etwas wie `Python 3.11.9` anzeigen.

---

## 2. Port 8000 ist bereits belegt

**Fehlermeldung beim Start:**

```
Port 8000 ist bereits belegt:
```

**Ursache:** Ein anderes Programm verwendet bereits den Port 8000.

**Lösung — Möglichkeit A: Belegenes Programm beenden**

1. Finden Sie heraus, welches Programm den Port belegt:
   ```powershell
   netstat -ano | findstr :8000
   ```
2. Notieren Sie die PID (Prozess-ID) aus der letzten Spalte
3. Beenden Sie den Prozess:
   ```powershell
   taskkill /PID <PID> /F
   ```

**Lösung — Möglichkeit B: Anderen Port verwenden**

Setzen Sie die Umgebungsvariable `PLN_PORT`, bevor Sie starten:

```powershell
$env:PLN_PORT = "8080"
.\start.ps1
```

Öffnen Sie dann http://127.0.0.1:8080 im Browser.

---

## 3. App startet nicht / kein Browser öffnet sich

**Problem:** Nach `.\start.ps1` erscheint keine Meldung oder der Browser öffnet sich nicht.

**Lösung:**

1. **Prüfen, ob Python verfügbar ist:**
   ```powershell
   py --version
   ```

2. **Installation prüfen:**
   ```powershell
   & "$env:LOCALAPPDATA\PrivateLegalNavigator\.venv\Scripts\python.exe" -m private_legal_navigator --help
   ```

3. **Log-Datei prüfen:**
   ```powershell
   Get-Content "$env:LOCALAPPDATA\PrivateLegalNavigator\logs\server-*.log"
   ```

4. **Manuelles Starten (für detaillierte Fehlermeldungen):**
   ```powershell
   & "$env:LOCALAPPDATA\PrivateLegalNavigator\.venv\Scripts\python.exe" -m private_legal_navigator serve
   ```

5. **Health-Check testen:**
   Öffnen Sie http://127.0.0.1:8000/health im Browser. Bei Erfolg sehen Sie `{"status":"ok"}`.

---

## 4. Browser öffnet sich, aber Seite lädt nicht

**Problem:** Der Browser öffnet sich, aber die Seite bleibt weiß oder zeigt einen Fehler.

**Lösung:**

1. **Adresse prüfen:** Geben Sie manuell `http://127.0.0.1:8000/health` ein
2. **Server läuft nicht:** Wiederholen Sie den Startvorgang
3. **Cache leeren:** Drücken Sie `Strg + F5` im Browser
4. **Anderen Browser versuchen:** Firefox, Chrome oder Edge

---

## 5. Datenverzeichnis nicht beschreibbar

**Problem:** Die Anwendung kann nicht in das Datenverzeichnis schreiben.

**Ursache:** Das Datenverzeichnis existiert nicht oder hat falsche Berechtigungen.

**Lösung:**

1. **Verzeichnis manuell erstellen:**
   ```powershell
   New-Item -ItemType Directory -Path "$env:LOCALAPPDATA\PrivateLegalNavigator\data" -Force
   ```

2. **Schreibberechtigung prüfen:**
   ```powershell
   Test-Path "$env:LOCALAPPDATA\PrivateLegalNavigator\data"
   ```

3. **Alternatives Datenverzeichnis verwenden:**
   ```powershell
   $env:PLN_DATA_DIR = "D:\MeineDaten\PLN"
   .\start.ps1
   ```

---

## 6. PDF hat keinen Text (leere Textansicht)

**Problem:** Nach dem Hochladen eines PDFs wird kein Text angezeigt.

**Ursache:** Das PDF enthält keine Textschicht. Dies ist typisch für gescannte Dokumente oder Faxe.

**Lösung:**

- Die Anwendung kann nur **digital erstellte PDFs** verarbeiten (z. B. aus Word, Behörden-PDFs mit Text)
- Für **gescannte PDFs** benötigen Sie eine separate OCR-Software
- Alternativ: Kopieren Sie den Text manuell und fügen Sie ihn als Notiz ein

**Prüfen:** Öffnen Sie das PDF in einem PDF-Reader. Können Sie Text markieren und kopieren? Falls nicht, ist es ein gescanntes Dokument.

---

## 7. GII-Synchronisation schlägt fehl

**Problem:** Beim Synchronisieren der Rechtsquellen tritt ein Fehler auf.

**Lösung:**

1. **Internetverbindung prüfen:**
   ```powershell
   Test-NetConnection gesetze-im-internet.de -Port 443
   ```

2. **Fehlermeldung im Detail anzeigen (mit erhöhter Ausführlichkeit):**
   ```powershell
   & "$env:LOCALAPPDATA\PrivateLegalNavigator\.venv\Scripts\python.exe" -m private_legal_navigator legal-source sync --source gii --apply
   ```

3. **Firewall prüfen:** Stellen Sie sicher, dass Ihr Firewall ausgehende Verbindungen zu `gesetze-im-internet.de` auf Port 443 erlaubt.

4. **Bereits vorhandene Daten prüfen:**
   ```powershell
   & "$env:LOCALAPPDATA\PrivateLegalNavigator\.venv\Scripts\python.exe" -m private_legal_navigator legal-source sync-status
   ```

---

## 8. Backup-Fehler

**Problem:** Das Backup-Skript bricht mit einem Fehler ab.

**Lösung:**

1. **Anwendung beenden (für konsistentes Backup):**
   ```powershell
   .\stop.ps1
   ```

2. **Manuelles Backup durchführen:**
   ```powershell
   .\backup.ps1 -BackupDir "D:\TempBackup"
   ```

3. **Speicherplatz prüfen:**
   ```powershell
   Get-PSDrive C | Select-Object Used, Free
   ```

4. **Berechtigungen prüfen:**
   ```powershell
   Test-Path "$env:LOCALAPPDATA\PrivateLegalNavigator"
   ```

---

## 9. Wiederherstellung wird abgelehnt

**Problem:** `restore.ps1` bricht mit einer Fehlermeldung ab.

**Mögliche Ursachen und Lösungen:**

| Fehler | Ursache | Lösung |
|--------|---------|--------|
| "Backup-Datei nicht gefunden" | Falscher Pfad | Korrekten Pfad angeben: `.\restore.ps1 -BackupPath "C:\...\backup.zip"` |
| "Keine gültige ZIP-Datei" | Datei ist beschädigt | Backup erneut erstellen |
| "Kein backup-manifest.json" | Kein gültiges PLN-Backup | Nur PLN-Backups werden unterstützt |
| "Hash-Abweichung" | Datei wurde nachträglich verändert | Backup neu erstellen |
| "Datenverzeichnis enthält bereits Dateien" | Ziel ist nicht leer | Mit `-Force` überschreiben (vorherige Daten werden gesichert) |

---

## 10. Datenbank-Migration schlägt fehl

**Problem:** Nach einem Upgrade startet die Anwendung nicht oder zeigt Datenbankfehler.

**Lösung:**

1. **Fehlermeldung notieren:** Starten Sie die Anwendung manuell, um die vollständige Fehlermeldung zu sehen:
   ```powershell
   & "$env:LOCALAPPDATA\PrivateLegalNavigator\.venv\Scripts\python.exe" -m private_legal_navigator serve
   ```

2. **Backup einspielen:**
   ```powershell
   .\stop.ps1
   .\restore.ps1 -BackupPath "C:\...\letztes-Backup.zip"
   ```

3. **Datenbankdatei prüfen:**
   ```powershell
   Test-Path "$env:LOCALAPPDATA\PrivateLegalNavigator\data\private_legal_navigator.db"
   ```

4. **Bei anhaltenden Problemen:** Deinstallieren Sie die Software (Daten bleiben erhalten) und installieren Sie sie neu. Siehe [UPGRADE.md](UPGRADE.md).

---

## 11. Sonstige Probleme

### Anwendung reagiert nicht

```powershell
.\stop.ps1
.\start.ps1
```

### Nichts hilft

1. Backup erstellen
2. Komplette Deinstallation (Purge) — siehe [UNINSTALL.md](UNINSTALL.md)
3. Neuinstallation
4. Backup wiederherstellen

---

## Log-Dateien zur Diagnose

Die Log-Dateien enthalten detaillierte Informationen zu Fehlern:

```powershell
Get-Content "$env:LOCALAPPDATA\PrivateLegalNavigator\logs\server-*.log"
```

Bei wiederholten Problemen: Speichern Sie die Log-Ausgabe und kontaktieren Sie den Support.
