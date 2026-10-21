# Windows Baseline and LSTM Workload Models

This phase consumes `ml/data/clean_metrics.csv` and produces a simple baseline plus an LSTM workload predictor. The baseline is required so the LSTM is compared against something measurable.

## Preconditions

First complete the historical metrics phase:

```powershell
Test-Path .\ml\data\clean_metrics.csv
Get-Content .\ml\data\data_quality.json
```

The dataset should contain at least 60 valid observations and should include low- and high-workload periods. A 30–60 minute collection at 15-second intervals normally provides enough rows for an initial experiment.

## Run the baseline only

This does not require TensorFlow:

```powershell
.\scripts\train-models.ps1 -SkipLstm
```

The baseline predicts the next workload value as the most recent observed value. It writes:

```text
ml/models/baseline_predictions.csv
ml/models/metrics.json
```

## Run baseline plus LSTM

```powershell
.\scripts\train-models.ps1 -Epochs 30 -Window 12
```

The default window of 12 means that, with a 15-second sampling interval, the model uses the previous three minutes to predict the next sample.

The LSTM writes:

```text
ml/models/lstm_workload.keras
ml/models/lstm_predictions.csv
ml/models/lstm_scaler.json
ml/models/metrics.json
```

## Windows TensorFlow note

TensorFlow installation can be more reliable in WSL2 than in native Windows Python, depending on the Python and TensorFlow versions. The baseline model remains available without TensorFlow. If the LSTM installation fails, do not fabricate results; run the baseline first, then install the LSTM dependencies inside a WSL2 Ubuntu environment and run the same script against the shared project folder.

## Evaluate the result

```powershell
Get-Content .\ml\models\metrics.json
Import-Csv .\ml\models\baseline_predictions.csv | Select-Object -First 10 | Format-Table
Import-Csv .\ml\models\lstm_predictions.csv | Select-Object -First 10 | Format-Table
```

Compare MAE and RMSE in `metrics.json`. The LSTM should not be described as better unless its test metrics are lower than the persistence baseline on the same chronological test period.

## Checkpoint

The phase passes when the baseline trains and produces evaluation metrics, the LSTM either trains and saves a loadable model or its environment limitation is documented, and the test split is chronological rather than randomly shuffled.
