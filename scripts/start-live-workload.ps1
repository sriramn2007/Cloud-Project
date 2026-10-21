[CmdletBinding()]
param(
    [int]$Minutes = 30,
    [int]$MinConcurrency = 1,
    [int]$MaxConcurrency = 12,
    [int]$Port = 8001,
    [int]$CpuWorkPercent = 25
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

if (-not (Test-Path .\data\uci\diabetic_data_features.csv)) {
    throw "The real UCI dataset is missing from data\uci."
}

Write-Host "Starting real-dataset workload stream for $Minutes minutes. Press Ctrl+C to stop."
python .\scripts\live_dataset_workload.py `
    --url "http://127.0.0.1:$Port" `
    --dataset .\data\uci\diabetic_data_features.csv `
    --minutes $Minutes `
    --min-concurrency $MinConcurrency `
    --max-concurrency $MaxConcurrency `
    --cpu-work-percent $CpuWorkPercent
