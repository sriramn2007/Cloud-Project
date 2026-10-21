# Kubernetes Baseline

## Prerequisites

Docker, kubectl, and Minikube must be installed. The image `hospital/patient-service:dev` must be built first.

For Minikube, either build inside the Minikube container runtime:

```bash
minikube docker-env
# Apply the displayed environment command in your shell.
docker build -t hospital/patient-service:dev -f services/patient-service/Dockerfile .
```

Or load an image built by the host:

```bash
minikube image load hospital/patient-service:dev
```

## Deploy

```bash
kubectl apply -k k8s/
kubectl -n hospital rollout status deployment/patient-service
kubectl -n hospital get pods,svc
```

## Verify service behavior

```bash
kubectl -n hospital port-forward service/patient-service 8001:8000
curl http://127.0.0.1:8001/healthz
curl http://127.0.0.1:8001/patients
```

## Verify self-healing

```bash
kubectl -n hospital delete pod -l app.kubernetes.io/name=patient-service --wait=false
kubectl -n hospital get pods -w
```

The Deployment should recreate the deleted Pod and return to two ready replicas.
