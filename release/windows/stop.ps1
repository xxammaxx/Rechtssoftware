# stop.ps1 — PrivateLegalNavigator sicher beenden
# Beendet NUR den eigenen Prozess via PID-Datei, keine fremden Python-Prozesse.

$ErrorActionPreference = "Stop"
$AppName = "PrivateLegalNavigator"
$InstallDir = "$env:LOCALAPPDATA\PrivateLegalNavigator"
$PidFile = Join-Path $InstallDir "run\server.json"

Write-Host "$AppName wird beendet ..." -ForegroundColor Cyan

# ——— Hilfsfunktion: Prozess-Details via CIM ———
function Get-ProcessDetails {
    param([int]$Pid)
    try {
        $cim = Get-CimInstance Win32_Process -Filter "ProcessId = $Pid" -Property ProcessId,ExecutablePath,CommandLine,CreationDate -ErrorAction SilentlyContinue
        if ($cim) {
            return @{
                Pid = $cim.ProcessId
                ExecutablePath = $cim.ExecutablePath
                CommandLine = $cim.CommandLine
                CreationDate = $cim.CreationDate
            }
        }
    } catch {
        return $null
    }
    return $null
}

# ——— PID-Datei lesen und validieren ———
if (-not (Test-Path $PidFile)) {
    Write-Host "$AppName laeuft nicht (keine PID-Datei unter $PidFile)." -ForegroundColor Yellow
    exit 0
}

try {
    $pidData = Get-Content $PidFile -Raw | ConvertFrom-Json
} catch {
    Write-Host "FEHLER: Kann $PidFile nicht lesen. Entferne Datei manuell und starte neu." -ForegroundColor Red
    exit 1
}

# ——— Pflichtfelder pruefen ———
$requiredFields = @("pid", "executable", "install_dir", "started_at_utc", "process_start_time_utc", "instance_id")
foreach ($f in $requiredFields) {
    if (-not $pidData.$f) {
        Write-Host "FEHLER: PID-Datei unvollstaendig (Feld '$f' fehlt). Entferne manuell und starte neu." -ForegroundColor Red
        exit 1
    }
}

Write-Host "Gefundene Instanz: PID=$($pidData.pid), Instanz=$($pidData.instance_id)" -ForegroundColor White

# ——— Prozess-Existenz pruefen ———
$details = Get-ProcessDetails -Pid $pidData.pid
if (-not $details) {
    Write-Host "$AppName laeuft nicht (PID $($pidData.pid) existiert nicht)." -ForegroundColor Yellow
    Write-Host "Entferne veraltete PID-Datei." -ForegroundColor Yellow
    Remove-Item $PidFile -Force
    exit 0
}

# ——— Prozess-Identitaet verifizieren ———
$executableMatch = $details.ExecutablePath -eq $pidData.executable
$installDirMatch = $details.ExecutablePath.StartsWith($pidData.install_dir, [StringComparison]::OrdinalIgnoreCase)
$startTimeMatch = $details.CreationDate -eq $pidData.process_start_time_utc

if (-not $executableMatch) {
    Write-Host "WARNUNG: Executable-Pfad stimmt nicht mit PID-Datei ueberein." -ForegroundColor Yellow
    Write-Host "  PID-Datei: $($pidData.executable)" -ForegroundColor Yellow
    Write-Host "  System:    $($details.ExecutablePath)" -ForegroundColor Yellow
}
if (-not $installDirMatch) {
    Write-Host "WARNUNG: Executable liegt nicht im erwarteten Installationsverzeichnis." -ForegroundColor Yellow
    Write-Host "  Install-Dir: $($pidData.install_dir)" -ForegroundColor Yellow
    Write-Host "  Executable:  $($details.ExecutablePath)" -ForegroundColor Yellow
}
if (-not $startTimeMatch) {
    Write-Host "WARNUNG: Prozess-Startzeit stimmt nicht mit PID-Datei ueberein." -ForegroundColor Yellow
    Write-Host "  PID-Datei: $($pidData.process_start_time_utc)" -ForegroundColor Yellow
    Write-Host "  System:    $($details.CreationDate)" -ForegroundColor Yellow
}

$identityOK = $executableMatch -and $installDirMatch -and $startTimeMatch
if (-not $identityOK) {
    Write-Host ""
    Write-Host "FEHLER: Prozess-Identitaet nicht verifiziert. Fremder Prozess?" -ForegroundColor Red
    Write-Host "Der Prozess (PID $($pidData.pid)) ist NICHT der erwartete $AppName-Prozess." -ForegroundColor Red
    Write-Host "Beende NICHT aus Sicherheitsgruenden. Entferne PID-Datei manuell nach Pruefung." -ForegroundColor Red
    exit 1
}

# ——— Graceful Stop: CloseMainWindow zuerst ———
Write-Host "Beende Prozess PID: $($pidData.pid) (Graceful) ..." -ForegroundColor Yellow

try {
    $proc = Get-Process -Id $pidData.pid -ErrorAction SilentlyContinue
    if ($proc) {
        $closed = $proc.CloseMainWindow()
        if ($closed) {
            # Warte bis zu 10 Sekunden auf sauberes Beenden
            $waited = 0
            while (-not $proc.HasExited -and $waited -lt 10) {
                Start-Sleep -Seconds 1
                $waited++
                $proc.Refresh()
            }
        }
        if (-not $proc.HasExited) {
            Write-Host "Graceful Stop nicht erfolgreich nach ${waited}s. Force Stop ..." -ForegroundColor Yellow
            $proc | Stop-Process -Force
        }
    } else {
        Write-Host "Prozess nicht mehr vorhanden (bereits beendet)." -ForegroundColor Yellow
    }
} catch {
    Write-Host "Fehler beim Beenden, versuche Force Stop ..." -ForegroundColor Yellow
    try {
        Stop-Process -Id $pidData.pid -Force -ErrorAction SilentlyContinue
    } catch {
        Write-Host "Konnte Prozess nicht beenden." -ForegroundColor Red
    }
}

Start-Sleep -Seconds 1

# ——— Verifikation ———
$stillRunning = Get-Process -Id $pidData.pid -ErrorAction SilentlyContinue
if ($stillRunning) {
    Write-Host "FEHLER: Konnte Prozess PID $($pidData.pid) nicht beenden." -ForegroundColor Red
    exit 1
}

# ——— PID-Datei aufraeumen ———
if (Test-Path $PidFile) {
    Remove-Item $PidFile -Force
}

Write-Host "$AppName wurde beendet." -ForegroundColor Green
