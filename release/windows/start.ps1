# start.ps1 — PrivateLegalNavigator starten
# Bindet an 127.0.0.1, wartet auf Healthcheck, oeffnet Browser.
# Schreibt PID-Datei fuer prozesssicheren Stop (vgl. stop.ps1).

param(
    [string]$InstallDir = "$env:LOCALAPPDATA\PrivateLegalNavigator",
    [string]$HostAddr = "127.0.0.1",
    [int]$Port = 8000,
    [int]$HealthTimeout = 30
)

$ErrorActionPreference = "Stop"
$AppName = "PrivateLegalNavigator"
$VenvDir = Join-Path $InstallDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$LogDir = Join-Path $InstallDir "logs"
$RunDir = Join-Path $InstallDir "run"
$PidFile = Join-Path $RunDir "server.json"

# ——— Hilfsfunktion: Prozess-Details via CIM (PowerShell 5.1+ kompatibel) ———
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

# ——— Pruefen ob bereits eigener Prozess laeuft (PID-Datei) ———
if (Test-Path $PidFile) {
    try {
        $pidData = Get-Content $PidFile -Raw | ConvertFrom-Json
        $details = Get-ProcessDetails -Pid $pidData.pid
        if ($details) {
            $executableOk = $details.ExecutablePath -eq $pidData.executable
            $installOk = $details.ExecutablePath.StartsWith($pidData.install_dir, [StringComparison]::OrdinalIgnoreCase)
            $startTimeOk = $details.CreationDate -eq $pidData.process_start_time_utc
            if ($executableOk -and $installOk -and $startTimeOk) {
                Write-Host "$AppName laeuft bereits (PID: $($pidData.pid), Instanz: $($pidData.instance_id))." -ForegroundColor Yellow
                Write-Host "Zum Neustart erst stop.ps1 ausfuehren." -ForegroundColor Yellow
                exit 0
            } else {
                Write-Host "Veraltete PID-Datei gefunden (Prozess existiert nicht mehr oder stimmt nicht ueberein)." -ForegroundColor Yellow
                Write-Host "Entferne $PidFile und starte neu ..." -ForegroundColor Yellow
                Remove-Item $PidFile -Force
            }
        } else {
            Write-Host "Veraltete PID-Datei gefunden (PID $($pidData.pid) existiert nicht mehr)." -ForegroundColor Yellow
            Write-Host "Entferne $PidFile und starte neu ..." -ForegroundColor Yellow
            Remove-Item $PidFile -Force
        }
    } catch {
        Write-Host "Beschaedigte PID-Datei gefunden, entferne und starte neu ..." -ForegroundColor Yellow
        if (Test-Path $PidFile) { Remove-Item $PidFile -Force }
    }
}

# ——— Pruefen ob Port belegt ———
$portCheck = netstat -ano | Select-String ":$Port .*LISTENING"
if ($portCheck) {
    Write-Host "Port $Port ist bereits belegt:" -ForegroundColor Red
    Write-Host $portCheck -ForegroundColor Red
    Write-Host "Bitte den belegenden Prozess beenden oder Port in config.py aendern." -ForegroundColor Yellow
    exit 1
}

# ——— Log- und Run-Verzeichnis ———
foreach ($d in @($LogDir, $RunDir)) {
    if (-not (Test-Path $d)) {
        New-Item -ItemType Directory -Path $d -Force | Out-Null
    }
}

# ——— Umgebungsvariablen ———
$env:PLN_HOST = $HostAddr
$env:PLN_PORT = "$Port"
$env:PLN_DATA_DIR = Join-Path $InstallDir "data"
$env:PLN_LOG_DIR = $LogDir

# ——— Starten ———
$logFile = Join-Path $LogDir "server-$(Get-Date -Format 'yyyyMMdd').log"
Write-Host "$AppName wird gestartet ..." -ForegroundColor Cyan
Write-Host "  Host:  http://${HostAddr}:${Port}" -ForegroundColor White
Write-Host "  Daten: $env:PLN_DATA_DIR" -ForegroundColor White
Write-Host "  Log:   $logFile" -ForegroundColor White
Write-Host ""

$startedAt = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$instanceId = [guid]::NewGuid().ToString()

$process = Start-Process -FilePath $VenvPython -ArgumentList "-m", "private_legal_navigator", "serve" `
    -PassThru -WindowStyle Minimized -NoNewWindow

# CET/CEST -> Dienen nur als Indikator: Unmittelbar nach Start ist der Prozess garantiert schon gestartet
Start-Sleep -Seconds 2
$details = Get-ProcessDetails -Pid $process.Id
if (-not $details) {
    Write-Host "FEHLER: Kann Prozess-Details fuer PID $($process.Id) nicht abrufen." -ForegroundColor Red
    Write-Host "Server wurde gestartet, aber Prozess-Identitaet kann nicht validiert werden." -ForegroundColor Red
    exit 1
}

# ——— PID-Datei atomar schreiben (via Temp-Datei + Move) ———
$pidPayload = @{
    pid = $process.Id
    executable = $details.ExecutablePath
    install_dir = $InstallDir
    started_at_utc = $startedAt
    process_start_time_utc = $details.CreationDate
    instance_id = $instanceId
} | ConvertTo-Json

$pidTemp = "$PidFile.tmp"
Set-Content -Path $pidTemp -Value $pidPayload -Encoding UTF8
Move-Item -Path $pidTemp -Destination $PidFile -Force

# ——— Healthcheck ———
Write-Host "Warte auf Server-Start ..." -ForegroundColor Yellow
$started = $false
for ($i = 0; $i -lt $HealthTimeout; $i++) {
    Start-Sleep -Seconds 1
    try {
        $response = Invoke-WebRequest -Uri "http://${HostAddr}:${Port}/health" `
            -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Host "Server bereit (health OK)." -ForegroundColor Green
            $started = $true
            break
        }
    } catch {
        # not ready yet
    }
    Write-Host "." -NoNewline
}

if (-not $started) {
    Write-Host ""
    Write-Host "FEHLER: Server hat nicht innerhalb von $HealthTimeout Sekunden gestartet." -ForegroundColor Red
    Write-Host "Pruefe Log: $logFile" -ForegroundColor Yellow
    if (Test-Path $PidFile) { Remove-Item $PidFile -Force }
    exit 1
}
Write-Host ""

# ——— Browser oeffnen ———
$url = "http://${HostAddr}:${Port}/ui/cases"
Write-Host "Oeffne Browser: $url" -ForegroundColor Cyan
Start-Process $url

Write-Host ""
Write-Host "$AppName laeuft. Zum Beenden: stop.ps1 ausfuehren." -ForegroundColor Green
Write-Host "Prozess-ID: $($process.Id)" -ForegroundColor White
Write-Host "Instanz-ID: $instanceId" -ForegroundColor Gray
