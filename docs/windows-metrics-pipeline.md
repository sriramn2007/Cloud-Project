# Historical Prometheus Metrics Pipeline

This phase converts live Prometheus observations into a reproducible time-series dataset for the baseline model and later LSTM work. Prometheus remains the primary monitoring system; this CSV is an ML training artifact, not a replacement for Prometheus.

## Dataset fields

The collector writes one row per sampling interval:

| Field | Meaning |
|---|---|
| `timestamp_utc` | UTC observation time |
| `elapsed_seconds` | Seconds since collection started |
| `workload_rps` | Patient-service request rate |
| `cpu_cores` | Aggregate CPU usage in cores |
| `memory_bytes` | Aggregate working-set memory |
| `available_replicas` | Available patient-service Deployment replicas |
| `desired_replicas` | Desired Deployment replicas |
| `hpa_current_replicas` | Current HPA replica count |
| `hpa_desired_replicas` | HPA desired replica count |
| `request_latency_p95_seconds` | 95th-percentile request latency |

Blank values can occur during startup or when a metric has not accumulated enough history. The preprocessing step reports and interpolates these gaps; it does not silently discard them.

## Preconditions

Prometheus, kube-state-metrics, patient-service, and Metrics Server must be healthy:

```powershell
kubectl -n monitoring get pods
kubectl -n hospital get pods,hpa
kubectl top pods -n hospital
```

Run Prometheus port-forwarding manually if you want to inspect queries:

```powershell
kubectl -n monitoring port-forward service/prometheus 9090:9090
```

## Collect a short validation dataset

From the project root:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\collect-metrics.ps1 `
  -DurationSeconds 300 `
  -IntervalSeconds 15 `
  -Output .\ml\data\raw_metrics.csv
```

Five minutes is only a pipeline validation. For a useful initial model dataset, collect at least 30–60 minutes while running normal, high, spike, and decreasing workload scenarios. Longer history is better when the laptop can support it.

The raw dataset is intentionally ignored by Git because it is generated from the user's local cluster.

## Create a cleaned dataset

```powershell
.\scripts\prepare-metrics.ps1
```

This creates:

```text
ml/data/clean_metrics.csv
ml/data/data_quality.json
```

Review the quality report:

```powershell
Get-Content .\ml\data\data_quality.json
```

Review the data:

```powershell
Import-Csv .\ml\data\clean_metrics.csv | Select-Object -First 10 | Format-Table
```

## Recommended collection procedure

1. Start the patient-service port-forward if you want to run the load generator locally.
2. Start Prometheus port-forwarding through `collect-metrics.ps1`.
3. Begin collection for the desired duration.
4. Run one or more workload profiles in another PowerShell window.
5. Keep the sampling interval fixed across experiments.
6. Preserve the raw CSV and quality report with the experiment results.

Example workload during a collection run:

```powershell
python .\scripts\load_generator.py --url http://127.0.0.1:8001 --profile spike
```

## Checkpoint

The phase passes when `raw_metrics.csv` contains timestamped rows from Prometheus, `clean_metrics.csv` is generated deterministically, and `data_quality.json` documents row count, time span, and missing values. Do not start LSTM training until the dataset contains enough observations across multiple workload conditions.
