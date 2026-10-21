from fastapi.testclient import TestClient

from app import app


client = TestClient(app)


def test_health_and_readiness() -> None:
    assert client.get("/healthz").json()["status"] == "ok"
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert int(response.json()["dataset_rows"]) > 100_000


def test_list_and_get_real_admissions() -> None:
    response = client.get("/patients?limit=3")
    assert response.status_code == 200
    admissions = response.json()
    assert len(admissions) == 3
    assert all("id" in admission and "time_in_hospital" in admission for admission in admissions)
    assert "age" not in admissions[0]

    response = client.get("/patients/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1


def test_missing_admission_returns_404() -> None:
    response = client.get("/patients/999999")
    assert response.status_code == 404


def test_metrics_endpoint() -> None:
    client.get("/healthz")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "patient_service_requests_total" in response.text


def test_work_is_bounded() -> None:
    response = client.get("/work?iterations=10")
    assert response.status_code == 200
    assert response.json()["iterations"] == 10

    response = client.get("/work?iterations=999999999")
    assert response.status_code == 200
    assert response.json()["iterations"] == 2_000_000
