[CmdletBinding()]
param(
    [string[]]$Profiles = @("normal", "high", "spike", "decreasing"),
    [int]$Port = 8001,
    [int]$SampleSeconds = 5,
    [string]$OutputDirectory = ".\results\hpa"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

$durations = @{
    normal = 120
    high = 180
    spike = 240
    decreasing = 180
}

foreach ($profile in $Profiles) {
    if (-not $durations.ContainsKey($profile)) {
        throw "Unsupported profile '$profile'. Use normal, high, spike, or decreasing."
    }
}

New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

foreach ($profile in $Profiles) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $runDirectory = Join-Path $OutputDirectory "$stamp-$profile"
    New-Item -ItemType Directory -Force -Path $runDirectory | Out-Null
    $samplesPath = Join-Path $runDirectory "cluster-samples.csv"
    $loadLogPath = Join-Path $runDirectory "load-generator.jsonl"
    $metadataPath = Join-Path $runDirectory "metadata.txt"

    @(
        "profile=$profile"
        "started=$(Get-Date -Format o)"
        "sample_seconds=$SampleSeconds"
        "planned_duration_seconds=$($durations[$profile])"
    ) | Set-Content $metadataPath

    "timestamp,profile,hpa_current_replicas,hpa_desired_replicas,hpa_cpu_target,hpa_cpu_current,pod_count,running_pod_count,top_output" | Set-Content $samplesPath

    Write-Host "Starting port-forward for profile '$profile'..."
    $forward = Start-Process kubectl -ArgumentList @("-n", "hospital", "port-forward", "service/patient-service", "$Port`:8000") -PassThru -WindowStyle Hidden
    $load = $null

    try {
        Start-Sleep -Seconds 3
        $load = Start-Process python -ArgumentList @(".\scripts\load_generator.py", "--url", "http://127.0.0.1:$Port", "--profile", $profile) -PassThru -WindowStyle Hidden -RedirectStandardOutput $loadLogPath
        $end = (Get-Date).AddSeconds($durations[$profile])

        while ((Get-Date) -lt $end) {
            $timestamp = Get-Date -Format o
            $hpa = kubectl -n hospital get hpa patient-service -o json | ConvertFrom-Json
            $hpaCurrent = $hpa.status.currentReplicas
            $hpaDesired = $hpa.status.desiredReplicas
            $hpaTarget = $hpa.spec.metrics[0].resource.target.averageUtilization
            $hpaCurrentCpu = ""
            if ($hpa.status.currentMetrics -and $hpa.status.currentMetrics[0].resource) {
                $hpaCurrentCpu = $hpa.status.currentMetrics[0].resource.current.averageUtilization
            }

            $pods = @(kubectl -n hospital get pods -l app.kubernetes.io/name=patient-service -o json | ConvertFrom-Json).items
            $podCount = $pods.Count
            $runningCount = @($pods | Where-Object { $_.status.phase -eq "Running" }).Count
            $top = (kubectl top pods -n hospital --no-headers 2>$null) -join " | "
            $safeTop = $top.Replace('"', '""')
            "$timestamp,$profile,$hpaCurrent,$hpaDesired,$hpaTarget,$hpaCurrentCpu,$podCount,$runningCount,""$safeTop""" | Add-Content $samplesPath
            Start-Sleep -Seconds $SampleSeconds
        }
    }
    finally {
        if ($load -and -not $load.HasExited) {
            Stop-Process -Id $load.Id -Force
        }
        if ($forward -and -not $forward.HasExited) {
            Stop-Process -Id $forward.Id -Force
        }
        Add-Content $metadataPath "finished=$(Get-Date -Format o)"
    }

    Write-Host "Completed '$profile'. Evidence: $runDirectory"
}

Write-Host "All HPA experiments completed. Review CSV files under $OutputDirectory."
