# Environment Installation Guide

## Recommended host

Use a normal Ubuntu 24.04, Windows with Docker Desktop and WSL2, or macOS with Docker Desktop. The project needs approximately four CPU cores, 6–8 GB of memory available to the local cluster, and at least 20 GB of free storage for images and monitoring components.

The commands below target Ubuntu 24.04. Windows and macOS users should install Docker Desktop first, enable Kubernetes-compatible resources, and run the Kubernetes commands from WSL2 or a terminal with `kubectl`, `minikube`, and Docker available on `PATH`.

## Ubuntu installation

### 1. Install Docker Engine

```bash
sudo apt-get update
sudo apt-get install -y docker.io conntrack socat curl ca-certificates apt-transport-https
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

Log out and log in again, or apply the group change in the current shell:

```bash
newgrp docker
```

Verify Docker:

```bash
docker version
docker run --rm hello-world
```

### 2. Install kubectl

```bash
KUBECTL_VERSION="$(curl -fsSL https://dl.k8s.io/release/stable.txt)"
curl -fL "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl" -o /tmp/kubectl
sudo install -m 0755 /tmp/kubectl /usr/local/bin/kubectl
rm -f /tmp/kubectl
kubectl version --client
```

### 3. Install Minikube

```bash
curl -fL https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64 -o /tmp/minikube-linux-amd64
sudo install -m 0755 /tmp/minikube-linux-amd64 /usr/local/bin/minikube
rm -f /tmp/minikube-linux-amd64
minikube version
```

### 4. Start the cluster

Use at least 6 GiB if the computer has enough memory:

```bash
minikube start --driver=docker --cpus=4 --memory=6144
```

If the computer has only 8 GiB total RAM, use 3 GiB initially and start monitoring components one at a time:

```bash
minikube start --driver=docker --cpus=4 --memory=3072
```

Verify the node:

```bash
minikube status
kubectl get nodes
```

### 5. Enable Metrics Server

```bash
minikube addons enable metrics-server
kubectl -n kube-system rollout status deployment/metrics-server --timeout=180s
kubectl top nodes
```

The first `kubectl top nodes` call may need a short wait while Metrics Server collects its first samples.

## Project setup

From the project root:

```bash
cd /path/to/hospital-cloud-autoscaling

python3 -m venv services/patient-service/.venv
services/patient-service/.venv/bin/python -m pip install -r services/patient-service/requirements.txt pytest httpx
services/patient-service/.venv/bin/python -m pytest -q services/patient-service

docker build -t hospital/patient-service:dev -f services/patient-service/Dockerfile .
minikube image load hospital/patient-service:dev
```

Apply the application, HPA, and monitoring layers:

```bash
kubectl apply -k k8s/
kubectl apply -k monitoring/

kubectl -n hospital rollout status deployment/patient-service --timeout=180s
kubectl -n monitoring rollout status deployment/prometheus --timeout=180s
kubectl -n monitoring rollout status deployment/grafana --timeout=180s
```

## Live verification

In separate terminals:

```bash
kubectl -n hospital port-forward service/patient-service 8001:8000
kubectl -n monitoring port-forward service/prometheus 9090:9090
kubectl -n monitoring port-forward service/grafana 3000:3000
```

Run the service and HPA checks:

```bash
curl http://127.0.0.1:8001/healthz
curl http://127.0.0.1:8001/metrics
kubectl -n hospital get pods,svc,hpa
kubectl top nodes
kubectl top pods -n hospital

python3 scripts/load_generator.py --url http://127.0.0.1:8001 --profile spike
kubectl -n hospital get hpa patient-service --watch
```

Prometheus should be ready at `http://127.0.0.1:9090`. Grafana should be available at `http://127.0.0.1:3000`.

## Important sandbox limitation

The current Manus sandbox has Docker, kubectl, and Minikube installed successfully, and the patient-service image builds and runs. However, its host kernel does not expose the `iptables raw` table required for Docker bridge networking. As a result, Minikube's CNI cannot initialize and the node remains `NotReady`. This is a limitation of the sandbox kernel, not of the project manifests.

Do not permanently disable Docker iptables on a normal host. The temporary workaround was removed after testing. Run the Minikube commands on a normal Linux host, Docker Desktop/WSL2 host, or macOS Docker Desktop host for live Kubernetes verification.
