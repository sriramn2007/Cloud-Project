[CmdletBinding()]
param(
    [int]$PrometheusPort = 9090,
    [int]$GrafanaPort = 3000
)

$ErrorActionPreference = "Stop"

$prometheus = Start-Process kubectl -ArgumentList @("-n", "monitoring", "port-forward", "service/prometheus", "$PrometheusPort`:9090") -PassThru -WindowStyle Hidden
$grafana = Start-Process kubectl -ArgumentList @("-n", "monitoring", "port-forward", "service/grafana", "$GrafanaPort`:3000") -PassThru -WindowStyle Hidden

try {
    Start-Sleep -Seconds 5

    Write-Host "Checking Metrics Server..."
    kubectl top nodes
    kubectl top pods -n hospital

    Write-Host "Checking Prometheus readiness..."
    $ready = (Invoke-WebRequest "http://127.0.0.1:$PrometheusPort/-/ready").Content
    Write-Host $ready

    Write-Host "Checking Prometheus targets..."
    $targets = Invoke-RestMethod "http://127.0.0.1:$PrometheusPort/api/v1/targets"
    $targets.data.activeTargets | Select-Object job, health, scrapeUrl | Format-Table

    Write-Host "Querying patient-service request metrics..."
    $query = [uri]::EscapeDataString("patient_service_requests_total")
    $result = Invoke-RestMethod "http://127.0.0.1:$PrometheusPort/api/v1/query?query=$query"
    $result.data.result | Format-Table

    Write-Host "Querying Kubernetes object metrics..."
    $stateQuery = [uri]::EscapeDataString('kube_deployment_status_replicas_available{namespace="hospital",deployment="patient-service"}')
    $stateResult = Invoke-RestMethod "http://127.0.0.1:$PrometheusPort/api/v1/query?query=$stateQuery"
    $stateResult.data.result | Format-Table

    Write-Host "Checking Grafana HTTP endpoint..."
    $grafanaStatus = Invoke-WebRequest "http://127.0.0.1:$GrafanaPort/api/health"
    $grafanaStatus.Content

    Write-Host "Monitoring verification completed. Open http://127.0.0.1:$GrafanaPort for the provisioned dashboard."
}
finally {
    foreach ($process in @($prometheus, $grafana)) {
        if ($process -and -not $process.HasExited) {
            Stop-Process -Id $process.Id -Force
        }
    }
}
