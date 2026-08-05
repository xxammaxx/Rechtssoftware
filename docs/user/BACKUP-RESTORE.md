# Backup und Wiederherstellung

**PrivateLegalNavigator v1.0.0-rc.2**

---

## Warum Backups wichtig sind

Ihre Daten (Fälle, Dokumente, Notizen, verknüpfte Gesetze) werden lokal auf Ihrem Computer gespeichert. Ein regelmäßiges Backup schützt vor Datenverlust durch:

- Festplattenfehler
- Versehentliches Löschen
- Fehlerhafte Updates
- Sonstige technische Probleme

---

## Backup erstellen

### Schritt 1: Anwendung beenden

Stellen Sie sicher, dass die Anwendung nicht läuft:

```powershell
cd C:\Downloads\PrivateLegalNavigator
.\stop.ps1
```

> **Hinweis:** Ein Backup ist auch bei laufender Anwendung möglich. Das Skript warnt Sie dann und fragt nach, ob Sie trotzdem fortfahren möchten. Für ein konsistentes Backup empfehlen wir, die Anwendung vorher zu beenden.

### Schritt 2: Backup-Skript ausführen

```powershell
.\backup.ps1
```

Das Skript durchläuft 4 Schritte:

| Schritt | Beschreibung |
|---------|-------------|
| 1/4 | Datenbank sichern (die SQLite-Datenbankdatei) |
| 2/4 | Dokumente und Snapshots sichern (hochgeladene PDFs, Gesetzeskopien) |
| 3/4 | Manifest und Prüfsummen erstellen (SHA-256-Hashes aller Dateien) |
| 4/4 | ZIP-Archiv erstellen |

### Ergebnis

Nach erfolgreichem Backup erhalten Sie:

```
Backup erstellt!
  Datei:     %LOCALAPPDATA%\PrivateLegalNavigator\backups\PrivateLegalNavigator-Backup-20260325-143022.zip
  SHA-256:   3a7b...f9e1
  Größe:     12345678 Bytes
```

Das Backup liegt als ZIP-Datei mit folgendem Inhalt:

- `private_legal_navigator.db` — Ihre Datenbank
- `documents/` — Ihre hochgeladenen PDF-Dokumente
- `snapshots/` — Kopien der heruntergeladenen Gesetze
- `backup-manifest.json` — Prüfsummen-Manifest

### Backup-Speicherort

Standardmäßig werden Backups gespeichert unter:

```
%LOCALAPPDATA%\PrivateLegalNavigator\backups\
```

Dies entspricht: `C:\Benutzer\<IhrBenutzername>\AppData\Local\PrivateLegalNavigator\backups\`

### Eigenes Backup-Verzeichnis

```powershell
.\backup.ps1 -BackupDir "D:\MeineSicherungen\PLN"
```

---

## Backup wiederherstellen

### Schritt 1: Anwendung beenden

```powershell
.\stop.ps1
```

### Schritt 2: Wiederherstellung starten

```powershell
.\restore.ps1 -BackupPath "C:\Users\<IhrName>\AppData\Local\PrivateLegalNavigator\backups\PrivateLegalNavigator-Backup-20260325-143022.zip"
```

### Ablauf der Wiederherstellung

| Schritt | Beschreibung |
|---------|-------------|
| 1/6 | ZIP-Archiv entpacken |
| 2/6 | Manifest validieren (Prüfung auf Vollständigkeit) |
| 3/6 | SHA-256-Prüfsummen aller Dateien verifizieren |
| 4/6 | Zielverzeichnis prüfen (vorhandene Daten erkennen) |
| 5/6 | Vorhandene Daten sichern (als `.pre-restore-...` Ordner) |
| 6/6 | Daten aus dem Backup wiederherstellen |

### Wichtige Hinweise zur Wiederherstellung

1. **Vorhandene Daten werden gesichert:** Ihre aktuellen Daten werden vor der Wiederherstellung automatisch in einen Ordner mit dem Namen `data.pre-restore-20260325-143022` verschoben.
2. **Integritätsprüfung:** Jede Datei wird anhand ihres SHA-256-Hashs überprüft. Bei Abweichungen wird die Wiederherstellung abgebrochen.
3. **Bestätigung erforderlich:** Wenn bereits Daten vorhanden sind, werden Sie gefragt, ob Sie fortfahren möchten.

### Wiederherstellung ohne Nachfrage

Falls Sie die Wiederherstellung vollautomatisch durchführen möchten:

```powershell
.\restore.ps1 -BackupPath "..." -Force
```

> Vorsicht: Mit `-Force` überspringen Sie die Sicherheitsabfrage.

---

## SHA-256-Prüfsumme

Jedes Backup enthält eine SHA-256-Prüfsumme für jede enthaltene Datei. Diese Prüfsumme wird bei der Wiederherstellung automatisch verifiziert. So wird sichergestellt:

- Keine Datei wurde versehentlich beschädigt
- Keine Datei wurde manipuliert
- Das Backup ist vollständig

---

## Backup-Strategie (Empfehlung)

| Intervall | Aktion |
|-----------|--------|
| Nach jeder Arbeitssitzung | Backup erstellen |
| Vor jedem Update | Backup erstellen (siehe [UPGRADE.md](UPGRADE.md)) |
| Wöchentlich | Backup auf externem Datenträger sichern |
| Monatlich | Ältere Backups aufräumen |

---

## Tipps

- **Backups sind portabel:** Sie können ein Backup auf einen USB-Stick kopieren oder in der Cloud speichern.
- **Backups sind unabhängig:** Jedes Backup ist ein vollständiges ZIP-Archiv — Sie brauchen keine anderen Dateien.
- **Benennen Sie Backups nicht um:** Das Wiederherstellungsskript erwartet die korrekte Ordnerstruktur im ZIP.
