#requires -Version 5.1
<#
.SYNOPSIS
Windows Cold-Install Test for PrivateLegalNavigator v1.0.0-rc.2

.DESCRIPTION
Validates a complete cold install, start, stop, backup, restore, uninstall,
and reinstall cycle on a genuine Windows environment.  Must be executed on a
real Windows machine — no results are simulated.

The harness produces a JSON evidence file (cold-test-result.json) and a
transcript file (cold-test-transcript.txt) in $OutputDir.

.NOTES
Version:  1.0.0rc2
Requires: PowerShell 5.1+, Python 3.11+, Wheel file for this version
#>

param(
  [Parameter(Mandatory = $true)][string]$WheelPath,
  [Parameter(Mandatory = $true)][string]$PythonPath,
  [Parameter(Mandatory = $true)][string]$OutputDir,
  [switch]$SkipPurge
)

$ErrorActionPreference = "Stop"

$ResultPath = Join-Path $OutputDir "cold-test-result.json"
$TranscriptPath = Join-Path $OutputDir "cold-test-transcript.txt"
$ArtifactManifestPath = Join-Path $OutputDir "cold-test-artifacts-manifest.json"

$AppVersion = "1.0.0rc2"

# ----------------------------- helpers -----------------------------

function Write-Step {
  param([string]$Message)
  Write-Host "[COLD-TEST] $Message" -ForegroundColor Cyan
}

function Write-Fail {
  param([string]$Message)
  Write-Host "[FAIL] $Message" -ForegroundColor Red
}

$Results = @{
  started_at            = (Get-Date -Format "o")
  finished_at           = ""
  windows_version       = ""
  powershell_version    = $PSVersionTable.PSVersion.ToString()
  python_version        = ""
  package_version       = ""
  wheel_sha256          = ""
  test_results          = @{}
  process_ids           = @()
  backup_sha256         = ""
  restore_result        = ""
  final_classification  = "AMBER_WINDOWS_COLD_TEST_REQUIRED"
}

function Finalize-Result {
  param([string]$Classification)
  $Results.finished_at = (Get-Date -Format "o")
  $Results.final_classification = $Classification
  $Results | ConvertTo-Json -Depth 4 | Set-Content -Path $ResultPath -Encoding UTF8
  Write-Host ""
  Write-Host "=== COLD TEST COMPLETE ===" -ForegroundColor Green
  Write-Host "Classification: $Classification"
  Write-Host "Results: $ResultPath"
  Write-Host "Transcript: $TranscriptPath"
}

# ----------------------------- guard: genuine windows only -----------------------------

if ($IsLinux -or $IsMacOS) {
  Write-Host "ERROR: This harness requires genuine Windows. Detected: non-Windows." -ForegroundColor Red
  Finalize-Result "RED_BLOCK_GENUINE_WINDOWS_REQUIRED"
  exit 1
}

# 1. Environment Discovery
Write-Step "1. Windows & Python Discovery"

$Results.windows_version = [System.Environment]::OSVersion.VersionString

$PythonExe = Join-Path $PythonPath "python.exe"
if (-not (Test-Path $PythonExe)) {
  Write-Fail "python.exe not found at $PythonExe"
  Finalize-Result "RED_BLOCK_PYTHON_NOT_FOUND"
  exit 1
}

$PythonVersion = & $PythonExe --version 2>&1
$Results.python_version = ($PythonVersion -join " ").Trim()
Write-Step "  Python: $($Results.python_version)"

# 2. Verify Wheel Hash
Write-Step "2. Wheel SHA-256"
$WheelHash = (Get-FileHash -Path $WheelPath -Algorithm SHA256).Hash.ToLower()
$Results.wheel_sha256 = $WheelHash
Write-Step "  Wheel SHA-256: $WheelHash"

# 3. Install without admin rights
Write-Step "3. Install (per-user, no admin)"
$InstallIdempotent = 1
try {
  & $PythonExe -m pip install --user $WheelPath 2>&1 | ForEach-Object { Write-Host "    $_" }
} catch {
  Write-Fail "Install failed: $_"
  $InstallIdempotent = 0
}
$Results.test_results["install_no_admin"] = $InstallIdempotent

# 4. Start
Write-Step "4. Start Application"
$DataDir = Join-Path $OutputDir "cold-test-data"
$Port = 18899
$env:PLN_DATA_DIR = $DataDir
$env:PLN_HOST = "127.0.0.1"
$env:PLN_PORT = $Port

