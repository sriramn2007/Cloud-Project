[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
    throw "kubectl was not found on PATH."
}
if (-not (Get-Command minikube -ErrorAction SilentlyContinue)) {
    throw "minikube was not found on PATH."
}

Write-Host "Checking the Kubernetes node..."
kubectl get nodes

Write-Host "Ensuring Metrics Server is enabled..."
minikube addons enable metrics-server

Write-Host "Applying Prometheus, kube-state-metrics, and Grafana..."
kubectl apply -k .\monitoring\

Write-Host "Waiting for monitoring workloads..."
kubectl -n monitoring rollout status deployment/prometheus --timeout=180s
kubectl -n monitoring rollout status deployment/kube-state-metrics --timeout=180s
kubectl -n monitoring rollout status deployment/grafana --timeout=180s

Write-Host "Monitoring resources:"
kubectl -n monitoring get pods,svc -o wide

Write-Host "Monitoring deployment completed. Run scripts/test-monitoring.ps1 next."
