[CmdletBinding()]
param(
    [int]$Cpus = 4,
    [int]$MemoryMb = 6144,
    [switch]$SkipClusterStart,
    [switch]$RunSelfHealingTest
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

function Require-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' was not found on PATH. Install it and restart PowerShell."
    }
}

Require-Command "docker"
Require-Command "kubectl"
Require-Command "minikube"

Write-Host "Using project root: $ProjectRoot"
Write-Host "Checking Docker..."
docker info | Out-Null

if (-not $SkipClusterStart) {
    $status = minikube status --output=json 2>$null | ConvertFrom-Json
    if (-not $status.Host -or $status.Host.Status -ne "Running") {
        Write-Host "Starting Minikube..."
        minikube start --driver=docker --cpus=$Cpus --memory=$MemoryMb
    }
}

Write-Host "Verifying Minikube and Kubernetes node..."
minikube status
kubectl get nodes

Write-Host "Enabling Metrics Server..."
minikube addons enable metrics-server

Write-Host "Building patient-service image..."
if (-not (Test-Path .\data\uci\diabetic_data_features.csv) -or -not (Test-Path .\data\uci\diabetic_data_targets.csv)) {
    throw "UCI dataset files are missing. Ensure data\uci\diabetic_data_features.csv and data\uci\diabetic_data_targets.csv are present before building."
}
docker build -t hospital/patient-service:dev -f .\services\patient-service\Dockerfile .

Write-Host "Loading image into Minikube..."
minikube image load hospital/patient-service:dev

Write-Host "Applying hospital manifests..."
kubectl apply -k .\k8s\

Write-Host "Waiting for patient-service rollout..."
kubectl -n hospital rollout status deployment/patient-service --timeout=180s

Write-Host "Current hospital resources:"
kubectl -n hospital get pods,svc,hpa -o wide

Write-Host "Metrics Server status:"
kubectl -n kube-system rollout status deployment/metrics-server --timeout=180s
kubectl top nodes

if ($RunSelfHealingTest) {
    Write-Host "Running self-healing test..."
    $pod = kubectl -n hospital get pods -l app.kubernetes.io/name=patient-service -o jsonpath="{.items[0].metadata.name}"
    if ([string]::IsNullOrWhiteSpace($pod)) {
        throw "No patient-service Pod was found for the self-healing test."
    }
    Write-Host "Deleting Pod $pod"
    kubectl -n hospital delete pod $pod --wait=false
    Start-Sleep -Seconds 5
    kubectl -n hospital get pods -o wide
    kubectl -n hospital rollout status deployment/patient-service --timeout=180s
    Write-Host "Self-healing test completed."
}

Write-Host "Baseline deployment completed. To access the service, run:"
Write-Host "kubectl -n hospital port-forward service/patient-service 8001:8000"
