# Intelligent Kubernetes Auto-Scaling and Resource Optimization for Hospital Cloud

A local, open-source prototype for intelligent Kubernetes workload management using the public, de-identified UCI Diabetes 130-US Hospitals dataset.

> Monitor → Predict → Decide → Scale → Optimize → Monitor again

## Implementation status

The repository now contains the complete runnable prototype: UCI-backed admissions service, Docker/Kubernetes deployment, Prometheus/Grafana monitoring, reactive HPA baseline, historical metrics pipeline, persistence and LSTM workload prediction, FastAPI integration API, role-based access control, PostgreSQL-compatible audit logging, guarded predictive scaling, and the PulseGrid React operator dashboard.

Predictive scaling is implemented with explicit safety controls. It remains blocked by default and can only be enabled with `ENABLE_AUTOMATIC_SCALING=true`; it then applies at most one replica change per request within configured min/max guardrails. The default behavior is dry-run/recommendation mode.

## What is included

- Real, de-identified UCI admissions data; no generated clinical dataset.
- Doctor and nurse roles with hashed passwords and environment-configurable users.
- FastAPI endpoints for admissions, cluster state, Prometheus metrics, model results, recommendations, audit events, and guarded scaling.
- PostgreSQL audit storage through `DATABASE_URL`, with SQLite fallback for local development.
- Kubernetes manifests for the patient service, HPA, PostgreSQL development service, and a database NetworkPolicy.
- LSTM and persistence-baseline evaluation using collected workload observations.
- React dashboard that uses live API responses and shows explicit offline states rather than fabricated telemetry.
- Windows PowerShell scripts for setup, monitoring, load tests, model training, verification, and self-healing checks.

## Required production configuration

Before deploying outside development, configure `APP_ENV=production`, a long random `AUTH_SECRET`, `AUTH_USERS_JSON` containing PBKDF2 password hashes, and a real managed PostgreSQL `DATABASE_URL`. Replace the development PostgreSQL password in `k8s/postgres.yaml` with a Kubernetes Secret or external secret manager. Keep `ENABLE_AUTOMATIC_SCALING=false` until the reactive-vs-predictive evaluation has been reviewed.

## Verification

Backend tests:

```powershell
cd backend
python -m pytest -q
```

Frontend build:

```powershell
cd frontend
npm ci
npm run build
```

Project checks:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify-project.ps1
```

Train and evaluate models from real collected metrics:

```powershell
python .\ml\train_models.py --input .\ml\data\clean_metrics.csv --output-dir .\ml\models --skip-lstm
python .\ml\evaluate_models.py
```

## Repository layout

| Directory | Purpose |
|---|---|
| `backend/` | FastAPI integration layer, authentication, audit persistence, and scaling controls |
| `frontend/` | React PulseGrid operator dashboard |
| `services/` | UCI-backed hospital admissions service |
| `k8s/` | Namespace, Deployment, Service, HPA, PostgreSQL, and NetworkPolicy |
| `monitoring/` | Prometheus, Grafana, and Metrics Server configuration |
| `ml/` | Dataset preparation, baseline model, LSTM, and evaluation |
| `scripts/` | Repeatable setup, workload, and experiment scripts |
| `docs/` | Architecture, setup, experiments, and security documentation |

## Scope and safety

This is a research and classroom prototype, not a clinical system. The dataset is public and de-identified. The automatic scaling switch is deliberately opt-in, guarded, and auditable. Live Docker, Minikube, Prometheus, Grafana, and Windows verification must still be executed on the target laptop because those components depend on the local installation and cluster runtime.
