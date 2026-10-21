# Windows Reactive HPA and Load-Testing Experiments

This phase measures the existing Kubernetes HPA before predictive scaling is introduced. The goal is to create a repeatable baseline, not to claim an improvement yet.

## Preconditions

The following must already be healthy:

```powershell
kubectl get nodes
kubectl -n hospital get pods,svc,hpa
kubectl -n monitoring get pods
kubectl top nodes
kubectl top pods -n hospital
```

The patient-service and monitoring Pods must be running. The HPA must show a CPU target and should eventually report current CPU.

## Run all profiles

From the project root:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\run-hpa-experiments.ps1
```

The runner executes these profiles:

| Profile | Traffic shape | Planned duration |
|---|---|---:|
| `normal` | Low steady CPU workload | 120 seconds |
| `high` | Sustained high workload | 180 seconds |
| `spike` | Low → high spike → low | 240 seconds |
| `decreasing` | High → medium → low | 180 seconds |

Each profile is executed separately. The runner starts a port-forward, runs the load generator, samples the HPA and Pods every five seconds, and stores evidence under `results/hpa/`.

## Run one profile

```powershell
.\scripts\run-hpa-experiments.ps1 -Profiles spike -SampleSeconds 5
```

## Observe live behavior manually

In another PowerShell window:

```powershell
kubectl -n hospital get hpa patient-service -w
kubectl -n hospital get pods -w
kubectl top pods -n hospital
```

## Review results

Each run directory contains:

```text
cluster-samples.csv
load-generator.jsonl
metadata.txt
```

Open the CSV in Excel or PowerShell:

```powershell
Import-Csv .\results\hpa\<run-directory>\cluster-samples.csv | Format-Table
```

## What to record

Record the initial replica count, peak replica count, time until the first scale-up, CPU usage, final replica count, request errors, and whether scale-down respected the stabilization window. The HPA is reactive, so a traffic spike can occur before the replica count increases.

## Phase completion criteria

The phase is complete when all four profiles run without infrastructure failures, the result directories contain samples and load logs, HPA transitions are observable where the laptop has enough capacity, and the comparison table in `results/hpa/README.md` is filled using measured values.
