# Patient Service

This is the first lightweight synthetic hospital service. It exists to create observable Kubernetes workload, not to represent a complete patient management system.

## Run locally

From this directory:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn app:app --reload --port 8001
```

Open `http://127.0.0.1:8001/docs` for the generated API documentation.

## Verify

```bash
curl http://127.0.0.1:8001/healthz
curl http://127.0.0.1:8001/patients
curl http://127.0.0.1:8001/metrics
```

Run tests with:

```bash
python -m pytest -q
```

All records are synthetic and use display names such as `Demo Patient 001`. Do not add real patient information.
