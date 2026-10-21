# Live workload, Prometheus, and Grafana

## Start changing real-data traffic

The workload runner reads row positions from `data/uci/diabetic_data_features.csv`. Each row maps to the corresponding de-identified admission returned by the admissions service. It randomly requests real admission records, list responses, and readiness checks while gradually increasing and decreasing concurrency.

Start the application and monitoring stack first. Then, in a separate PowerShell window:

```powershell
cd "D:\hospital-cloud-autoscaling-projectt\hospital-cloud-autoscaling"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-live-workload.ps1 -Minutes 30 -MinConcurrency 1 -MaxConcurrency 12 -Port 8001
```

The runner is intentionally traffic simulation, not fake clinical data generation: records remain read-only and come from the bundled public UCI dataset. Stop it with `Ctrl+C`.

## Prometheus

Keep this port-forward open:

```powershell
kubectl -n monitoring port-forward service/prometheus 9090:9090
```

Open `http://127.0.0.1:9090` and use **Graph** or **Query**. Useful queries are:

```promql
sum(rate(patient_service_requests_total{namespace="hospital"}[2m]))
```

Request rate in requests per second.

```promql
histogram_quantile(0.95, sum(rate(patient_service_request_duration_seconds_bucket{namespace="hospital"}[2m])) by (le))
```

95th-percentile request latency.

```promql
sum(rate(container_cpu_usage_seconds_total{namespace="hospital",container!="POD",container!=""}[2m]))
```

CPU usage in cores.

```promql
kube_deployment_status_replicas_available{namespace="hospital",deployment="patient-service"}
```

Available patient-service replicas.

Use a 15-second or 30-second graph refresh. The Prometheus scrape interval is 15 seconds, and the rate queries use a two-minute window to remain stable while traffic changes.

## Grafana

Start the Grafana port-forward:

```powershell
kubectl -n monitoring port-forward service/grafana 3000:3000
```

Open `http://127.0.0.1:3000`. The project provisions a Prometheus datasource and the `Hospital Kubernetes Workload Monitoring` dashboard. The dashboard contains panels for:

- Pod CPU usage
- Pod memory usage
- Patient-service request rate
- P95 request latency
- Available replicas
- HPA desired replicas
- HPA current replicas

Set the dashboard time range to **Last 15 minutes** and refresh to **5s** or **10s**. Start the workload runner and watch request rate rise and fall. HPA replica changes can lag because Kubernetes applies stabilization and metrics-server sampling intervals.

## PulseGrid refresh

The React dashboard polls the FastAPI integration API every five seconds. Its rolling metric charts are populated from the Prometheus-backed API responses. If the cluster, Prometheus, or backend is unavailable, it shows an offline state rather than fabricated live values.

For a complete demonstration, keep these processes running:

1. Kubernetes patient-service and monitoring manifests
2. Prometheus port-forward on port 9090
3. FastAPI backend on port 8000
4. PulseGrid frontend on port 5173
5. The live dataset workload runner
