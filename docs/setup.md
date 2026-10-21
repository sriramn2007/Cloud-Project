# Setup and Phase Checkpoints

## Phase 0 environment audit

The execution environment was checked on 2026-09-13.

| Tool | Detected status |
|---|---|
| Git | Available: 2.43.0 |
| Python | Available: 3.12.3 |
| pip | Available: 24.0 |
| Node.js | Available: v22.13.0 |
| npm | Available: 10.9.2 |
| Docker | Not installed in the current environment |
| kubectl | Not installed in the current environment |
| Minikube | Not installed in the current environment |

## Required local tools before the Kubernetes gate

Install Docker, kubectl, and Minikube on the development computer. Docker must have enough CPU and memory for a small Minikube cluster. The project will not require an AWS account for the main implementation.

After installation, run:

```bash
git --version
python3 --version
node --version
npm --version
docker --version
kubectl version --client
minikube version
```

Then create the local cluster:

```bash
minikube start --driver=docker --cpus=4 --memory=6144
kubectl get nodes
minikube status
```

If the computer has less memory, reduce the Minikube memory only after checking whether monitoring components still run reliably.

## Development rule

Each phase must pass its checkpoint before the next phase begins. Keep generated secrets, datasets, model files, and local credentials out of Git.

## Phase 1 service checkpoint

The patient-service template is located at `services/patient-service`. Its isolated environment is created with:

```bash
cd services/patient-service
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt pytest httpx
.venv/bin/python -m pytest -q
```

Expected result: 5 tests pass.

Run the service locally with:

```bash
.venv/bin/uvicorn app:app --reload --port 8001
```

## Phase 2 container checkpoint

After Docker is installed and running:

```bash
docker build -t hospital/patient-service:dev -f services/patient-service/Dockerfile .
docker run --rm -p 8001:8000 hospital/patient-service:dev
```

In another terminal:

```bash
curl http://127.0.0.1:8001/healthz
curl http://127.0.0.1:8001/metrics
```

The image runs as a non-root user and contains only runtime files.
