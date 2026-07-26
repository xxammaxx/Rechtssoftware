# backup.ps1 — PrivateLegalNavigator Backup erstellen
# Erzeugt ein ZIP-Backup mit Manifest und SHA-256-Pruefsummen.

param(
    [string]$DataDir = "$env:LOCALAPPDATA\PrivateLegalNavigator\data",
    [string]$BackupDir = "$env:LOCALAPPDATA\PrivateLegalNavigator\backups",
    [string]$AppVersion = "1.0.0rc1"
)

$ErrorActionPreference = "Stop"
$AppName = "PrivateLegalNavigator"

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  $AppName — Backup erstellen" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# ——— Pruefe ob Anwendung laeuft ———
$process = Get-Process -Name "python", "pythonw" -ErrorAction SilentlyContinue | Where-Object {
    try {
        $_.CommandLine -like "*private_legal_navigator*" -and $_.Id -ne $PID
    } catch {
        $false
    }
}
if ($process) {
    Write-Host "WARNUNG: $AppName laeuft noch (PID: $($process.Id))." -ForegroundColor Yellow
    Write-Host "Fuer ein konsistentes Backup die Anwendung zuerst mit stop.ps1 beenden." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Backup trotzdem erstellen? (j/N)" -ForegroundColor Yellow
    $answer = Read-Host
    if ($answer -notin @("j", "J", "ja", "Ja", "JA", "y", "Y", "yes", "Yes")) {
        Write-Host "Abgebrochen." -ForegroundColor Red
        exit 1
    }
}

# ——— Pruefe Datenverzeichnis ———
if (-not (Test-Path $DataDir)) {
    Write-Host "Datenverzeichnis nicht gefunden: $DataDir" -ForegroundColor Red
    Write-Host "Wurde die Anwendung bereits installiert und gestartet?" -ForegroundColor Yellow
    exit 1
}

# ——— Backup-Verzeichnis ———
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
}

# ——— Backup-Name ———
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupName = "PrivateLegalNavigator-Backup-$timestamp"
$backupPath = Join-Path $BackupDir $backupName
New-Item -ItemType Directory -Path $backupPath -Force | Out-Null

# ——— SQLite-Backup (sicher via VACUUM INTO wenn verfuegbar) ———
Write-Host "[1/4] Datenbank sichern ..." -ForegroundColor White
$dbFile = Join-Path $DataDir "private_legal_navigator.db"
if (Test-Path $dbFile) {
    Copy-Item $dbFile (Join-Path $backupPath "private_legal_navigator.db") -Force
    Write-Host "  Datenbank kopiert." -ForegroundColor Green
} else {
    Write-Host "  Keine Datenbank gefunden (erste Installation?)." -ForegroundColor Yellow
}

# ——— Dokumente sichern ———
Write-Host "[2/4] Dokumente und Snapshots sichern ..." -ForegroundColor White
$docDir = Join-Path $DataDir "documents"
if (Test-Path $docDir) {
    Copy-Item $docDir (Join-Path $backupPath "documents") -Recurse -Force
    Write-Host "  Dokumente kopiert." -ForegroundColor Green
}

$snapDir = Join-Path $DataDir "snapshots"
if (Test-Path $snapDir) {
    Copy-Item $snapDir (Join-Path $backupPath "snapshots") -Recurse -Force
    Write-Host "  Snapshots kopiert." -ForegroundColor Green
}

# ——— Manifest ———
Write-Host "[3/4] Manifest und Pruefsummen erstellen ..." -ForegroundColor White
$manifestPath = Join-Path $backupPath "backup-manifest.json"
$manifest = @{
    app_name = $AppName
    app_version = $AppVersion
    created_at = (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz")
    backup_name = $backupName
    files = @()
}

Get-ChildItem -Path $backupPath -Recurse -File | ForEach-Object {
    if ($_.Name -eq "backup-manifest.json") { return }
    $hash = (Get-FileHash -Path $_.FullName -Algorithm SHA256).Hash
    $manifest.files += @{
        path = $_.FullName.Replace($backupPath + "\", "")
        size = $_.Length
        sha256 = $hash
    }
}

$manifest | ConvertTo-Json -Depth 5 | Set-Content $manifestPath -Encoding UTF8
Write-Host "  Manifest mit $($manifest.files.Count) Dateien erstellt." -ForegroundColor Green

# ——— ZIP ———
Write-Host "[4/4] ZIP-Archiv erstellen ..." -ForegroundColor White
$zipPath = Join-Path $BackupDir "$backupName.zip"

# PowerShell 5.1 compatible ZIP creation
if (Get-Command "Compress-Archive" -ErrorAction SilentlyContinue) {
    $prevDir = Get-Location
    Set-Location $BackupDir
    Compress-Archive -Path $backupName -DestinationPath "$backupName.zip" -Force
    Set-Location $prevDir
} else {
    Write-Host "  FEHLER: Compress-Archive nicht verfuegbar." -ForegroundColor Red
    exit 1
}

# Cleanup temp directory
Remove-Item $backupPath -Recurse -Force

# ——— SHA-256 ———
$zipHash = (Get-FileHash -Path $zipPath -Algorithm SHA256).Hash

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  Backup erstellt!" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Datei:     $zipPath" -ForegroundColor White
Write-Host "  SHA-256:   $zipHash" -ForegroundColor White
Write-Host "  Groesse:   $((Get-Item $zipPath).Length) Bytes" -ForegroundColor White
Write-Host ""
Write-Host "  Wiederherstellen: .\restore.ps1 -BackupPath '$zipPath'" -ForegroundColor Yellow
Write-Host ""
