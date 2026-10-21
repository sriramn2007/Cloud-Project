# Windows FastAPI Integration Backend

This phase adds a read-only integration API. It reads Kubernetes state through the Kubernetes Python client, reads metrics through Prometheus, and reports ML prediction artifacts when they exist.

## Run the backend

From the project root:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\run-backend.ps1
```

The script creates `backend/.venv`, installs backend dependencies, runs tests, and starts Uvicorn on port 8000.

Open the API documentation:

```text
http://127.0.0.1:8000/docs
```

## Endpoints

| Endpoint | Purpose |
|---|---|
| `/healthz` | Backend process health |
| `/api/readyz` | Backend readiness |
| `/api/cluster/status` | Cluster summary |
| `/api/nodes` | Node readiness and capacity |
| `/api/pods` | Hospital namespace Pod status |
| `/api/workloads` | Deployment and HPA state |
| `/api/metrics?metric=workload_rps` | Prometheus-backed workload rate |
| `/api/metrics?metric=cpu_cores` | Prometheus-backed CPU usage |
| `/api/metrics?metric=memory_bytes` | Prometheus-backed memory usage |
| `/api/metrics?metric=latency_p95_seconds` | Prometheus-backed latency |
| `/api/prediction` | Latest saved LSTM prediction, if available |

## Required local connections

For local development, the Kubernetes Python client reads the current kubeconfig context. Confirm it points to Minikube:

```powershell
kubectl config current-context
```

The backend expects Prometheus at `http://127.0.0.1:9090` by default. Keep this port-forward running in another PowerShell window:

```powershell
kubectl -n monitoring port-forward service/prometheus 9090:9090
```

If Prometheus uses another URL, set it before starting the backend:

```powershell
$env:PROMETHEUS_URL = "http://127.0.0.1:9090"
```

## Checkpoint

The phase passes when backend tests pass, `/api/cluster/status` returns the Minikube state, `/api/workloads` returns the patient-service Deployment/HPA, and `/api/metrics` returns real Prometheus values. The backend remains read-only in this phase; automatic scaling is intentionally deferred to the decision-engine phase.
