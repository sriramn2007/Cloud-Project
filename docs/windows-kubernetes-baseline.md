# Windows Kubernetes Baseline Deployment

This phase deploys the already-tested Docker image into Minikube and verifies Kubernetes service behavior. Run PowerShell from the project root.

## Prerequisites

Docker Desktop must be running with Linux containers and the Docker engine available. Confirm:

```powershell
docker info
kubectl version --client
minikube version
```

## One-command deployment

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\deploy-baseline.ps1 -RunSelfHealingTest
```

The script starts Minikube if necessary, enables Metrics Server, builds and loads the image, applies `k8s/`, waits for the Deployment, checks resource metrics, and deletes one Pod when `-RunSelfHealingTest` is provided.

If Windows still reports that the script is not digitally signed, run it explicitly with a process-scoped bypass policy:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\deploy-baseline.ps1 -Cpus 4 -MemoryMb 6144
```

If the laptop has limited memory, use:

```powershell
.\scripts\deploy-baseline.ps1 -Cpus 4 -MemoryMb 4096 -RunSelfHealingTest
```

## Smoke test

```powershell
.\scripts\test-baseline.ps1
```

The smoke test checks health, readiness, patient records, synthetic CPU work, and Prometheus metrics. It starts and stops port-forwarding automatically.

## Manual checks

```powershell
kubectl -n hospital get pods,svc,hpa -o wide
kubectl top nodes
kubectl top pods -n hospital
kubectl -n hospital logs deployment/patient-service
```

For interactive API access:

```powershell
kubectl -n hospital port-forward service/patient-service 8001:8000
```

Then open `http://127.0.0.1:8001/docs` or run:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/healthz
Invoke-RestMethod http://127.0.0.1:8001/patients
```

## Success criteria

The phase passes when the Minikube node is `Ready`, two patient-service Pods are `Running` and `Ready`, the Service is reachable, Metrics Server reports usage, and deleting a Pod causes the Deployment to create a replacement.

If the phase fails, collect:

```powershell
kubectl get nodes -o wide
kubectl get pods -A -o wide
kubectl get events -A --sort-by=.lastTimestamp
minikube logs --file=minikube-logs.txt
```

Do not continue to monitoring verification until the application Deployment is healthy.
