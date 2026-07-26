# stop.ps1 — PrivateLegalNavigator sicher beenden
# Beendet NUR den eigenen Prozess, keine fremden Python-Prozesse.

$ErrorActionPreference = "Stop"
$AppName = "PrivateLegalNavigator"

Write-Host "$AppName wird beendet ..." -ForegroundColor Cyan

# Finde Python-Prozess mit private_legal_navigator im CommandLine
$process = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
    try {
        $_.CommandLine -like "*private_legal_navigator*" -and $_.Id -ne $PID
    } catch {
        $false
    }
}

if (-not $process) {
    $process = Get-Process -Name "pythonw" -ErrorAction SilentlyContinue | Where-Object {
        try {
            $_.CommandLine -like "*private_legal_navigator*" -and $_.Id -ne $PID
        } catch {
            $false
        }
    }
}

if (-not $process) {
    Write-Host "$AppName laeuft nicht." -ForegroundColor Yellow
    exit 0
}

Write-Host "Beende Prozess PID: $($process.Id) ..." -ForegroundColor Yellow
$process | ForEach-Object {
    try {
        $_.CloseMainWindow()
        Start-Sleep -Seconds 2
        if (-not $_.HasExited) {
            $_ | Stop-Process -Force
        }
    } catch {
        $_ | Stop-Process -Force
    }
}

Start-Sleep -Seconds 1

# Verify
$stillRunning = Get-Process -Name "python", "pythonw" -ErrorAction SilentlyContinue | Where-Object {
    try {
        $_.CommandLine -like "*private_legal_navigator*" -and $_.Id -ne $PID
    } catch {
        $false
    }
}
if ($stillRunning) {
    Write-Host "Konnte Prozess nicht beenden." -ForegroundColor Red
    exit 1
}

Write-Host "$AppName wurde beendet." -ForegroundColor Green
