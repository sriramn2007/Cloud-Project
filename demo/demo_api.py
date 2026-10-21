from __future__ import annotations

import math
import os
import random
import threading
import time
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

try:
    from kubernetes import client, config
except ImportError:
    client = None
    config = None

app = FastAPI(title="PulseGrid Presentation Simulator", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
NAMESPACE = os.getenv("KUBERNETES_NAMESPACE", "hospital")
DEPLOYMENT = os.getenv("SCALING_DEPLOYMENT", "patient-service")
MUTATE_K8S = os.getenv("DEMO_MUTATE_K8S", "false").lower() == "true"
lock = threading.Lock()
state: dict[str, Any] = {"tick": 0, "workload_rps": 8.0, "predicted_rps": 9.0, "current_replicas": 2, "desired_replicas": 2, "history": [8.0]}


def _k8s_scale(target: int) -> None:
    if not MUTATE_K8S or client is None or config is None:
        return
    try:
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()
        client.AppsV1Api().patch_namespaced_deployment_scale(DEPLOYMENT, NAMESPACE, {"spec": {"replicas": target}})
    except Exception:
        pass


def advance() -> None:
    while True:
        time.sleep(5)
        with lock:
            state["tick"] += 1
            phase = state["tick"] / 2.2
            state["workload_rps"] = round(max(2.0, 8.0 + 14.0 * (math.sin(phase) + 0.35 * math.sin(phase * 2.7)) + random.uniform(-1.5, 1.5)), 2)
            state["predicted_rps"] = round(max(2.0, state["workload_rps"] + random.uniform(-1.2, 2.2)), 2)
            state["desired_replicas"] = max(2, min(6, math.ceil(state["predicted_rps"] / 7)))
            state["current_replicas"] += 1 if state["desired_replicas"] > state["current_replicas"] else -1 if state["desired_replicas"] < state["current_replicas"] else 0
            state["history"] = (state["history"] + [state["workload_rps"]])[-20:]
            target = state["desired_replicas"]
        _k8s_scale(target)


threading.Thread(target=advance, daemon=True).start()


def snapshot() -> dict[str, Any]:
    with lock:
        return dict(state)


def _k8s_objects():
    if not MUTATE_K8S or client is None or config is None:
        return None, None
    try:
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()
        return client.AppsV1Api(), client.CoreV1Api()
    except Exception:
        return None, None

def _actual_state():
    apps, core = _k8s_objects()
    if not apps or not core:
        return None
    try:
        deployment = apps.read_namespaced_deployment(DEPLOYMENT, NAMESPACE)
        pod_list = core.list_namespaced_pod(NAMESPACE, label_selector='app.kubernetes.io/name=patient-service')
        pods = [{"name": p.metadata.name, "namespace": NAMESPACE, "phase": p.status.phase or "Unknown", "node": p.spec.node_name or "Pending", "ready": any(c.type == "Ready" and c.status == "True" for c in (p.status.conditions or [])), "restart_count": sum((c.restart_count or 0) for c in (p.status.container_statuses or []))} for p in pod_list.items]
        return {"current_replicas": len(pods), "desired_replicas": deployment.spec.replicas or 0, "pods": pods}
    except Exception:
        return None

def token_from_request(request: Request) -> str | None:
    value = request.headers.get("authorization", "")
    return value.replace("Bearer ", "", 1) if value.startswith("Bearer ") else None


def require_user(token: str | None) -> dict[str, str]:
    if token == "demo-doctor-token":
        return {"username": "doctor", "role": "doctor", "display_name": "Presentation Doctor"}
    if token == "demo-nurse-token":
        return {"username": "nurse", "role": "nurse", "display_name": "Presentation Nurse"}
    raise HTTPException(status_code=401, detail="Presentation login required")


@app.get("/healthz")
def healthz() -> dict[str, Any]:
    return {"status": "ok", "service": "pulsegrid-presentation-simulator", "simulation": True}


@app.post("/api/auth/login")
def login(payload: dict[str, str]) -> dict[str, Any]:
    username, password = payload.get("username", ""), payload.get("password", "")
    if (username, password) not in {("doctor", "doctor-demo"), ("nurse", "nurse-demo")}:
        raise HTTPException(status_code=401, detail="Use doctor/doctor-demo or nurse/nurse-demo")
    role = "doctor" if username == "doctor" else "nurse"
    return {"access_token": f"demo-{role}-token", "token_type": "bearer", "user": {"username": username, "role": role, "display_name": f"Simulation {role.title()}"}}


@app.get("/api/cluster/status")
def cluster(request: Request) -> dict[str, Any]:
    require_user(token_from_request(request)); s = snapshot(); actual = _actual_state(); s = {**s, **actual} if actual else s
    return {"namespace": NAMESPACE, "nodes": 1, "pods": s["current_replicas"], "ready_pods": sum(1 for p in s.get("pods", []) if isinstance(p, dict) and p.get("ready")) if actual else s["current_replicas"], "deployments": 1, "healthy": True, "simulation": True}


@app.get("/api/nodes")
def nodes(request: Request) -> list[dict[str, Any]]:
    require_user(token_from_request(request)); return [{"name": "minikube-sim", "ready": True, "cpu_capacity": "4", "memory_capacity": "8Gi"}]


@app.get("/api/pods")
def pods(request: Request) -> list[dict[str, Any]]:
    if require_user(token_from_request(request))["role"] != "doctor":
        raise HTTPException(status_code=403, detail="Pod inventory is restricted to doctors in presentation mode")
    actual = _actual_state()
    if actual:
        return actual["pods"]
    return [{"name": f"patient-service-sim-{i+1}", "namespace": NAMESPACE, "phase": "Running", "node": "minikube-sim", "ready": True, "restart_count": 0} for i in range(snapshot()["current_replicas"])]


@app.get("/api/workloads")
def workloads(request: Request) -> list[dict[str, Any]]:
    require_user(token_from_request(request)); s = snapshot(); actual = _actual_state(); s = {**s, **actual} if actual else s
    return [{"name": DEPLOYMENT, "desired_replicas": s["desired_replicas"], "available_replicas": s["current_replicas"], "ready_replicas": s["current_replicas"], "hpa": {"min_replicas": 2, "max_replicas": 6, "current_replicas": s["current_replicas"], "desired_replicas": s["desired_replicas"]}}]


@app.get("/api/metrics")
def metrics(request: Request, metric: str = "workload_rps") -> dict[str, Any]:
    require_user(token_from_request(request)); s = snapshot()
    values = {"workload_rps": s["workload_rps"], "cpu_cores": round(min(3.8, 0.25 + s["workload_rps"] / 12), 3), "memory_bytes": 120000000 + s["current_replicas"] * 12000000, "latency_p95_seconds": round(0.04 + s["workload_rps"] / 700, 4)}
    return {"metric": metric, "value": values.get(metric, 0), "status": "available", "prometheus_url": "simulation://prometheus"}


@app.get("/api/prediction")
def prediction(request: Request) -> dict[str, Any]:
    require_user(token_from_request(request)); s = snapshot()
    return {"status": "available", "latest": {"actual_workload_rps": s["workload_rps"], "lstm_predicted_workload_rps": s["predicted_rps"]}, "count": len(s["history"])}


@app.get("/api/model-metrics")
def model_metrics(request: Request) -> dict[str, Any]:
    require_user(token_from_request(request)); return {"status": "available", "models": [{"model": "lstm", "mae": 1.84, "rmse": 2.61, "train_rows": 700}], "comparison": {"winner_by_mae": "lstm", "winner_by_rmse": "lstm"}}


@app.get("/api/scaling/recommendation")
def recommendation(request: Request) -> dict[str, Any]:
    require_user(token_from_request(request)); s = snapshot(); action = "scale_up" if s["desired_replicas"] > s["current_replicas"] else "scale_down" if s["desired_replicas"] < s["current_replicas"] else "hold"
    return {"mode": "simulation", "status": "available", "action": action, "observed_workload_rps": s["workload_rps"], "predicted_workload_rps": s["predicted_rps"], "mutation_performed": MUTATE_K8S}


@app.get("/api/data/common")
def common(request: Request, limit: int = 25) -> dict[str, Any]:
    require_user(token_from_request(request)); return {"visibility": "common", "records": [{"encounter_index": i, "admission_type_id": str((i % 8) + 1), "time_in_hospital": str((i % 14) + 1), "num_lab_procedures": str(20 + i % 60), "num_procedures": str(i % 6), "num_medications": str(4 + i % 20), "readmitted": "NO" if i % 3 else ">30"} for i in range(1, min(limit, 25) + 1)]}


@app.get("/api/data/clinical")
def clinical(request: Request, limit: int = 25) -> dict[str, Any]:
    if require_user(token_from_request(request))["role"] != "doctor": raise HTTPException(status_code=403, detail="Doctor-only simulation view")
    return {"visibility": "doctor-only", "records": [{"encounter_index": i, "admission_type_id": str((i % 8) + 1), "time_in_hospital": str((i % 14) + 1), "age": "[50-60)", "gender": "Female" if i % 2 else "Male", "race": "Caucasian", "medical_specialty": "InternalMedicine", "diag_1": "250.83", "readmitted": "NO"} for i in range(1, min(limit, 25) + 1)]}


@app.get("/api/sim-state")
def sim_state() -> dict[str, Any]:
    return {**snapshot(), "simulation": True, "kubernetes_mutation_enabled": MUTATE_K8S}


@app.get("/grafana", response_class=HTMLResponse)
def grafana() -> str:
    return """<!doctype html><html><head><title>Grafana Presentation</title><style>body{margin:0;background:#111827;color:#e5e7eb;font:14px Arial}header{padding:18px 28px;background:#172033;border-bottom:1px solid #374151}main{padding:24px;display:grid;grid-template-columns:repeat(2,1fr);gap:18px}.panel{background:#1f2937;padding:18px;border-radius:10px}.value{font-size:32px;color:#66e3bb;font-weight:bold}.bars{height:100px;display:flex;align-items:end;gap:4px}.bar{background:#8f9cff;min-width:10px}.tag{color:#fca5a5;font-weight:bold}</style></head><body><header><h1>Mock Grafana · Hospital Workload</h1><div class='tag'>PRESENTATION ENVIRONMENT · ILLUSTRATIVE TELEMETRY</div></header><main><div class='panel'><h2>Request rate</h2><div id='rps' class='value'>—</div><div id='rpsbars' class='bars'></div></div><div class='panel'><h2>Desired replicas</h2><div id='replicas' class='value'>—</div><div id='replicabars' class='bars'></div></div><div class='panel'><h2>CPU utilization</h2><div id='cpu' class='value'>—</div></div><div class='panel'><h2>Forecast</h2><div id='forecast' class='value'>—</div></div></main><script>async function refresh(){let x=await fetch('/api/sim-state').then(r=>r.json());document.getElementById('rps').textContent=x.workload_rps+' rps';document.getElementById('replicas').textContent=x.desired_replicas+' Pods';document.getElementById('cpu').textContent=Math.round((.25+x.workload_rps/12)*25)+'%';document.getElementById('forecast').textContent=x.predicted_rps+' rps';document.getElementById('rpsbars').innerHTML=x.history.map(v=>`<i class='bar' style='height:${Math.max(8,v*3)}px'></i>`).join('');document.getElementById('replicabars').innerHTML=x.history.map(v=>`<i class='bar' style='height:${v*8}px'></i>`).join('')}refresh();setInterval(refresh,5000)</script></body></html>"""
