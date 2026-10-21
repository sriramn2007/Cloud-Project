# Windows React Operator Dashboard

The frontend is a Vite + React dashboard named **PulseGrid**. It connects to the FastAPI integration backend and displays an explicit offline state when Kubernetes, Prometheus, or the backend is unavailable. It does not silently present simulated live telemetry.

## Run locally

From the project root:

```powershell
cd .\frontend
npm install
npm run dev
```

Open the URL printed by Vite, normally:

```text
http://localhost:5173
```

The FastAPI backend should run separately on port 8000:

```powershell
cd ..
.\scripts\run-backend.ps1
```

The dashboard uses `http://127.0.0.1:8000` by default. To point it at another backend:

```powershell
$env:VITE_API_URL = "http://127.0.0.1:8000"
npm run dev
```

## Implemented views

- **Command center:** cluster health, request rate, CPU, latency, desired replicas, service posture, activity timeline, and node capacity.
- **Workloads:** Deployments, HPA state, available/ready/desired replicas, and Pod inventory.
- **AI forecast:** predicted peak demand, recommendation state, model quality summary, and observed-vs-forecast chart.
- **Optimization:** node score, capacity headroom, and dry-run placement recommendations.
- **Security posture:** control status, synthetic-data boundary, dry-run scaling state, and audit timeline.

## API behavior

On each refresh, the dashboard requests cluster status, nodes, Pods, workloads, four Prometheus-backed metrics, prediction status, and role-specific admission data from FastAPI. It refreshes automatically every 30 seconds and has a manual refresh button. When a live request fails, the dashboard clears the live values and marks the environment as `OFFLINE` so the issue is visible.

## Production build

```powershell
npm run build
npm run preview
```

The generated `frontend/dist` directory is a build artifact and should not be committed or transferred in the project archive.
