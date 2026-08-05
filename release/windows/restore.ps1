# restore.ps1 — PrivateLegalNavigator Backup wiederherstellen
# Nutzt den getesteten Python-Restore-Helper mit ZIP-Pre-Validation.
# Blockiert Path-Traversal, Symlinks und absolute Pfade VOR der Extraktion.
# Fuehrt atomaren Staging-to-Target-Wechsel mit Rollback durch.

param(
    [Parameter(Mandatory=$true)]
    [string]$BackupPath,
    [string]$InstallDir = "$env:LOCALAPPDATA\PrivateLegalNavigator",
    [switch]$Force = $false
)

$ErrorActionPreference = "Stop"
$AppName = "PrivateLegalNavigator"
$VenvPython = Join-Path $InstallDir ".venv\Scripts\python.exe"
$DataDir = Join-Path $InstallDir "data"

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  $AppName — Backup wiederherstellen" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# ——— Backup existiert? ———
if (-not (Test-Path $BackupPath)) {
    Write-Host "FEHLER: Backup-Datei nicht gefunden: $BackupPath" -ForegroundColor Red
    exit 1
}

# ——— Python-Venv pruefen ———
if (-not (Test-Path $VenvPython)) {
    Write-Host "FEHLER: Python nicht gefunden: $VenvPython" -ForegroundColor Red
    Write-Host "Wurde die Anwendung installiert?" -ForegroundColor Yellow
    exit 1
}

# ——— Pruefe ob Anwendung laeuft (via PID-Datei) ———
$PidFile = Join-Path $InstallDir "run\server.json"
if (Test-Path $PidFile) {
    try {
        $pidData = Get-Content $PidFile -Raw | ConvertFrom-Json
        $proc = Get-Process -Id $pidData.pid -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "WARNUNG: $AppName laeuft noch (PID: $($pidData.pid))." -ForegroundColor Yellow
            Write-Host "Bitte zuerst stop.ps1 ausfuehren, dann restore.ps1." -ForegroundColor Yellow
            Write-Host ""
            Write-Host "Restore trotzdem erzwingen? (j/N)" -ForegroundColor Yellow
            $answer = Read-Host
            if ($answer -notin @("j", "J", "ja", "Ja", "JA", "y", "Y", "yes", "Yes")) {
                Write-Host "Abgebrochen." -ForegroundColor Red
                exit 1
            }
        }
    } catch {
        # PID file unreadable — proceed with caution
    }
}

# ——— Zielpruefung (vor Python-Aufruf, damit wir frueh abbrechen koennen) ———
if ((Test-Path $DataDir) -and -not $Force) {
    $existingFiles = Get-ChildItem $DataDir -Recurse -File -ErrorAction SilentlyContinue
    if ($existingFiles -and $existingFiles.Count -gt 0) {
        Write-Host "WARNUNG: Datenverzeichnis enthaelt bereits $($existingFiles.Count) Dateien." -ForegroundColor Yellow
        Write-Host "  $DataDir" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Fortfahren? Bestehende Daten werden vor der Wiederherstellung gesichert. (j/N)" -ForegroundColor Yellow
        $answer = Read-Host
        if ($answer -notin @("j", "J", "ja", "Ja", "JA", "y", "Y", "yes", "Yes")) {
            Write-Host "Abgebrochen." -ForegroundColor Red
            exit 1
        }
    }
}

# ——— Python-Restore-Helper ausfuehren (ZIP-Validation + Restore) ———
Write-Host ""
Write-Host "[*] Python-Restore-Helper ausfuehren (ZIP-Pre-Validation + atomarer Restore) ..." -ForegroundColor White
Write-Host "  Backup: $BackupPath" -ForegroundColor White
Write-Host "  Ziel:   $DataDir" -ForegroundColor White

$restoreArgs = @(
    "-m", "private_legal_navigator.infrastructure.restore_helper",
    $BackupPath,
    $DataDir
)
if ($Force) {
    $restoreArgs += "--force"
}

$result = & $VenvPython $restoreArgs 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "FEHLER: Wiederherstellung fehlgeschlagen:" -ForegroundColor Red
    Write-Host $result -ForegroundColor Red
    Write-Host ""
    Write-Host "WICHTIG: Ein fehlgeschlagener Restore hinterlaesst KEINE teilweise aktualisierten Daten." -ForegroundColor Yellow
    Write-Host "Bestehende Daten wurden NICHT ueberschrieben." -ForegroundColor Yellow
    exit 1
}

Write-Host "  Restore-Helper erfolgreich." -ForegroundColor Green
Write-Host ""

# ——— Ergebnis anzeigen ———
try {
    $restoreResult = $result | ConvertFrom-Json
    Write-Host "=============================================" -ForegroundColor Cyan
    Write-Host "  Wiederherstellung abgeschlossen!" -ForegroundColor Green
    Write-Host "=============================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  App-Version:    $($restoreResult.app_version)" -ForegroundColor White
    Write-Host "  Schema-Version: $($restoreResult.schema_version)" -ForegroundColor White
    Write-Host "  DB-Integrity:   $($restoreResult.db_integrity)" -ForegroundColor White
    Write-Host "  Dokumente:      $($restoreResult.document_count)" -ForegroundColor White
    Write-Host "  Snapshots:      $($restoreResult.snapshot_count)" -ForegroundColor White
    Write-Host "  Backup-Datum:   $($restoreResult.created_at)" -ForegroundColor White
    Write-Host ""
    Write-Host "  Datenverzeichnis: $DataDir" -ForegroundColor White
    Write-Host "  Anwendung starten: .\start.ps1" -ForegroundColor Yellow
    Write-Host ""
} catch {
    Write-Host "Wiederherstellung erfolgreich, konnte Ergebnis aber nicht parsen." -ForegroundColor Yellow
    Write-Host "Datenverzeichnis: $DataDir" -ForegroundColor White
    Write-Host "Anwendung starten: .\start.ps1" -ForegroundColor Yellow
}
