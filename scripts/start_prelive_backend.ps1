param(
  [Parameter(Mandatory = $true)][string]$BackendDir,
  [Parameter(Mandatory = $true)][string]$DbPath,
  [int]$Port = 8010
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$env:DATABASE_URL = "sqlite+aiosqlite:///$($DbPath.Replace('\', '/'))"
$env:PRELIVE_AUTH_BYPASS = "true"
$env:CLAMAV_ENABLED = "false"
$env:OCRMYPDF_ENABLED = "false"
$env:MEILISEARCH_ENABLED = "false"

Set-Location $BackendDir
python -m uvicorn app.main:app --host 127.0.0.1 --port $Port
