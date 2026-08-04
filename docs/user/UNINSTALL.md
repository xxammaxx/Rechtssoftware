# Deinstallation

**PrivateLegalNavigator v1.0.0-rc.2**

---

Es gibt zwei Arten der Deinstallation:

| Variante | Programm wird entfernt | Ihre Daten bleiben | Beschreibung |
|----------|----------------------|-------------------|-------------|
| **Standard** | ✅ Ja | ✅ Ja | Nur die Programmdateien werden gelöscht |
| **Purge** | ✅ Ja | ❌ Nein | Alles wird unwiderruflich gelöscht |

---

## Standard-Deinstallation (Daten bleiben erhalten)

Diese Variante entfernt die Programmdateien, behält aber Ihre Fälle, Dokumente und Einstellungen.

### Schritt 1: Anwendung beenden

```powershell
cd C:\Downloads\PrivateLegalNavigator
.\stop.ps1
```

### Schritt 2: Deinstallationsskript ausführen

```powershell
.\uninstall.ps1
```

### Was wird entfernt?

| Entfernt | Nicht entfernt |
|----------|---------------|
| Virtuelle Python-Umgebung (`.venv`) | Ihre Datenbank (`data/`) |
| Log-Dateien (`logs/`) | Ihre hochgeladenen Dokumente |
| Desktop-Verknüpfung | Ihre Backups |
| | Ihre Konfiguration |

### Nach der Deinstallation

Ihre Daten verbleiben unter:

```
%LOCALAPPDATA%\PrivateLegalNavigator\data
```

Bei einer erneuten Installation werden diese Daten automatisch verwendet.

---

## Vollständige Löschung (Purge) — Daten werden gelöscht

Diese Variante entfernt **alle** Dateien — Programm und Daten. Dieser Vorgang ist **endgültig und nicht umkehrbar**.

### Schritt 1: Backup erstellen (empfohlen)

```powershell
.\backup.ps1
```

Falls Sie später doch noch einmal auf Ihre Daten zugreifen möchten.

### Schritt 2: Purge-Deinstallation

```powershell
.\uninstall.ps1 -Purge
```

### Sicherheitsabfrage

Das Skript fordert Sie zur Bestätigung auf:

```
WARNUNG: PURGE-MODUS AKTIV

Alle Falldaten, Dokumente, Rechtsquellen-Snapshots
und die Datenbank werden unwiderruflich gelöscht.
Diese Aktion kann nicht rückgängig gemacht werden.

SIND SIE SICHER? Geben Sie 'LOESCHEN' ein zum Bestätigen:
```

Sie müssen **genau** das Wort `LOESCHEN` eingeben (Großbuchstaben) und mit Enter bestätigen. Bei jeder anderen Eingabe wird der Vorgang abgebrochen.

### Was wird beim Purge gelöscht?

| Gelöscht | Pfad |
|----------|------|
| Programmdateien (virtuelle Umgebung, Logs) | `%LOCALAPPDATA%\PrivateLegalNavigator\.venv\` |
| **Ihre Datenbank** (Fälle, Dokumente, alles) | `%LOCALAPPDATA%\PrivateLegalNavigator\data\` |
| Desktop-Verknüpfung | Desktop |
| Installationsverzeichnis (falls leer) | `%LOCALAPPDATA%\PrivateLegalNavigator\` |

**Nicht gelöscht werden:**

- Backups im Unterordner `backups/` (diese müssen Sie manuell löschen, falls gewünscht)

---

## Nach der Deinstallation

Nach der Standard-Deinstallation können Sie die Software jederzeit neu installieren. Ihre alten Daten werden automatisch erkannt und weiterverwendet.

Nach dem Purge ist eine vollständige Neuinstallation erforderlich. Alle Daten sind dann verloren.

---

## Weitere Informationen

- Vor der Deinstallation ein Backup erstellen: [BACKUP-RESTORE.md](BACKUP-RESTORE.md)
- Upgrade von einer alten Version: [UPGRADE.md](UPGRADE.md)
