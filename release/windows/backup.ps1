# backup.ps1 — PrivateLegalNavigator Backup erstellen
# Nutzt den getesteten Python-Backup-Helper (sqlite3.Connection.backup()).
# Erzeugt ein ZIP-Backup mit Manifest und SHA-256-Pruefsummen.

param(
    [string]$InstallDir = "$env:LOCALAPPDATA\PrivateLegalNavigator",
    [string]$BackupDir = "$env:LOCALAPPDATA\PrivateLegalNavigator\backups"
)

$ErrorActionPreference = "Stop"
$AppName = "PrivateLegalNavigator"
$VenvPython = Join-Path $InstallDir ".venv\Scripts\python.exe"
$DataDir = Join-Path $InstallDir "data"
$PidFile = Join-Path $InstallDir "run\server.json"

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  $AppName — Backup erstellen" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# ——— Pruefe ob Anwendung laeuft (via PID-Datei) ———
if (Test-Path $PidFile) {
    try {
        $pidData = Get-Content $PidFile -Raw | ConvertFrom-Json
        $proc = Get-Process -Id $pidData.pid -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "WARNUNG: $AppName laeuft noch (PID: $($pidData.pid), Instanz: $($pidData.instance_id))." -ForegroundColor Yellow
            Write-Host "Fuer ein konsistentes Backup die Anwendung zuerst mit stop.ps1 beenden." -ForegroundColor Yellow
            Write-Host ""
            Write-Host "Backup trotzdem erzwingen? (j/N)" -ForegroundColor Yellow
            $answer = Read-Host
            if ($answer -notin @("j", "J", "ja", "Ja", "JA", "y", "Y", "yes", "Yes")) {
                Write-Host "Abgebrochen." -ForegroundColor Red
                exit 1
            }
        } else {
            Write-Host "Veraltete PID-Datei gefunden (Prozess laeuft nicht mehr). Fahre fort." -ForegroundColor Yellow
        }
    } catch {
        Write-Host "PID-Datei konnte nicht gelesen werden. Fahre fort." -ForegroundColor Yellow
    }
}

# ——— Pruefe Datenverzeichnis ———
if (-not (Test-Path $DataDir)) {
    Write-Host "Datenverzeichnis nicht gefunden: $DataDir" -ForegroundColor Red
    Write-Host "Wurde die Anwendung bereits installiert und gestartet?" -ForegroundColor Yellow
    exit 1
}

# ——— Python-Venv pruefen ———
if (-not (Test-Path $VenvPython)) {
    Write-Host "Python nicht gefunden: $VenvPython" -ForegroundColor Red
    Write-Host "Wurde die Anwendung installiert?" -ForegroundColor Yellow
    exit 1
}

# ——— Backup-Verzeichnis ———
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
}

# ——— Backup-Name und Arbeitsverzeichnis ———
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupName = "PrivateLegalNavigator-Backup-$timestamp"
$workDir = Join-Path $BackupDir $backupName
New-Item -ItemType Directory -Path $workDir -Force | Out-Null

Write-Host "[1/3] Python-Backup-Helper ausfuehren (SQLite Backup API) ..." -ForegroundColor White
Write-Host "  Datenquelle: $DataDir" -ForegroundColor White
Write-Host "  Ausgabe:     $workDir" -ForegroundColor White

$backupArgs = @(
    "-m", "private_legal_navigator.infrastructure.backup_helper",
    $DataDir,
    $workDir
)
$result = & $VenvPython $backupArgs 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "FEHLER: Backup-Helper fehlgeschlagen:" -ForegroundColor Red
    Write-Host $result -ForegroundColor Red
    Remove-Item $workDir -Recurse -Force -ErrorAction SilentlyContinue
    exit 1
}
Write-Host "  Backup-Helper erfolgreich." -ForegroundColor Green

# ——— Manifest fuer Uebersicht parsen ———
$manifest = Get-Content (Join-Path $workDir "backup-manifest.json") -Raw | ConvertFrom-Json
Write-Host "  DB-Integrity: $($manifest.db_integrity)" -ForegroundColor White
Write-Host "  Dokumente:    $($manifest.document_count)" -ForegroundColor White
Write-Host "  Snapshots:    $($manifest.snapshot_count)" -ForegroundColor White

# ——— ZIP ———
Write-Host "[2/3] ZIP-Archiv erstellen ..." -ForegroundColor White
$zipPath = Join-Path $BackupDir "$backupName.zip"

$prevDir = Get-Location
Set-Location $BackupDir
Compress-Archive -Path $backupName -DestinationPath "$backupName.zip" -Force
Set-Location $prevDir

# Cleanup temp directory
Remove-Item $workDir -Recurse -Force

# ——— SHA-256 ———
Write-Host "[3/3] Pruefsumme berechnen ..." -ForegroundColor White
$zipHash = (Get-FileHash -Path $zipPath -Algorithm SHA256).Hash
$zipSize = (Get-Item $zipPath).Length

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  Backup erstellt!" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Datei:     $zipPath" -ForegroundColor White
Write-Host "  SHA-256:   $zipHash" -ForegroundColor White
Write-Host "  Groesse:   $zipSize Bytes" -ForegroundColor White
Write-Host "  Version:   $($manifest.app_version)" -ForegroundColor White
Write-Host ""
Write-Host "  Wiederherstellen: .\restore.ps1 -BackupPath '$zipPath'" -ForegroundColor Yellow
Write-Host ""
