[CmdletBinding()]
param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

if (-not (Test-Path .\backend\.venv)) {
    python -m venv .\backend\.venv
}
.\backend\.venv\Scripts\python.exe -m pip install -r .\backend\requirements.txt

Write-Host "Running backend tests..."
Push-Location .\backend
try {
    .\.venv\Scripts\python.exe -m pytest -q
}
finally {
    Pop-Location
}

Write-Host "Starting FastAPI at http://127.0.0.1:$Port"
.\backend\.venv\Scripts\python.exe -m uvicorn app:app --app-dir .\backend --reload --port $Port
