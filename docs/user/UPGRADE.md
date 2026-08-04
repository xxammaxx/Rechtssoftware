# Upgrade von v0.2.x auf v1.0.0-rc.2

**PrivateLegalNavigator v1.0.0-rc.2**

---

## Wichtige Änderungen

| Aspekt | Vorher (v0.2.x) | Neu (v1.0.0-rc.2) |
|--------|-----------------|-------------------|
| Python | 3.9+ | **3.11+** |
| Datenverzeichnis | `~/.private-legal-navigator` | `%LOCALAPPDATA%\PrivateLegalNavigator\data` |
| Installation | Manuell via `pip install` | Installationsskript `install.ps1` |
| Bindung | `127.0.0.1` (konfigurierbar) | `127.0.0.1` (Standard, nur lokal) |

---

## Upgrade-Schritte

### Schritt 1: Daten sichern (unbedingt!)

Führen Sie vor dem Upgrade ein Backup durch:

```powershell
cd C:\Pfad\zur\alten\Installation
.\stop.ps1
.\backup.ps1
```

Notieren Sie sich den Pfad der erstellten Backup-Datei.

> **Ohne Backup kein Upgrade:** Sollte etwas schiefgehen, können Sie mit dem Backup jederzeit zum alten Stand zurückkehren.

### Schritt 2: Python 3.11+ installieren (falls nicht vorhanden)

Die neue Version benötigt Python 3.11, 3.12, 3.13 oder 3.14. Prüfen Sie Ihre Version:

```powershell
py --version
```

Liegt Ihre Version unter 3.11, installieren Sie Python von:

https://www.python.org/downloads/

Aktivieren Sie bei der Installation **"Add Python to PATH"**.

### Schritt 3: Installationsskript ausführen

Laden Sie das Release-ZIP der neuen Version herunter und entpacken Sie es.

Führen Sie das neue Installationsskript aus:

```powershell
cd C:\Downloads\PrivateLegalNavigator_v1.0.0-rc.2
.\install.ps1
```

Das Installationsskript ist **idempotent** — es kann mehrfach ausgeführt werden, ohne bestehende Daten zu beschädigen.

### Schritt 4: Alte Daten migrieren (falls nötig)

Das Installationsskript legt ein neues Datenverzeichnis an unter:

```
%LOCALAPPDATA%\PrivateLegalNavigator\data
```

Wenn Ihre alten Daten noch im bisherigen Verzeichnis (`~/.private-legal-navigator`) liegen, gehen Sie wie folgt vor:

1. Kopieren Sie den Inhalt des alten Datenverzeichnisses in das neue:
   ```powershell
   Copy-Item "$env:USERPROFILE\.private-legal-navigator\*" "$env:LOCALAPPDATA\PrivateLegalNavigator\data\" -Recurse
   ```

2. Oder stellen Sie die Umgebungsvariable `PLN_DATA_DIR` auf Ihr altes Verzeichnis:
   ```powershell
   $env:PLN_DATA_DIR = "$env:USERPROFILE\.private-legal-navigator"
   .\start.ps1
   ```

### Schritt 5: Anwendung starten

```powershell
.\start.ps1
```

Die Datenbank wird beim ersten Start **automatisch migriert**. Dieser Vorgang ist nicht sichtbar — die Anwendung startet direkt.

> **Hinweis:** Die Migration ist irreversibel. Nach dem Start mit der neuen Version kann die Datenbank nicht mehr mit der alten Version verwendet werden. Ein vorheriges Backup ist daher wichtig.

---

## Nach dem Upgrade

### Verifizierung

1. Öffnen Sie http://127.0.0.1:8000/ui/cases
2. Prüfen Sie, ob alle Ihre Fälle noch vorhanden sind
3. Öffnen Sie einen Fall und prüfen Sie die Dokumente
4. Testen Sie die Rechtsquellenseite unter `/ui/legal-sources`

### Version prüfen

Die Version wird auf der Startseite oder über die Health-Seite angezeigt:

```
http://127.0.0.1:8000/health
```

---

## Fehlerbehebung beim Upgrade

| Problem | Lösung |
|---------|--------|
| "Python 3.11+ nicht gefunden" | Python 3.11+ installieren |
| Daten nach Upgrade nicht sichtbar | Prüfen, ob `PLN_DATA_DIR` richtig gesetzt ist |
| Alte Version startet noch | `.\stop.ps1` ausführen, dann neue starten |
| Datenbank-Fehler nach Start | Backup einspielen und Fehler melden |
| Desktop-Verknüpfung fehlt | Wird vom Installationsskript neu erstellt |

Siehe auch [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

---

## Rückkehr zur alten Version

Falls Sie zur alten Version zurückkehren möchten:

1. Neue Installation deinstallieren (siehe [UNINSTALL.md](UNINSTALL.md))
2. Backup mit `restore.ps1` einspielen (siehe [BACKUP-RESTORE.md](BACKUP-RESTORE.md))
3. Alte Version starten

**Wichtig:** Die Datenbankmigration ist nicht umkehrbar. Sie müssen das vor dem Upgrade erstellte Backup verwenden.