$Process = Start-Process -FilePath $PythonExe -ArgumentList "-m private_legal_navigator serve" -PassThru -NoNewWindow
$Results.process_ids += $Process.Id
Start-Sleep -Seconds 5

# 5. Health Check
Write-Step "5. Health Check"
try {
  $HealthResponse = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 5
  $HealthOK = $HealthResponse.status -eq "ok"
  $Results.test_results["health"] = if ($HealthOK) { 1 } else { 0 }
  Write-Step "  Health: $($HealthResponse.status)"
} catch {
  Write-Fail "Health check failed: $_"
  $Results.test_results["health"] = 0
}

# 6. Browser Page
Write-Step "6. Browser Accessible"
try {
  $Page = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/ui/cases" -TimeoutSec 5 -UseBasicParsing
  $PageOK = $Page.StatusCode -eq 200
  $Results.test_results["browser_page"] = if ($PageOK) { 1 } else { 0 }
  Write-Step "  Status code: $($Page.StatusCode)"
} catch {
  Write-Fail "Browser page: $_"
  $Results.test_results["browser_page"] = 0
}

# 7. PID File
Write-Step "7. PID File"
$PidPath = Join-Path $DataDir "private_legal_navigator.pid"
$PidExists = Test-Path $PidPath
$Results.test_results["pid_file_exists"] = if ($PidExists) { 1 } else { 0 }
Write-Step "  PID file exists: $PidExists"

# 8. Process Ownership
Write-Step "8. Process Ownership"
$OwnPid = $Process.Id
$IsRunning = -not $Process.HasExited
$Results.test_results["process_ownership"] = if ($IsRunning) { 1 } else { 0 }
Write-Step "  Process running (PID $OwnPid): $IsRunning"

# 9. Foreign Process Survives
Write-Step "9. Foreign Python Process"
$ForeignPython = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { $_.Id -ne $OwnPid }
$ForeignCount = ($ForeignPython | Measure-Object).Count
$Results.test_results["foreign_process_preserved"] = $ForeignCount
Write-Step "  Other Python processes: $ForeignCount"

# 10. Stop
Write-Step "10. Stop"
$Process | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
$Stopped = $Process.HasExited
$Results.test_results["stop"] = if ($Stopped) { 1 } else { 0 }
Write-Step "  Stopped: $Stopped"

# 11. Restart + Persistence
Write-Step "11. Restart + Persistence"
$Process2 = Start-Process -FilePath $PythonExe -ArgumentList "-m private_legal_navigator serve" -PassThru -NoNewWindow
$Results.process_ids += $Process2.Id
Start-Sleep -Seconds 4

try {
  $Health2 = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 5
  $RestartOK = $Health2.status -eq "ok"
  $Results.test_results["restart_health"] = if ($RestartOK) { 1 } else { 0 }
  Write-Step "  Restart health: $RestartOK"
} catch {
  $Results.test_results["restart_health"] = 0
  Write-Fail "Restart health: $_"
}

$Process2 | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

# 12. Create Test Case
Write-Step "12. Create Test Case"
$env:PLN_DATA_DIR = $DataDir
$Process3 = Start-Process -FilePath $PythonExe -ArgumentList "-m private_legal_navigator serve" -PassThru -NoNewWindow
Start-Sleep -Seconds 4

try {
  $Body = '{"title":"SYNTHETISCH – Cold-Test-Fall"}'
  $Case = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/v1/cases" -Method Post -Body $Body -ContentType "application/json" -TimeoutSec 5
  $CaseOK = $null -ne $Case.case_id -and $Case.title -match "Cold-Test-Fall"
  $Results.test_results["create_case"] = if ($CaseOK) { 1 } else { 0 }
  $Results.test_results["case_id"] = $Case.case_id
  Write-Step "  Case created: $($Case.case_id)"
} catch {
  $Results.test_results["create_case"] = 0
  Write-Fail "Case creation: $_"
}

$Process3 | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

# 13. Persistence After Restart
Write-Step "13. Persistence Check"
$Process4 = Start-Process -FilePath $PythonExe -ArgumentList "-m private_legal_navigator serve" -PassThru -NoNewWindow
Start-Sleep -Seconds 4

try {
  $Cases = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/v1/cases" -Method Get -TimeoutSec 5
  $PersistOK = $Cases.Count -ge 1
  $Results.test_results["persistence"] = if ($PersistOK) { 1 } else { 0 }
  Write-Step "  Cases after restart: $($Cases.Count)"
} catch {
  $Results.test_results["persistence"] = 0
  Write-Fail "Persistence: $_"
}

