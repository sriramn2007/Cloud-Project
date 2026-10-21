# Windows Prometheus and Grafana Monitoring

This phase deploys Prometheus, kube-state-metrics, and Grafana into the Minikube cluster. Grafana receives a provisioned dashboard automatically.

## Deploy monitoring

Run from the project root after the Kubernetes baseline is healthy:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\deploy-monitoring.ps1
```

The script applies `monitoring/`, waits for Prometheus, kube-state-metrics, and Grafana, and lists their Pods and Services.

## Verify monitoring

```powershell
.\scripts\test-monitoring.ps1
```

The verification script checks:

- Metrics Server node and Pod metrics.
- Prometheus readiness.
- Prometheus target health.
- Patient-service request metrics.
- Kubernetes Deployment replica metrics.
- Grafana health.

## Open the dashboard manually

If you prefer manual port forwarding:

```powershell
kubectl -n monitoring port-forward service/prometheus 9090:9090
kubectl -n monitoring port-forward service/grafana 3000:3000
```

Open:

- Prometheus: `http://127.0.0.1:9090`
- Grafana: `http://127.0.0.1:3000`

The dashboard is provisioned under the Grafana folder `Hospital Cloud` with the title `Hospital Kubernetes Workload Monitoring`.

## Dashboard panels

The provisioned dashboard includes:

- Pod CPU usage.
- Pod memory usage.
- Patient-service request rate.
- 95th percentile request latency.
- Available patient-service replicas.
- HPA desired replicas.
- HPA current replicas.

## Generate visible traffic

Keep the patient-service port-forward running:

```powershell
kubectl -n hospital port-forward service/patient-service 8001:8000
```

Run a load profile from another PowerShell window:

```powershell
python .\scripts\load_generator.py --url http://127.0.0.1:8001 --profile spike
```

Refresh the Grafana dashboard and observe request rate, CPU, latency, and replica changes.

## Troubleshooting

Check monitoring Pods:

```powershell
kubectl -n monitoring get pods -o wide
```

Check events:

```powershell
kubectl get events -A --sort-by=.lastTimestamp
```

Inspect Prometheus logs:

```powershell
kubectl -n monitoring logs deployment/prometheus
```

Inspect kube-state-metrics logs:

```powershell
kubectl -n monitoring logs deployment/kube-state-metrics
```

Inspect Grafana logs:

```powershell
kubectl -n monitoring logs deployment/grafana
```
