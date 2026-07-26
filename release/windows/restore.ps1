# restore.ps1 — PrivateLegalNavigator Backup wiederherstellen
# Validiert SHA-256-Hashes und laesst bestehende Daten nicht ungefragt ueberschreiben.

param(
    [Parameter(Mandatory=$true)]
    [string]$BackupPath,
    [string]$DataDir = "$env:LOCALAPPDATA\PrivateLegalNavigator\data",
    [switch]$Force = $false
)

$ErrorActionPreference = "Stop"
$AppName = "PrivateLegalNavigator"

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  $AppName — Backup wiederherstellen" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# ——— Backup existiert? ———
if (-not (Test-Path $BackupPath)) {
    Write-Host "FEHLER: Backup-Datei nicht gefunden: $BackupPath" -ForegroundColor Red
    exit 1
}

# ——— Arbeitsverzeichnis ———
$workDir = "$env:TEMP\pln-restore-$(Get-Date -Format 'yyyyMMddHHmmss')"
New-Item -ItemType Directory -Path $workDir -Force | Out-Null

# ——— Entpacken ———
Write-Host "[1/6] Backup entpacken ..." -ForegroundColor White
try {
    Expand-Archive -Path $BackupPath -DestinationPath $workDir -Force
    Write-Host "  Entpackt nach: $workDir" -ForegroundColor Green
} catch {
    Write-Host "  FEHLER: Backup-Datei ist kein gueltiges ZIP-Archiv." -ForegroundColor Red
    Remove-Item $workDir -Recurse -Force -ErrorAction SilentlyContinue
    exit 1
}

# ——— Manifest pruefen ———
Write-Host "[2/6] Manifest validieren ..." -ForegroundColor White
$manifestPath = Join-Path $workDir "backup-manifest.json"
if (-not (Test-Path $manifestPath)) {
    Write-Host "  FEHLER: Kein backup-manifest.json im Backup gefunden." -ForegroundColor Red
    Remove-Item $workDir -Recurse -Force -ErrorAction SilentlyContinue
    exit 1
}

$manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json
Write-Host "  App-Version: $($manifest.app_version)" -ForegroundColor White
Write-Host "  Erstellt:    $($manifest.created_at)" -ForegroundColor White

# ——— SHA-256 pruefen ———
Write-Host "[3/6] Datei-Integritaet pruefen ..." -ForegroundColor White
$allValid = $true
foreach ($file in $manifest.files) {
    $filePath = Join-Path $workDir $file.path
    if (-not (Test-Path $filePath)) {
        Write-Host "  FEHLER: Datei fehlt im Backup: $($file.path)" -ForegroundColor Red
        $allValid = $false
        continue
    }
    $actualHash = (Get-FileHash -Path $filePath -Algorithm SHA256).Hash
    if ($actualHash -ne $file.sha256) {
        Write-Host "  FEHLER: Hash-Abweichung bei $($file.path)" -ForegroundColor Red
        Write-Host "    Erwartet:  $($file.sha256)" -ForegroundColor Red
        Write-Host "    Berechnet: $actualHash" -ForegroundColor Red
        $allValid = $false
    }
}

if (-not $allValid) {
    Write-Host "  Backup ist beschaedigt oder manipuliert. Wiederherstellung abgebrochen." -ForegroundColor Red
    Remove-Item $workDir -Recurse -Force -ErrorAction SilentlyContinue
    exit 1
}
Write-Host "  Alle $($manifest.files.Count) Dateien gueltig." -ForegroundColor Green

# ——— Zielpruefung ———
Write-Host "[4/6] Zielverzeichnis pruefen ..." -ForegroundColor White
if (Test-Path $DataDir) {
    $existingFiles = Get-ChildItem $DataDir -Recurse -File -ErrorAction SilentlyContinue
    if ($existingFiles.Count -gt 0 -and -not $Force) {
        Write-Host "  WARNUNG: Datenverzeichnis enthaelt bereits $($existingFiles.Count) Dateien." -ForegroundColor Yellow
        Write-Host "  Eine Wiederherstellung wuerde diese Daten ueberschreiben." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "  Fortfahren? Vorhandene Daten werden zuvor gesichert. (j/N)" -ForegroundColor Yellow
        $answer = Read-Host
        if ($answer -notin @("j", "J", "ja", "Ja", "JA", "y", "Y", "yes", "Yes")) {
            Write-Host "  Abgebrochen." -ForegroundColor Red
            Remove-Item $workDir -Recurse -Force -ErrorAction SilentlyContinue
            exit 1
        }
    }
}

# ——— Vorhandene Daten sichern ———
Write-Host "[5/6] Vorhandene Daten sichern ..." -ForegroundColor White
if (Test-Path $DataDir) {
    $safetyDir = "$DataDir.pre-restore-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Move-Item $DataDir $safetyDir -Force
    Write-Host "  Vorhandene Daten verschoben nach: $safetyDir" -ForegroundColor Green
}

# ——— Wiederherstellen ———
Write-Host "[6/6] Daten wiederherstellen ..." -ForegroundColor White
$srcFiles = Get-ChildItem $workDir -Exclude "backup-manifest.json" | Where-Object { $_.Name -ne "backup-manifest.json" }

# Sicherstellen dass DataDir existiert
New-Item -ItemType Directory -Path $DataDir -Force | Out-Null

foreach ($item in $srcFiles) {
    $dest = Join-Path $DataDir $item.Name
    if (Test-Path $item.FullName) {
        Copy-Item $item.FullName $dest -Recurse -Force
    }
}
Write-Host "  Daten wiederhergestellt in: $DataDir" -ForegroundColor Green

# ——— Aufraeumen ———
Remove-Item $workDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  Wiederherstellung abgeschlossen!" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Datenverzeichnis: $DataDir" -ForegroundColor White
Write-Host "  Anwendung starten: .\start.ps1" -ForegroundColor Yellow
Write-Host ""
