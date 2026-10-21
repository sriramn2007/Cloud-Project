from fastapi.testclient import TestClient

from app import app


client = TestClient(app)


def login(username: str, password: str) -> dict:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_healthz() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["service"] == "hospital-control-api"


def test_readyz() -> None:
    response = client.get("/api/readyz")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_prediction_is_safe_before_model_exists() -> None:
    response = client.get("/api/prediction")
    assert response.status_code == 200
    assert response.json()["status"] in {"available", "not_available"}


def test_scaling_recommendation_is_dry_run() -> None:
    response = client.get("/api/scaling/recommendation")
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "dry-run"
    assert payload["mutation_performed"] is False


def test_metric_name_is_validated() -> None:
    response = client.get("/api/metrics?metric=not-allowed")
    assert response.status_code == 422


def test_model_metrics_endpoint_is_safe_before_training() -> None:
    response = client.get("/api/model-metrics")
    assert response.status_code == 200
    assert response.json()["status"] in {"available", "not_available"}


def test_audit_requires_doctor_role() -> None:
    nurse = login("nurse", "nurse-demo")
    assert client.get("/api/audit", headers=nurse).status_code == 403


def test_automatic_scaling_is_blocked_by_default() -> None:
    doctor = login("doctor", "doctor-demo")
    response = client.post("/api/scaling/apply", headers=doctor)
    assert response.status_code == 200
    assert response.json()["status"] == "blocked"


def test_nurse_gets_common_data_but_not_clinical_data() -> None:
    headers = login("nurse", "nurse-demo")
    common = client.get("/api/data/common?limit=2", headers=headers)
    assert common.status_code == 200
    assert len(common.json()["records"]) == 2
    assert "age" not in common.json()["records"][0]
    clinical = client.get("/api/data/clinical?limit=2", headers=headers)
    assert clinical.status_code == 403


def test_doctor_gets_clinical_data() -> None:
    headers = login("doctor", "doctor-demo")
    clinical = client.get("/api/data/clinical?limit=2", headers=headers)
    assert clinical.status_code == 200
    assert len(clinical.json()["records"]) == 2
    assert "age" in clinical.json()["records"][0]
    assert "diag_1" in clinical.json()["records"][0]
