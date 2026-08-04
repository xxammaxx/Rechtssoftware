# uninstall.ps1 — PrivateLegalNavigator deinstallieren
# Behaelt Nutzerdaten standardmaessig. Optionaler Purge-Modus loescht Daten.

param(
    [string]$InstallDir = "$env:LOCALAPPDATA\PrivateLegalNavigator",
    [switch]$Purge = $false,
    [switch]$Force = $false
)

$ErrorActionPreference = "Stop"
$AppName = "PrivateLegalNavigator"

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  $AppName — Deinstallation" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

$DataDir = Join-Path $InstallDir "data"

# ——— Anwendung zuerst stoppen ———
Write-Host "[1/4] Anwendung beenden ..." -ForegroundColor White
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$stopScript = Join-Path $ScriptDir "stop.ps1"
if (Test-Path $stopScript) {
    & $stopScript
} else {
    # Direkt beenden
    $process = Get-Process -Name "python", "pythonw" -ErrorAction SilentlyContinue | Where-Object {
        try { $_.CommandLine -like "*private_legal_navigator*" -and $_.Id -ne $PID } catch { $false }
    }
    if ($process) {
        $process | Stop-Process -Force
    }
}
Write-Host "  Anwendung beendet." -ForegroundColor Green

# ——— Installationsverzeichnis entfernen ———
Write-Host "[2/4] Programmdateien entfernen ..." -ForegroundColor White
$VenvDir = Join-Path $InstallDir ".venv"
$LogDir = Join-Path $InstallDir "logs"
$RunDir = Join-Path $InstallDir "run"

if (Test-Path $VenvDir) {
    Remove-Item $VenvDir -Recurse -Force
    Write-Host "  Virtuelle Umgebung entfernt." -ForegroundColor Green
}
if (Test-Path $LogDir) {
    Remove-Item $LogDir -Recurse -Force
    Write-Host "  Logs entfernt." -ForegroundColor Green
}
if (Test-Path $RunDir) {
    Remove-Item $RunDir -Recurse -Force
    Write-Host "  Runtime-Dateien (PID) entfernt." -ForegroundColor Green
}

# ——— Desktop-Verknuepfung ———
Write-Host "[3/4] Desktop-Verknuepfung entfernen ..." -ForegroundColor White
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "$AppName.lnk"
if (Test-Path $ShortcutPath) {
    Remove-Item $ShortcutPath -Force
    Write-Host "  Desktop-Verknuepfung entfernt." -ForegroundColor Green
}

# ——— Daten ———
Write-Host "[4/4] Nutzerdaten ..." -ForegroundColor White
if ($Purge) {
    if (-not $Force) {
        Write-Host ""
        Write-Host "=============================================" -ForegroundColor Red
        Write-Host "  WARNUNG: PURGE-MODUS AKTIV" -ForegroundColor Red
        Write-Host "=============================================" -ForegroundColor Red
        Write-Host ""
        Write-Host "  Alle Falldaten, Dokumente, Rechtsquellen-Snapshots" -ForegroundColor Yellow
        Write-Host "  und die Datenbank werden unwiderruflich geloescht." -ForegroundColor Yellow
        Write-Host "  Diese Aktion kann nicht rueckgaengig gemacht werden." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "  SIND SIE SICHER? Geben Sie 'LOESCHEN' ein zum Bestaetigen:" -ForegroundColor Red
        $answer = Read-Host
        if ($answer -ne "LOESCHEN") {
            Write-Host "  Purge abgebrochen. Daten bleiben erhalten." -ForegroundColor Green
            exit 0
        }
    }

    if (Test-Path $DataDir) {
        Remove-Item $DataDir -Recurse -Force
        Write-Host "  Datenverzeichnis geloescht: $DataDir" -ForegroundColor Green
    }

    if (Test-Path $InstallDir) {
        # Pruefen ob InstallDir nur noch leer ist oder Backups enthaelt
        $remaining = Get-ChildItem $InstallDir -ErrorAction SilentlyContinue
        if (-not $remaining) {
            Remove-Item $InstallDir -Force
            Write-Host "  Installationsverzeichnis geloescht." -ForegroundColor Green
        } else {
            Write-Host "  Installationsverzeichnis enthaelt noch Dateien (z.B. Backups)." -ForegroundColor Yellow
            Write-Host "  Nicht geloescht: $InstallDir" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "  Nutzerdaten bleiben erhalten in: $DataDir" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Hinweis: Bei erneuter Installation werden vorhandene" -ForegroundColor Yellow
    Write-Host "  Daten automatisch weiterverwendet." -ForegroundColor Yellow
    Write-Host "  Fuer vollstaendige Loeschung: .\uninstall.ps1 -Purge" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  Deinstallation abgeschlossen." -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""
