# start.ps1 — PrivateLegalNavigator starten
# Bindet an 127.0.0.1, wartet auf Healthcheck, oeffnet Browser.

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

# ——— Pruefen ob bereits laeuft ———
$existing = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*private_legal_navigator*" -and $_.Id -ne $PID
}
if ($existing) {
    Write-Host "$AppName laeuft bereits (PID: $($existing.Id))." -ForegroundColor Yellow
    Write-Host "Zum Neustart erst stop.ps1 ausfuehren." -ForegroundColor Yellow
    exit 0
}

# ——— Pruefen ob Port belegt ———
$portCheck = netstat -ano | Select-String ":$Port .*LISTENING"
if ($portCheck) {
    Write-Host "Port $Port ist bereits belegt:" -ForegroundColor Red
    Write-Host $portCheck -ForegroundColor Red
    Write-Host "Bitte den belegenden Prozess beenden oder Port in config.py aendern." -ForegroundColor Yellow
    exit 1
}

# ——— Log-Verzeichnis ———
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

# ——— Umgebungsvariablen ———
$env:PLN_HOST = $HostAddr
$env:PLN_PORT = "$Port"
# Datenverzeichnis als absolute Pfad
$env:PLN_DATA_DIR = Join-Path $InstallDir "data"
$env:PLN_LOG_DIR = $LogDir

# ——— Starten ———
$logFile = Join-Path $LogDir "server-$(Get-Date -Format 'yyyyMMdd').log"
Write-Host "$AppName wird gestartet ..." -ForegroundColor Cyan
Write-Host "  Host:  http://${HostAddr}:${Port}" -ForegroundColor White
Write-Host "  Daten: $env:PLN_DATA_DIR" -ForegroundColor White
Write-Host "  Log:   $logFile" -ForegroundColor White
Write-Host ""

$process = Start-Process -FilePath $VenvPython -ArgumentList "-m", "private_legal_navigator", "serve" `
    -PassThru -WindowStyle Minimized -NoNewWindow

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
