from __future__ import annotations

import csv
import os
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel, Field
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

app = FastAPI(
    title="Hospital Admissions Service",
    version="0.2.0",
    description="Read-only workload service backed by the public de-identified UCI hospital admissions dataset.",
)

REQUEST_COUNT = Counter("patient_service_requests_total", "Total HTTP requests handled by the patient service.", ["method", "path", "status"])
REQUEST_LATENCY = Histogram("patient_service_request_duration_seconds", "HTTP request duration in seconds.", ["method", "path"])
DATA_ROOT = Path(os.getenv("DATA_ROOT", Path(__file__).resolve().parents[2] / "data" / "uci"))
FEATURES_PATH = DATA_ROOT / "diabetic_data_features.csv"
TARGETS_PATH = DATA_ROOT / "diabetic_data_targets.csv"


class CommonAdmission(BaseModel):
    id: int = Field(gt=0)
    admission_type_id: str
    time_in_hospital: str
    num_lab_procedures: str
    num_procedures: str
    num_medications: str
    readmitted: str


def record_request(method: str, path: str, status_code: int) -> None:
    REQUEST_COUNT.labels(method=method, path=path, status=str(status_code)).inc()


@app.middleware("http")
async def observe_requests(request, call_next):
    with REQUEST_LATENCY.labels(method=request.method, path=request.url.path).time():
        response = await call_next(request)
    record_request(request.method, request.url.path, response.status_code)
    return response


@lru_cache(maxsize=1)
def load_admissions() -> list[dict[str, Any]]:
    if not FEATURES_PATH.exists() or not TARGETS_PATH.exists():
        raise RuntimeError(f"Dataset files not found under {DATA_ROOT}")
    with FEATURES_PATH.open(newline="", encoding="utf-8") as feature_file, TARGETS_PATH.open(newline="", encoding="utf-8") as target_file:
        features = csv.DictReader(feature_file)
        targets = csv.DictReader(target_file)
        rows = []
        for index, (feature, target) in enumerate(zip(features, targets), start=1):
            rows.append({"id": index, **feature, **target})
        return rows


def common_view(row: dict[str, Any]) -> CommonAdmission:
    return CommonAdmission(
        id=int(row["id"]),
        admission_type_id=row.get("admission_type_id", ""),
        time_in_hospital=row.get("time_in_hospital", ""),
        num_lab_procedures=row.get("num_lab_procedures", ""),
        num_procedures=row.get("num_procedures", ""),
        num_medications=row.get("num_medications", ""),
        readmitted=row.get("readmitted", ""),
    )


@app.get("/healthz", tags=["system"])
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "hospital-admissions-service"}


@app.get("/readyz", tags=["system"])
def readyz() -> dict[str, str]:
    try:
        count = len(load_admissions())
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return {"status": "ready", "service": "hospital-admissions-service", "dataset_rows": str(count)}


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/patients", response_model=list[CommonAdmission], tags=["admissions"])
def list_admissions(limit: int = 25) -> list[CommonAdmission]:
    limit = max(1, min(limit, 100))
    return [common_view(row) for row in load_admissions()[:limit]]


@app.get("/patients/{patient_id}", response_model=CommonAdmission, tags=["admissions"])
def get_admission(patient_id: int) -> CommonAdmission:
    row = next((item for item in load_admissions() if item["id"] == patient_id), None)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admission not found")
    return common_view(row)


@app.get("/work", tags=["workload"])
def workload(iterations: int = 100_000) -> dict[str, int]:
    """Perform bounded CPU work for Kubernetes autoscaling experiments; records remain real and read-only."""
    iterations = max(1, min(iterations, 2_000_000))
    accumulator = 0
    for value in range(iterations):
        accumulator = (accumulator + value * value) % 1_000_003
    return {"iterations": iterations, "result": accumulator}
