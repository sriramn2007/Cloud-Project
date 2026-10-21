[CmdletBinding()]
param(
    [int]$DurationSeconds = 1800,
    [int]$IntervalSeconds = 15,
    [string]$Output = ".\ml\data\raw_metrics.csv"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

New-Item -ItemType Directory -Force -Path (Split-Path $Output -Parent) | Out-Null
$forward = Start-Process kubectl -ArgumentList @("-n", "monitoring", "port-forward", "service/prometheus", "9090:9090") -PassThru -WindowStyle Hidden

try {
    Start-Sleep -Seconds 5
    Invoke-WebRequest "http://127.0.0.1:9090/-/ready" | Out-Null
    python .\scripts\collect_prometheus_metrics.py `
        --prometheus-url http://127.0.0.1:9090 `
        --output $Output `
        --duration-seconds $DurationSeconds `
        --interval-seconds $IntervalSeconds
}
finally {
    if ($forward -and -not $forward.HasExited) {
        Stop-Process -Id $forward.Id -Force
    }
}
