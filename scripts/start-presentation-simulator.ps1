[CmdletBinding()]
param([int]$ApiPort = 8100, [switch]$MutateKubernetes)
$ErrorActionPreference = 'Stop'
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root
$Python = Join-Path $Root 'backend\.venv\Scripts\python.exe'
if (-not (Test-Path $Python)) {
    python -m venv (Join-Path $Root 'backend\.venv')
}
& $Python -m pip install -r (Join-Path $Root 'backend\requirements.txt')
$env:DEMO_MUTATE_K8S = if ($MutateKubernetes) { 'true' } else { 'false' }
Write-Host "Starting isolated PulseGrid presentation simulator on http://127.0.0.1:$ApiPort"
if ($MutateKubernetes) { Write-Warning 'Kubernetes mutation is enabled: the simulator will patch patient-service replicas between 2 and 6.' } else { Write-Host 'Kubernetes mutation is disabled; only synthetic simulator values will change.' }
& $Python -m uvicorn demo.demo_api:app --host 127.0.0.1 --port $ApiPort --reload
