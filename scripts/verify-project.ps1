[CmdletBinding()]
param(
    [int]$BackendPort = 8000
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

function Require-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' was not found on PATH."
    }
}

Write-Host "Checking project files..."
foreach ($path in @(
    ".\data\uci\diabetic_data_features.csv",
    ".\data\uci\diabetic_data_targets.csv",
    ".\services\patient-service\Dockerfile",
    ".\k8s\patient-service-deployment.yaml",
    ".\monitoring\prometheus-config.yaml",
    ".\monitoring\grafana.yaml",
    ".\frontend\package.json"
)) {
    if (-not (Test-Path $path)) { throw "Missing required project file: $path" }
}

Write-Host "Checking local tool versions..."
foreach ($command in @("python", "node", "npm", "docker", "kubectl", "minikube")) { Require-Command $command }
python --version
node --version
npm --version
docker --version
kubectl version --client
minikube version

if (Test-NetConnection -ComputerName 127.0.0.1 -Port $BackendPort -InformationLevel Quiet) {
    Write-Host "Checking FastAPI health..."
    $health = Invoke-RestMethod "http://127.0.0.1:$BackendPort/healthz"
    if ($health.status -ne "ok") { throw "FastAPI health check failed." }
    Write-Host "FastAPI health: OK"
} else {
    Write-Warning "FastAPI is not listening on port $BackendPort. Start scripts\run-backend.ps1 before live API checks."
}

Write-Host "Project verification completed."
