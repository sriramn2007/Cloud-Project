from __future__ import annotations

import csv
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from auth import User, authenticate, create_token, current_user, require_role
from db import init_db, recent_events, record_event
from dataset import clinical_records, common_records, summary

try:
    from kubernetes import client, config
    from kubernetes.client.exceptions import ApiException
except ImportError:  # pragma: no cover - gives a useful API error when optional runtime deps are absent
    client = None
    config = None
    ApiException = Exception

app = FastAPI(
    title="Hospital Cloud Control API",
    version="0.1.0",
    description="Read-only integration API for Kubernetes, Prometheus, ML artifacts, and role-protected public clinical data.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

NAMESPACE = os.getenv("KUBERNETES_NAMESPACE", "hospital")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://127.0.0.1:9090")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUTOMATIC_SCALING_ENABLED = os.getenv("ENABLE_AUTOMATIC_SCALING", "false").lower() == "true"


@app.on_event("startup")
def startup() -> None:
    init_db()


class LoginRequest(BaseModel):
    username: str
    password: str


def kubernetes_clients() -> tuple[Any, Any, Any]:
    if client is None or config is None:
        raise HTTPException(status_code=503, detail="kubernetes Python client is not installed")
    try:
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()
        return client.CoreV1Api(), client.AppsV1Api(), client.AutoscalingV2Api()
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"Kubernetes configuration unavailable: {error}") from error


def prometheus_query(expression: str) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode({"query": expression})
    request = urllib.request.Request(f"{PROMETHEUS_URL.rstrip('/')}/api/v1/query?{params}")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.load(response)
    except OSError as error:
        raise HTTPException(status_code=503, detail=f"Prometheus unavailable: {error}") from error
    if payload.get("status") != "success":
        raise HTTPException(status_code=502, detail="Prometheus query failed")
    return payload.get("data", {}).get("result", [])


def metric_value(expression: str) -> float | None:
    values = prometheus_query(expression)
    if not values:
        return None
    try:
        return float(values[0]["value"][1])
    except (KeyError, IndexError, TypeError, ValueError):
        return None


@app.get("/healthz", tags=["system"])
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "hospital-control-api"}


