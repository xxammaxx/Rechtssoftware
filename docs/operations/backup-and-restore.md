# Backup und Restore — PrivateLegalNavigator

## Datensicherung (Backup)

Die Anwendung speichert alle Daten lokal in einer SQLite-Datenbank
und einem Dokumentenverzeichnis.

### Datenpfad ermitteln

Der Standard-Datenpfad ist:

```
C:\Users\{Benutzername}\.private-legal-navigator\
```

Enthält:
- `private_legal_navigator.db` — SQLite-Datenbank (Fälle, Dokumente, Bestätigungen)
- `documents/` — Hochgeladene Dokumente

Der Pfad kann über die Umgebungsvariable `PLN_DATA_DIR` geändert werden.

### Backup erstellen

```powershell
# Anwendung muss gestoppt sein!

$dataDir = "$env:USERPROFILE\.private-legal-navigator"
$backupDir = "$dataDir.backup-$(Get-Date -Format 'yyyy-MM-dd_HHmm')"

# Komplettes Datenverzeichnis sichern
Copy-Item -LiteralPath $dataDir -Destination $backupDir -Recurse

# Prüfsumme erstellen
Get-FileHash -LiteralPath "$backupDir\private_legal_navigator.db" -Algorithm SHA256
```

### Backup-Validierung

Nach dem Backup kann die Prüfsumme zur Integritätsprüfung verwendet werden:

```powershell
Get-FileHash -LiteralPath "$backupDir\private_legal_navigator.db" -Algorithm SHA256
```

## Wiederherstellung (Restore)

### Vollständige Wiederherstellung

```powershell
# Anwendung muss gestoppt sein!

$originalDir = "$env:USERPROFILE\.private-legal-navigator"
$backupDir = "$env:USERPROFILE\.private-legal-navigator.backup-2026-07-22"

# Backup in separates Verzeichnis kopieren (empfohlen)
$restoreDir = "$env:USERPROFILE\.private-legal-navigator.restored"
Copy-Item -LiteralPath $backupDir -Destination $restoreDir -Recurse

# Anwendung mit wiederhergestellten Daten starten
$env:PLN_DATA_DIR = $restoreDir
python -m private_legal_navigator
```

### Teilweise Wiederherstellung

Nur die Datenbank wiederherstellen:

```powershell
# Anwendung stoppen
# Datenbank ersetzen
Copy-Item -LiteralPath "$backupDir\private_legal_navigator.db" `
          -Destination "$originalDir\private_legal_navigator.db" -Force
# Anwendung starten
```

## Wichtige Hinweise

- **Backup nur bei gestoppter Anwendung** — eine laufende Anwendung
  kann die Datenbank geöffnet haben.
- **Keine Bearbeitung der Datenbank** — direkte SQL-Änderungen an der
  Datenbank können zu Inkonsistenzen führen.
- **Keine produktiven Benutzerdaten** — die Testdaten tragen das
  Präfix "SYNTHETISCH –".
- **Daten bleiben lokal** — Backups enthalten potenziell sensible
  Daten und sollten sicher aufbewahrt werden.
