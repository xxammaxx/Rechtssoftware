# install.ps1 — PrivateLegalNavigator v1.0.0-rc.1 Windows-Installation
# Idempotent: safe to run multiple times.
# Keine Administratorrechte erforderlich.

param(
    [string]$InstallDir = "$env:LOCALAPPDATA\PrivateLegalNavigator",
    [string]$DataDir = "$env:LOCALAPPDATA\PrivateLegalNavigator\data",
    [switch]$CreateDesktopShortcut = $true,
    [string]$WheelPath = $null
)

$ErrorActionPreference = "Stop"
$AppName = "PrivateLegalNavigator"
$AppVersion = "1.0.0rc1"
$RequiredPython = @("3.11", "3.12", "3.13", "3.14")

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  $AppName v$AppVersion — Installation" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# ——— 1. Python finden ———
Write-Host "[1/7] Python suchen ..." -ForegroundColor White
$PythonExe = $null
foreach ($ver in $RequiredPython) {
    $candidate = Get-Command "py" -ErrorAction SilentlyContinue
    if ($candidate) {
        $result = & py "-$ver" -c "import sys; print(sys.executable); print(sys.version)" 2>$null
        if ($LASTEXITCODE -eq 0) {
            $lines = $result -split "`n"
            $PythonExe = $lines[0].Trim()
            $PythonVer = $lines[1].Trim()
            Write-Host "  Gefunden: $PythonExe ($PythonVer)" -ForegroundColor Green
            break
        }
    }
}

if (-not $PythonExe) {
    Write-Host "  FEHLER: Python 3.11 oder neuer nicht gefunden." -ForegroundColor Red
    Write-Host "  Bitte installiere Python von https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "  (Bei Installation 'Add Python to PATH' aktivieren)" -ForegroundColor Yellow
    exit 1
}

# ——— 2. Wheel finden ———
Write-Host "[2/7] Release-Paket finden ..." -ForegroundColor White
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $WheelPath) {
    $WheelPath = Join-Path $ScriptDir "..\output\private_legal_navigator-1.0.0rc1-py3-none-any.whl"
}
if (-not (Test-Path $WheelPath)) {
    # Fallback: wheel im gleichen Verzeichnis
    $WheelPath = Join-Path $ScriptDir "private_legal_navigator-1.0.0rc1-py3-none-any.whl"
}
if (-not (Test-Path $WheelPath)) {
    Write-Host "  FEHLER: Wheel-Datei nicht gefunden: $WheelPath" -ForegroundColor Red
    Write-Host "  Bitte das Release-ZIP vollstaendig entpacken." -ForegroundColor Yellow
    exit 1
}
Write-Host "  Gefunden: $WheelPath" -ForegroundColor Green

# ——— 3. Installationsverzeichnis ———
Write-Host "[3/7] Installationsverzeichnis vorbereiten ..." -ForegroundColor White
if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    Write-Host "  Erstellt: $InstallDir" -ForegroundColor Green
} else {
    Write-Host "  Vorhanden: $InstallDir" -ForegroundColor Yellow
}

# ——— 4. Virtuelle Umgebung ———
Write-Host "[4/7] Virtuelle Umgebung erstellen ..." -ForegroundColor White
$VenvDir = Join-Path $InstallDir ".venv"
if (Test-Path $VenvDir) {
    Write-Host "  Virtuelle Umgebung existiert bereits. Ueberspringe Erstellung." -ForegroundColor Yellow
} else {
    & $PythonExe -m venv $VenvDir *>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  FEHLER: Konnte virtuelle Umgebung nicht erstellen." -ForegroundColor Red
        exit 1
    }
    Write-Host "  Erstellt: $VenvDir" -ForegroundColor Green
}

$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

# ——— 5. Pip aktualisieren und Wheel installieren ———
Write-Host "[5/7] Package installieren ..." -ForegroundColor White
& $VenvPython -m pip install --upgrade pip --quiet 2>&1 | Out-Null
& $VenvPython -m pip install $WheelPath 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  FEHLER: Installation des Wheels fehlgeschlagen." -ForegroundColor Red
    exit 1
}
Write-Host "  Installation erfolgreich." -ForegroundColor Green

# ——— 6. pip check ———
Write-Host "[6/7] Abhaengigkeiten pruefen ..." -ForegroundColor White
$checkResult = & $VenvPython -m pip check 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  WARNUNG: pip check meldet Probleme:" -ForegroundColor Yellow
    Write-Host "  $checkResult" -ForegroundColor Yellow
} else {
    Write-Host "  Alle Abhaengigkeiten in Ordnung." -ForegroundColor Green
}

# ——— 7. Datenverzeichnis ———
Write-Host "[7/7] Datenverzeichnis vorbereiten ..." -ForegroundColor White
if (-not (Test-Path $DataDir)) {
    New-Item -ItemType Directory -Path $DataDir -Force | Out-Null
    Write-Host "  Erstellt: $DataDir" -ForegroundColor Green
} else {
    Write-Host "  Vorhanden: $DataDir (Daten werden nicht ueberschrieben)" -ForegroundColor Yellow
}

# ——— Desktop-Verknuepfung ———
if ($CreateDesktopShortcut) {
    $DesktopPath = [Environment]::GetFolderPath("Desktop")
    $ShortcutPath = Join-Path $DesktopPath "$AppName.lnk"
    if (-not (Test-Path $ShortcutPath)) {
        $StartScript = Join-Path $ScriptDir "start.ps1"
        $WshShell = New-Object -ComObject WScript.Shell
        $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
        $Shortcut.TargetPath = "powershell.exe"
        $Shortcut.Arguments = "-ExecutionPolicy Bypass -File `"$StartScript`""
        $Shortcut.WorkingDirectory = $ScriptDir
        $Shortcut.IconLocation = "powershell.exe,0"
        $Shortcut.Description = "$AppName — Lokale Unterstuetzung bei rechtlichen Angelegenheiten"
        $Shortcut.Save()
        Write-Host "  Desktop-Verknuepfung erstellt: $ShortcutPath" -ForegroundColor Green
    } else {
        Write-Host "  Desktop-Verknuepfung existiert bereits." -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  Installation abgeschlossen!" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Installationsverzeichnis: $InstallDir" -ForegroundColor White
Write-Host "  Datenverzeichnis:        $DataDir" -ForegroundColor White
Write-Host ""
Write-Host "  Starten:  .\start.ps1" -ForegroundColor Yellow
Write-Host "  Oeffnen:  http://127.0.0.1:8000" -ForegroundColor Yellow
Write-Host ""
