param(
  [Parameter(Mandatory = $true)][string]$FrontendDir,
  [int]$BackendPort = 8010,
  [int]$Port = 3000
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$env:VITE_API_PROXY_TARGET = "http://127.0.0.1:$BackendPort"
$env:VITE_PRELIVE_AUTH_BYPASS = "1"

Set-Location $FrontendDir
npm run dev -- --port $Port
