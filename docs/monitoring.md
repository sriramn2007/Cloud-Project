# Monitoring Foundation

## Prerequisites

The local Minikube cluster must be running, and the patient-service image must be loaded before applying the application and monitoring manifests.

Enable Metrics Server through the Minikube addon:

```bash
minikube addons enable metrics-server
kubectl get deployment metrics-server -n kube-system
```

Apply the application and monitoring layers:

```bash
kubectl apply -k k8s/
kubectl apply -k monitoring/

kubectl -n hospital rollout status deployment/patient-service
kubectl -n monitoring rollout status deployment/prometheus
kubectl -n monitoring rollout status deployment/grafana
```

Access the interfaces through port forwarding:

```bash
kubectl -n monitoring port-forward service/prometheus 9090:9090
kubectl -n monitoring port-forward service/grafana 3000:3000
```

Verify telemetry:

```bash
kubectl top pods -n hospital
kubectl top nodes
curl http://127.0.0.1:9090/-/ready
curl http://127.0.0.1:9090/api/v1/query --get --data-urlencode 'query=patient_service_requests_total'
```

Grafana should be available at `http://127.0.0.1:3000`. The Prometheus data source is provisioned automatically. The initial deployment uses ephemeral Prometheus and Grafana storage for local demonstration; persistent storage will be added only if needed for longer experiments.

## Checkpoint

The monitoring phase passes when Metrics Server reports resource usage, Prometheus is ready and returns patient-service metrics, and Grafana can query Prometheus.