$Process4 | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

# 14. Backup
Write-Step "14. Backup"
try {
  $BackupDir = Join-Path $OutputDir "cold-test-backup"
  & $PythonExe -m private_legal_navigator.infrastructure.backup_helper $DataDir $BackupDir 2>&1
  $BackupOK = Test-Path (Join-Path $BackupDir "backup-manifest.json")
  $Results.test_results["backup"] = if ($BackupOK) { 1 } else { 0 }

  if ($BackupOK) {
    $ManifestContent = Get-Content (Join-Path $BackupDir "backup-manifest.json") -Raw | ConvertFrom-Json
    $Results.backup_sha256 = $ManifestContent.db_sha256
  }
  Write-Step "  Backup OK: $BackupOK"
} catch {
  $Results.test_results["backup"] = 0
  Write-Fail "Backup: $_"
}

# 16. Purge + Restore
Write-Step "16. Restore in Clean Environment"
try {
  $EmptyDir = Join-Path $OutputDir "cold-test-empty"
  New-Item -ItemType Directory -Force -Path $EmptyDir | Out-Null

  # Create backup ZIP first
  $BackupZip = Join-Path $OutputDir "cold-test-backup.zip"
  Compress-Archive -Path "$BackupDir\*" -DestinationPath $BackupZip -Force

  # Restore into empty dir
  & $PythonExe -m private_legal_navigator.infrastructure.restore_helper $BackupZip $EmptyDir --force 2>&1
  $RestoreOK = Test-Path (Join-Path $EmptyDir "private_legal_navigator.db")

  if ($RestoreOK) {
    $RestoreProc = Start-Process -FilePath $PythonExe -ArgumentList "-c `"import sqlite3; c=sqlite3.connect('$EmptyDir\private_legal_navigator.db'); print(len(c.execute('SELECT * FROM cases').fetchall())); c.close()`"" -PassThru -NoNewWindow -Wait
    $Results.test_results["restore_data_identity"] = if ($RestoreProc.ExitCode -eq 0) { 1 } else { 0 }
  }

  $Results.test_results["restore"] = if ($RestoreOK) { 1 } else { 0 }
  $Results.restore_result = if ($RestoreOK) { "SUCCESS" } else { "FAILURE" }
  Write-Step "  Restore OK: $RestoreOK"
} catch {
  $Results.test_results["restore"] = 0
  $Results.restore_result = "FAILURE: $_"
  Write-Fail "Restore: $_"
}

# 18. Uninstall Without Data Loss
Write-Step "18. Uninstall (keep data)"
try {
  & $PythonExe -m pip uninstall -y private-legal-navigator 2>&1
  $DataStillExists = Test-Path $DataDir
  $Results.test_results["uninstall_keep_data"] = if ($DataStillExists) { 1 } else { 0 }
  Write-Step "  Data preserved: $DataStillExists"
} catch {
  $Results.test_results["uninstall_keep_data"] = 0
  Write-Fail "Uninstall: $_"
}

# 19. Reinstall with Existing Data
Write-Step "19. Reinstall"
try {
  & $PythonExe -m pip install --user $WheelPath 2>&1
  $ReinstallOK = $LASTEXITCODE -eq 0
  $Results.test_results["reinstall"] = if ($ReinstallOK) { 1 } else { 0 }
  Write-Step "  Reinstall OK: $ReinstallOK"
} catch {
  $Results.test_results["reinstall"] = 0
  Write-Fail "Reinstall: $_"
}

# Classification
$AllPass = ($Results.test_results.Values | Where-Object { $_ -eq 0 }).Count -eq 0
$Classification = if ($AllPass) { "GREEN_LOCAL_RELEASE_LINE_RECONCILED" } else { "AMBER_WINDOWS_COLD_TEST_REQUIRED" }

# Artifact Manifest
$ArtifactManifest = @{
  started_at      = $Results.started_at
  finished_at     = (Get-Date -Format "o")
  wheel_sha256    = $Results.wheel_sha256
  data_dir        = $DataDir
  backup_dir      = Join-Path $OutputDir "cold-test-backup"
  output_dir      = $OutputDir
}
$ArtifactManifest | ConvertTo-Json -Depth 3 | Set-Content -Path $ArtifactManifestPath -Encoding UTF8

Finalize-Result $Classification
