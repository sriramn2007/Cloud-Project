[CmdletBinding()]
param(
    [switch]$SkipLstm,
    [int]$Epochs = 30,
    [int]$Window = 12
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

if ($SkipLstm) {
    python -m pip install -r .\ml\requirements.txt
} else {
    python -m pip install -r .\ml\requirements-lstm.txt
}

$args = @(
    ".\ml\train_models.py",
    "--input", ".\ml\data\clean_metrics.csv",
    "--output-dir", ".\ml\models",
    "--window", $Window,
    "--epochs", $Epochs
)
if ($SkipLstm) {
    $args += "--skip-lstm"
}
python @args
