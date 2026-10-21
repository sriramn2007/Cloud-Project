# Two-Minute Project Demo Guide

## 1. What has been implemented

The current prototype includes:

- A real, public, de-identified UCI hospital admissions dataset.

- A read-only FastAPI hospital admissions service.

- Docker packaging and Kubernetes Deployment/Service manifests.

- Health checks, resource limits, and Kubernetes self-healing.

- Prometheus monitoring, Grafana dashboards, kube-state-metrics, and Metrics Server.

- CPU-based Kubernetes HPA as the reactive autoscaling baseline.

- A load generator for normal, high, spike, and decreasing traffic experiments.

- Historical Prometheus metric collection and preprocessing.

- Persistence baseline and LSTM workload-prediction pipelines.

- FastAPI integration APIs for Kubernetes, Prometheus, predictions, and admissions data.

- JWT-based demonstration login with two roles:
  - Doctor: common data plus selected clinical/demographic fields.
  - Nurse: common operational fields only.

- React/Vite PulseGrid operator dashboard with workload, forecast, optimization, security, and admissions views.

## 2. What is not yet complete

Do not claim these as finished during the demo:

- The LSTM prediction is not yet connected to automatic Kubernetes scaling.

- The current HPA is reactive; it scales after resource pressure is observed.

- PostgreSQL audit persistence is not yet implemented.

- The login credentials are demonstration credentials, not production authentication.

- Production security, fault-tolerance testing, and final comparison results are still pending.

## 3. Windows setup before recording

Use the complete ZIP project folder. Open PowerShell in the project root, for example:

```
cd "D:\Hospital Cloud Autoscaling"
```

Make sure these are installed and available:

- Docker Desktop, running.

- Python 3.11 or newer.

- Node.js LTS and npm.

- kubectl.

- Minikube.

Check them:

```
python --version
node --version
npm --version
docker --version
kubectl version --client
minikube version
```

Do not run `npm install` in the project root. Run it inside the frontend folder:

```
cd .\frontend
npm install
cd ..
```

## 4. Recommended full live-demo startup

### PowerShell window 1: Kubernetes application

```
cd "D:\Hospital Cloud Autoscaling"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\deploy-baseline.ps1 -Cpus 4 -MemoryMb 6144
```

Wait until the patient-service Deployment is ready.

### PowerShell window 2: monitoring

```
cd "D:\Hospital Cloud Autoscaling"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\deploy-monitoring.ps1
.\scripts\test-monitoring.ps1
```

### PowerShell window 3: FastAPI backend

```
cd "D:\Hospital Cloud Autoscaling"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\run-backend.ps1
```

The backend tests run first. Leave this window open after Uvicorn starts.

### PowerShell window 4: frontend

```
cd "D:\Hospital Cloud Autoscaling\frontend"
npm run dev
```

Open the Vite URL, normally:

```
http://localhost:5173
```

### PowerShell windows 5–7: port forwarding

Open separate PowerShell windows and run:

```
cd "D:\Hospital Cloud Autoscaling"
kubectl -n hospital port-forward service/patient-service 8001:8000
```

```
cd "D:\Hospital Cloud Autoscaling"
kubectl -n monitoring port-forward service/prometheus 9090:9090
```

```
cd "D:\Hospital Cloud Autoscaling"
kubectl -n monitoring port-forward service/grafana 3000:3000
```

Optional URLs:

- FastAPI documentation: `http://127.0.0.1:8000/docs`

- Prometheus: `http://127.0.0.1:9090`

- Grafana: `http://127.0.0.1:3000`

## 5. Demo login credentials

Use either of these in the dashboard:

```
Doctor
Username: doctor
Password: doctor-demo
```

```
Nurse
Username: nurse
Password: nurse-demo
```

For a clear role demonstration, log in first as the doctor and open Admissions. Show the clinical fields briefly. Sign out and log in as the nurse. Show that the nurse sees only common operational fields.

## 6. Optional live HPA demonstration

Keep the patient-service port-forward running. In another PowerShell window:

```
cd "D:\Hospital Cloud Autoscaling"
python .\scripts\load_generator.py --url http://127.0.0.1:8001 --profile spike
```

At the same time, show the HPA state:

```
kubectl -n hospital get pods,hpa -w
```

The spike profile takes several minutes, so for a two-minute recording it is better to show the dashboard and HPA configuration rather than wait for the entire profile to finish.

## 7. Two-person script for a two-minute recording

### 0:00–0:15 — Person 1: introduction

“Hello, this project is an intelligent Kubernetes-based resource management platform for hospital cloud workloads. The goal is to monitor hospital services, study their workload, and prepare the system for predictive scaling.”

### 0:15–0:35 — Person 1: dataset and service

“We have integrated a real public and de-identified UCI hospital admissions dataset. The admissions service is read-only and runs as a containerized FastAPI service. It provides health checks, admission data, and Prometheus metrics.”

While saying this, show the PulseGrid login page and then the admissions section.

### 0:35–0:55 — Person 2: roles and security

“The dashboard supports two demonstration roles. A doctor can view selected clinical and demographic fields, while a nurse can view only common operational information. This restriction is enforced in the backend using JWT authentication and role checks, not only in the user interface.”

Show doctor Admissions data, sign out, log in as nurse, and show the restricted view.

### 0:55–1:15 — Person 2: Kubernetes and monitoring

“The service is packaged with Docker and deployed using Kubernetes. Kubernetes provides health checks, resource limits, replica management, and self-healing. Prometheus collects application and cluster metrics, while Grafana and kube-state-metrics provide monitoring dashboards.”

Open the Workloads or Command Center page. If prepared, briefly show Grafana or the Kubernetes Pods/HPA terminal.

### 1:15–1:35 — Person 1: autoscaling and machine learning

“We implemented CPU-based HPA as the reactive autoscaling baseline and created load profiles for normal traffic, high traffic, spikes, and decreasing demand. We also collect historical Prometheus metrics and have prepared a persistence baseline and LSTM pipeline for workload prediction.”

Show the AI Forecast and Workloads pages. Do not say that predictive scaling is already automatic.

### 1:35–1:55 — Person 2: dashboard summary

“The PulseGrid dashboard brings together cluster health, workload state, latency, resource usage, forecasts, optimization information, security status, and role-specific admissions data in one operator view.”

Move through the main dashboard cards quickly.

### 1:55–2:00 — Person 1: conclusion

“The remaining work is to connect the predictions to a guarded scaling decision engine, add audit persistence and production security, and evaluate predictive scaling against reactive HPA.”

## 8. Recording tips

- Start all services before beginning the recording.

- Keep the browser and dashboard zoom at approximately 90–100%.

- Do not show passwords or personal information other than the two demo credentials.

- Use the doctor-to-nurse login change as the clearest security demonstration.

- Keep the terminal visible only briefly; the dashboard should be the main focus.

- If Kubernetes is slow, use the dashboard’s clearly labelled demo state rather than stopping the recording. Explain that live cluster metrics require the local Kubernetes services to be running.

- Do not claim that automatic AI predictive scaling, PostgreSQL audit storage, or production healthcare security is complete.

