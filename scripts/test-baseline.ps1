[CmdletBinding()]
param(
    [int]$Port = 8001
)

$ErrorActionPreference = "Stop"

Write-Host "Starting port-forward in the current PowerShell process..."
$forward = Start-Process kubectl -ArgumentList @("-n", "hospital", "port-forward", "service/patient-service", "$Port`:8000") -PassThru -WindowStyle Hidden

try {
    Start-Sleep -Seconds 3
    Write-Host "Testing health endpoint..."
    Invoke-RestMethod "http://127.0.0.1:$Port/healthz"

    Write-Host "Testing readiness endpoint..."
    Invoke-RestMethod "http://127.0.0.1:$Port/readyz"

    Write-Host "Testing patients endpoint..."
    Invoke-RestMethod "http://127.0.0.1:$Port/patients"

    Write-Host "Testing synthetic workload endpoint..."
    Invoke-RestMethod "http://127.0.0.1:$Port/work?iterations=10"

    Write-Host "Testing Prometheus metrics endpoint..."
    $metrics = (Invoke-WebRequest "http://127.0.0.1:$Port/metrics").Content
    if ($metrics -notmatch "patient_service_requests_total") {
        throw "Expected patient_service_requests_total was not found."
    }
    Write-Host "Baseline service smoke test passed."
}
finally {
    if ($forward -and -not $forward.HasExited) {
        Stop-Process -Id $forward.Id -Force
    }
}
