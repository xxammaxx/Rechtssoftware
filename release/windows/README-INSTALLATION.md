# PrivateLegalNavigator — Windows-Installation (v1.0.0-rc.2)

## Voraussetzungen

- **Windows 10 oder neuer** (64-bit)
- **Python 3.11, 3.12, 3.13 oder 3.14** — von https://www.python.org/downloads/
  - Bei Installation: "Add Python to PATH" aktivieren
- **Keine** Administratorrechte erforderlich
- **Keine** Internetverbindung nach der Installation erforderlich

## Schnellstart

1. **ZIP entpacken** — das gesamte Release-ZIP in ein beliebiges Verzeichnis entpacken
2. **PowerShell oeffnen** — im entpackten Verzeichnis `windows\`
3. **Installieren:**
   ```powershell
   .\install.ps1
   ```
4. **Starten:**
   ```powershell
   .\start.ps1
   ```
5. **Browser oeffnet automatisch** → http://127.0.0.1:8000

## Was wird installiert?

| Verzeichnis | Inhalt |
|-------------|--------|
| `%LOCALAPPDATA%\PrivateLegalNavigator\.venv` | Python-Umgebung mit allen Abhaengigkeiten |
| `%LOCALAPPDATA%\PrivateLegalNavigator\data` | Nutzerdaten (Datenbank, Dokumente, Rechtsquellen) |
| `%LOCALAPPDATA%\PrivateLegalNavigator\logs` | Anwendungslogs (keine Falldaten!) |
| Desktop | Verknuepfung "PrivateLegalNavigator" |

## Taegliche Nutzung

### Starten
```powershell
.\start.ps1
```
Oder Desktop-Verknuepfung doppelklicken.

### Beenden
```powershell
.\stop.ps1
```
Oder Browser schliessen (Anwendung laeuft im Hintergrund weiter) und dann `stop.ps1`.

## Backup & Wiederherstellung

### Backup erstellen
```powershell
.\backup.ps1
```
Das Backup ist ein ZIP-Archiv unter `%LOCALAPPDATA%\PrivateLegalNavigator\backups\`.

### Wiederherstellen
```powershell
.\restore.ps1 -BackupPath "PFAD\ZUM\BACKUP.zip"
```
Vorhandene Daten werden vor dem Ueberschreiben gesichert.

## Deinstallation

### Standard (Daten behalten)
```powershell
.\uninstall.ps1
```
Programmdateien und virtuelle Umgebung werden entfernt. Nutzerdaten bleiben erhalten.

### Vollstaendig (Daten loeschen)
```powershell
.\uninstall.ps1 -Purge
```
**WARNUNG:** Alle Faelle, Dokumente und Rechtsquellen-Snapshots werden unwiderruflich geloescht.

## Fehlerbehebung

| Problem | Loesung |
|---------|---------|
| "Python nicht gefunden" | Python 3.11+ von python.org installieren, "Add to PATH" aktivieren |
| "Port 8000 belegt" | Anderen Port in start.ps1 setzen: `-Port 8001` |
| Seite laedt nicht | http://127.0.0.1:8000/health pruefen |
| "Zugriff verweigert" | Powershell als normaler Benutzer starten (nicht als Admin) |
| Backup schlaegt fehlt | Anwendung vor Backup mit stop.ps1 beenden |

## Bekannte Grenzen

- Nur lokale Nutzung (127.0.0.1) — kein Netzwerkzugriff
- Nur PDF-Dokumente (kein OCR fuer gescannte Dokumente)
- Keine verbindliche Rechtsfristberechnung
- Alle Berechnungen sind unverbindliche Vorschauen
- Keine automatische Rechtsberatung
- Rechtsquellen muessen manuell synchronisiert werden
- Keine Cloud-Synchronisierung
- Keine Mehrbenutzer-Unterstuetzung
- Keine Verschluesselung auf Anwendungsebene

## Support

- GitHub: https://github.com/Mueller-Systems-Lab/Rechtssoftware
- Issues: https://github.com/Mueller-Systems-Lab/Rechtssoftware/issues
