[CmdletBinding()]
param(
    [string]$Input = ".\ml\data\raw_metrics.csv",
    [string]$Output = ".\ml\data\clean_metrics.csv",
    [string]$Report = ".\ml\data\data_quality.json"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

python -m pip install -r .\ml\requirements.txt
python .\ml\prepare_dataset.py `
    --input $Input `
    --output $Output `
    --report $Report
