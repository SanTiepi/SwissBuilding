param(
  [int]$BackendPort = 8010,
  [int]$FrontendPort = 3000,
  [switch]$ResetDb = $true
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Test-PortInUse {
  param([int]$Port)
  $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
  try {
    $listener.Start()
    $listener.Stop()
    return $false
  } catch {
    return $true
  }
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot "backend"
$frontendDir = Join-Path $repoRoot "frontend"
$dbPath = Join-Path $backendDir "local_preview.db"
$backendStarter = Join-Path $PSScriptRoot "start_prelive_backend.ps1"
$frontendStarter = Join-Path $PSScriptRoot "start_prelive_frontend.ps1"

if (Test-PortInUse -Port $BackendPort) {
  throw "Backend port $BackendPort is already in use."
}

if (Test-PortInUse -Port $FrontendPort) {
  throw "Frontend port $FrontendPort is already in use."
}

Write-Host "[prelive] Bootstrap SQLite dataset..." -ForegroundColor Cyan
$bootstrapArgs = @("-m", "app.seeds.bootstrap_local_sqlite", "--db-path", "./local_preview.db")
if ($ResetDb) {
  $bootstrapArgs += "--reset"
}
Push-Location $backendDir
python @bootstrapArgs
Pop-Location

Write-Host "[prelive] Starting backend (no-password mode)..." -ForegroundColor Cyan
$backendProc = Start-Process `
  -FilePath "powershell" `
  -ArgumentList @(
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    $backendStarter,
    "-BackendDir",
    $backendDir,
    "-DbPath",
    $dbPath,
    "-Port",
    "$BackendPort"
  ) `
  -PassThru

$backendReady = $false
for ($i = 0; $i -lt 120; $i++) {
  try {
    $health = Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:$BackendPort/health" -TimeoutSec 2
    if ($health.status -eq "ok") {
      $backendReady = $true
      break
    }
  } catch {
    Start-Sleep -Milliseconds 500
  }
}

if (-not $backendReady) {
  throw "Backend failed to start on port $BackendPort."
}

Write-Host "[prelive] Starting frontend..." -ForegroundColor Cyan
$frontendProc = Start-Process `
  -FilePath "powershell" `
  -ArgumentList @(
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    $frontendStarter,
    "-FrontendDir",
    $frontendDir,
    "-BackendPort",
    "$BackendPort",
    "-Port",
    "$FrontendPort"
  ) `
  -PassThru

Write-Host "[prelive] Launched." -ForegroundColor Green
Write-Host "Backend health:  http://127.0.0.1:$BackendPort/health"
Write-Host "Frontend login:  http://localhost:$FrontendPort/login"
Write-Host "Mode pre-live sans mot de passe: ACTIF"
Write-Host "Backend PID: $($backendProc.Id)"
Write-Host "Frontend PID: $($frontendProc.Id)"