@app.post("/api/auth/login", tags=["auth"])
def login(payload: LoginRequest) -> dict[str, Any]:
    user = authenticate(payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    record_event("login", user.username, user.role, {"outcome": "success"})
    return {"access_token": create_token(user), "token_type": "bearer", "user": user.model_dump()}


@app.get("/api/auth/me", tags=["auth"])
def me(user: User = Depends(current_user)) -> dict[str, Any]:
    return user.model_dump()


@app.get("/api/data/summary", tags=["data"])
def data_summary(user: User = Depends(current_user)) -> dict[str, Any]:
    return summary()


@app.get("/api/data/common", tags=["data"])
def common_data(limit: int = Query(default=25, ge=1, le=100), user: User = Depends(current_user)) -> dict[str, Any]:
    return {"visibility": "common", "role": user.role, "records": common_records(limit)}


@app.get("/api/data/clinical", tags=["data"])
def clinical_data(limit: int = Query(default=25, ge=1, le=100), user: User = Depends(require_role("doctor"))) -> dict[str, Any]:
    return {"visibility": "doctor-only", "role": user.role, "records": clinical_records(limit)}


@app.get("/api/cluster/status", tags=["cluster"])
def cluster_status() -> dict[str, Any]:
    core, apps, _ = kubernetes_clients()
    try:
        nodes = core.list_node().items
        pods = core.list_namespaced_pod(NAMESPACE).items
        deployments = apps.list_namespaced_deployment(NAMESPACE).items
        ready_statuses = [
            condition.status
            for node in nodes
            for condition in (node.status.conditions or [])
            if condition.type == "Ready"
        ]
        return {
            "namespace": NAMESPACE,
            "nodes": len(nodes),
            "pods": len(pods),
            "ready_pods": sum(1 for pod in pods if pod.status.phase == "Running"),
            "deployments": len(deployments),
            "healthy": bool(nodes) and len(ready_statuses) == len(nodes) and all(status == "True" for status in ready_statuses),
        }
    except ApiException as error:
        raise HTTPException(status_code=502, detail=f"Kubernetes API error: {error.reason}") from error


@app.get("/api/nodes", tags=["cluster"])
def nodes() -> list[dict[str, Any]]:
    core, _, _ = kubernetes_clients()
    try:
        result = []
        for node in core.list_node().items:
            conditions = {condition.type: condition.status for condition in node.status.conditions or []}
            result.append({
                "name": node.metadata.name,
                "ready": conditions.get("Ready") == "True",
                "cpu_capacity": node.status.capacity.get("cpu") if node.status.capacity else None,
                "memory_capacity": node.status.capacity.get("memory") if node.status.capacity else None,
            })
        return result
    except ApiException as error:
        raise HTTPException(status_code=502, detail=f"Kubernetes API error: {error.reason}") from error


@app.get("/api/pods", tags=["cluster"])
def pods() -> list[dict[str, Any]]:
    core, _, _ = kubernetes_clients()
    try:
        return [
            {
                "name": pod.metadata.name,
                "namespace": pod.metadata.namespace,
                "phase": pod.status.phase,
                "node": pod.spec.node_name,
                "ready": any(condition.type == "Ready" and condition.status == "True" for condition in (pod.status.conditions or [])),
                "restart_count": sum((container.restart_count or 0) for container in (pod.status.container_statuses or [])),
            }
            for pod in core.list_namespaced_pod(NAMESPACE).items
        ]
    except ApiException as error:
        raise HTTPException(status_code=502, detail=f"Kubernetes API error: {error.reason}") from error


@app.get("/api/workloads", tags=["workloads"])
def workloads() -> list[dict[str, Any]]:
    _, apps, autoscaling = kubernetes_clients()
    try:
        hpas = {hpa.spec.scale_target_ref.name: hpa for hpa in autoscaling.list_namespaced_horizontal_pod_autoscaler(NAMESPACE).items}
        output = []
        for deployment in apps.list_namespaced_deployment(NAMESPACE).items:
            hpa = hpas.get(deployment.metadata.name)
            output.append({
                "name": deployment.metadata.name,
                "desired_replicas": deployment.spec.replicas,
                "available_replicas": deployment.status.available_replicas or 0,
                "ready_replicas": deployment.status.ready_replicas or 0,
                "hpa": {
                    "min_replicas": hpa.spec.min_replicas,
                    "max_replicas": hpa.spec.max_replicas,
                    "current_replicas": hpa.status.current_replicas,
                    "desired_replicas": hpa.status.desired_replicas,
                } if hpa else None,
            })
        return output
    except ApiException as error:
        raise HTTPException(status_code=502, detail=f"Kubernetes API error: {error.reason}") from error


@app.get("/api/metrics", tags=["metrics"])
def metrics(metric: str = Query(default="workload_rps", pattern="^(workload_rps|cpu_cores|memory_bytes|latency_p95_seconds)$")) -> dict[str, Any]:
    expressions = {
        "workload_rps": 'sum(rate(patient_service_requests_total{namespace="hospital"}[2m]))',
        "cpu_cores": 'sum(rate(container_cpu_usage_seconds_total{namespace="hospital",container!="POD",container!=""}[2m]))',
        "memory_bytes": 'sum(container_memory_working_set_bytes{namespace="hospital",container!="POD",container!=""})',
        "latency_p95_seconds": 'histogram_quantile(0.95, sum(rate(patient_service_request_duration_seconds_bucket{namespace="hospital"}[2m])) by (le))',
    }
    try:
        value = metric_value(expressions[metric])
        return {"metric": metric, "value": value, "status": "available" if value is not None else "no_samples", "prometheus_url": PROMETHEUS_URL}
    except HTTPException as error:
        return {"metric": metric, "value": None, "status": "unavailable", "detail": error.detail, "prometheus_url": PROMETHEUS_URL}


@app.get("/api/prediction", tags=["prediction"])
def prediction() -> dict[str, Any]:
    predictions_path = PROJECT_ROOT / "ml" / "models" / "lstm_predictions.csv"
    if not predictions_path.exists():
        return {"status": "not_available", "message": "Train the LSTM before requesting predictions.", "prediction": None}
    with predictions_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {"status": "available", "latest": rows[-1] if rows else None, "count": len(rows)}


@app.get("/api/model-metrics", tags=["prediction"])
def model_metrics() -> dict[str, Any]:
    metrics_path = PROJECT_ROOT / "ml" / "models" / "metrics.json"
    evaluation_path = PROJECT_ROOT / "results" / "model-evaluation.json"
    if not metrics_path.exists():
        return {"status": "not_available", "models": [], "comparison": None}
    models = json.loads(metrics_path.read_text(encoding="utf-8"))
    comparison = None
    if evaluation_path.exists():
        comparison = json.loads(evaluation_path.read_text(encoding="utf-8")).get("comparison")
    return {"status": "available", "models": models, "comparison": comparison}


@app.get("/api/scaling/recommendation", tags=["scaling"])
def scaling_recommendation() -> dict[str, Any]:
    """Return a safe predictive recommendation; this endpoint never changes Kubernetes state."""
    prediction_result = prediction()
    latest = prediction_result.get("latest") or {}
    try:
        observed = float(latest.get("actual_workload_rps"))
        predicted = float(latest.get("lstm_predicted_workload_rps"))
    except (TypeError, ValueError):
        return {"mode": "dry-run", "status": "unavailable", "action": "hold", "reason": "A trained prediction is not available.", "mutation_performed": False}
    if predicted > observed * 1.25:
        action = "scale_up"
    elif predicted < observed * 0.75:
        action = "scale_down"
    else:
        action = "hold"
    return {
        "mode": "dry-run",
        "status": "available",
        "action": action,
        "observed_workload_rps": observed,
        "predicted_workload_rps": predicted,
        "guardrails": {"min_replicas": 2, "max_replicas": 6, "max_change_per_action": 1, "cooldown_seconds": 120},
        "mutation_performed": False,
    }


@app.post("/api/scaling/apply", tags=["scaling"])
def apply_scaling(user: User = Depends(require_role("doctor"))) -> dict[str, Any]:
    """Apply one guarded replica change only when explicitly enabled by the operator."""
    recommendation = scaling_recommendation()
    if not AUTOMATIC_SCALING_ENABLED:
        record_event("scaling_blocked", user.username, user.role, {"reason": "ENABLE_AUTOMATIC_SCALING is false", "recommendation": recommendation})
        return {**recommendation, "status": "blocked", "reason": "Automatic scaling is disabled. Set ENABLE_AUTOMATIC_SCALING=true only after reviewing the guardrails."}
    if recommendation.get("status") != "available" or recommendation.get("action") == "hold":
        return {**recommendation, "status": "no_action"}
    _, apps, _ = kubernetes_clients()
    deployment_name = os.getenv("SCALING_DEPLOYMENT", "patient-service")
    try:
        deployment = apps.read_namespaced_deployment(deployment_name, NAMESPACE)
        current = int(deployment.spec.replicas or 1)
        guardrails = recommendation["guardrails"]
        delta = 1 if recommendation["action"] == "scale_up" else -1
        target = max(guardrails["min_replicas"], min(guardrails["max_replicas"], current + delta))
        if target == current:
            return {**recommendation, "status": "guardrail_hold", "current_replicas": current, "target_replicas": target}
        apps.patch_namespaced_deployment_scale(deployment_name, NAMESPACE, {"spec": {"replicas": target}})
        result = {**recommendation, "status": "applied", "current_replicas": current, "target_replicas": target, "mutation_performed": True}
        record_event("scaling_applied", user.username, user.role, result)
        return result
    except ApiException as error:
        raise HTTPException(status_code=502, detail=f"Kubernetes scaling API error: {error.reason}") from error


@app.get("/api/audit", tags=["audit"])
def audit(limit: int = Query(default=50, ge=1, le=200), user: User = Depends(require_role("doctor"))) -> dict[str, Any]:
    return {"events": recent_events(limit), "storage": "postgresql-or-sqlite-fallback"}


@app.get("/api/readyz", tags=["system"])
def readyz() -> dict[str, str]:
    return {"status": "ready", "service": "hospital-control-api"}
