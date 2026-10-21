# Intelligent Kubernetes Auto-Scaling and Resource Optimization for Hospital Cloud Workloads

## 1. Project Overview

This project presents a cloud-management platform for hospital workloads using Kubernetes, Prometheus, Grafana, machine-learning pipelines, FastAPI, and a React operator dashboard. The platform is designed to monitor hospital application workloads, understand resource usage, predict future demand, and eventually perform safe predictive scaling.

The current implementation uses the **Diabetes 130-US Hospitals for Years 1999–2008** dataset from the UCI Machine Learning Repository. The dataset contains 101,766 historical, de-identified hospital encounter records from 130 hospitals and is licensed under Creative Commons Attribution 4.0 International (CC BY 4.0). It is used for a classroom prototype and is not live confidential patient data or a clinical decision-making system.

The project is currently implemented through the monitoring, reactive autoscaling, data-processing, machine-learning, backend-integration, and role-aware dashboard stages. Predictive scaling and production-grade security remain future phases.

## 2. Project Objectives

The main objectives are to:

1. Deploy a hospital-related service in a Kubernetes environment.
2. Monitor application, Pod, cluster, and autoscaling metrics.
3. Store and preprocess historical workload data.
4. Train baseline and LSTM workload-prediction models.
5. Integrate Kubernetes, Prometheus, and model information through a FastAPI backend.
6. Provide an operator dashboard for workload and resource visibility.
7. Introduce role-based access for different hospital employees.
8. Develop a guarded predictive-scaling system in later phases.
9. Compare conventional reactive HPA scaling with predictive scaling.
10. Evaluate resource utilization, response latency, availability, and scaling quality.

## 3. Implemented Components

### 3.1 Public healthcare dataset integration

The original generated demonstration records were replaced with a real public dataset from the UCI Machine Learning Repository. The selected dataset contains hospital admission records, admission types, length of stay, laboratory-procedure counts, medication counts, readmission information, demographic attributes, and selected clinical attributes.

The dataset files are stored in the project under `data/uci/` and include:

- `diabetic_data_features.csv`
- `diabetic_data_targets.csv`

A dataset README records the source, citation, license, de-identification status, and safe-use limitations.

The project does not expose every original dataset field to every user. The application creates separate common and doctor-only views.

### 3.2 Hospital admissions service

The patient-service application was updated to load read-only hospital admission records from the UCI dataset instead of using hard-coded generated records.

The service provides:

- `/healthz` for liveness verification.
- `/readyz` for readiness verification and dataset availability.
- `/patients` for a limited common admission view.
- `/patients/{id}` for an individual common admission record.
- `/work` for bounded CPU workload generation during autoscaling experiments.
- `/metrics` for Prometheus-compatible application metrics.

The service remains read-only with respect to the dataset. No patient record creation or modification endpoint is provided.

### 3.3 Automated testing

Automated tests cover the hospital service and backend integration. The tests verify service health, readiness, dataset loading, admission retrieval, missing-record handling, metric exposure, bounded workload generation, authentication, and role restrictions.

The latest validation produced:

- Patient-service tests: **5 passed**.
- Backend tests: **6 passed**.
- React production build: **successful**.

### 3.4 Docker containerization

The hospital admissions service is packaged as a Docker image. The image contains the application, its Python dependencies, and the public UCI dataset required at runtime.

The Docker image:

- Uses Python 3.12.
- Runs as a non-root user.
- Exposes port 8000.
- Includes a health check.
- Uses the repository root as the build context so the dataset can be included.

### 3.5 Kubernetes deployment

Kubernetes manifests have been prepared for:

- The `hospital` namespace.
- The hospital admissions Deployment.
- The internal Service.
- Resource requests and limits.
- Liveness and readiness probes.
- Horizontal Pod Autoscaler configuration.

The Deployment maintains the desired number of replicas. If a Pod fails or is deleted, Kubernetes creates a replacement Pod. This demonstrates Kubernetes self-healing.

### 3.6 Prometheus monitoring

Prometheus is configured to collect application and Kubernetes metrics. The monitored information includes:

- Request rate.
- CPU usage.
- Memory usage.
- Request latency.
- Number of available replicas.
- Desired replica count.
- Current and desired HPA replicas.
- Deployment and Pod state.

The hospital service exposes request counters and request-duration histograms that Prometheus can scrape.

### 3.7 Grafana visualization

Grafana has been configured with Prometheus as a data source. A hospital Kubernetes dashboard provides visual panels for application traffic, latency, CPU, memory, Pod counts, and HPA behavior.

The dashboard provisioning configuration allows Grafana to start with the configured Prometheus data source and dashboard definitions.

### 3.8 Kubernetes object monitoring

`kube-state-metrics` has been included so Prometheus can observe the logical state of Kubernetes objects. This provides information about Deployments, Pods, replicas, HPAs, and other Kubernetes resources that is not available from container metrics alone.

### 3.9 Reactive autoscaling and load testing

A conventional CPU-based Horizontal Pod Autoscaler is used as the reactive scaling baseline. A bounded CPU workload endpoint and a repeatable load generator have been implemented for experiments.

Supported traffic profiles include:

- Normal workload.
- High workload.
- Sudden spike.
- Decreasing workload.

The experiment runner captures HPA state, Pod count, resource observations, and timing information. This baseline is required for later comparison with predictive scaling.

Reactive HPA operates after resource usage has increased. It does not predict future demand.

### 3.10 Historical metrics collection

A Prometheus collector has been implemented to query and save historical time-series data. The collected data includes workload rate, CPU, memory, request latency, available replicas, desired replicas, and HPA values.

The collector creates a dataset that can be used for model training and evaluation. A separate preprocessing utility performs data validation, type conversion, chronological sorting, missing-value handling, and data-quality reporting.

### 3.11 Workload-prediction pipeline

Two types of models have been prepared:

#### Persistence baseline

The persistence model predicts that the next workload value will be equal to the most recently observed value. Although simple, it is important because it provides a baseline for judging whether the LSTM model adds value.

#### LSTM model

The LSTM pipeline uses historical sequences of workload measurements to predict future workload. It supports normalization, chronological train/validation/test separation, sequence creation, early stopping, model saving, prediction generation, and evaluation using MAE and RMSE.

The final model-quality results depend on collecting and training with the real Prometheus dataset generated by the user's Kubernetes environment.

### 3.12 FastAPI integration backend

A FastAPI backend has been implemented as a unified read-only integration layer. It connects the React frontend to Kubernetes, Prometheus, model artifacts, and the hospital dataset.

Important endpoints include:

- `/healthz`
- `/api/readyz`
- `/api/cluster/status`
- `/api/nodes`
- `/api/pods`
- `/api/workloads`
- `/api/metrics`
- `/api/prediction`
- `/api/auth/login`
- `/api/auth/me`
- `/api/data/summary`
- `/api/data/common`
- `/api/data/clinical`

The backend currently observes and reports system state. It does not yet modify Kubernetes replica counts using AI predictions.

### 3.13 Role-based access control

Two demonstration roles have been implemented:

| Role | Credentials | Access |
|---|---|---|
| Doctor | `doctor` / `doctor-demo` | Common admission fields plus selected demographic and clinical fields |
| Nurse | `nurse` / `nurse-demo` | Common operational and admission fields only |

JWT bearer tokens are issued after login. The backend enforces the role boundary. A nurse request to the doctor-only clinical endpoint receives HTTP 403 Forbidden.

The role system demonstrates authentication and least-privilege authorization. The credentials are local demo credentials and are not suitable for production. A real deployment would require a proper identity provider, hashed passwords, secret management, HTTPS, auditing, and privacy review.

### 3.14 React PulseGrid dashboard

A React and Vite dashboard named **PulseGrid** has been implemented. The dashboard provides:

- Login screen.
- Doctor and nurse role selection.
- Role indicator.
- Logout functionality.
- Command-center overview.
- Kubernetes workload view.
- Admissions data page.
- AI forecast view.
- Resource-optimization view.
- Security-posture view.
- Live and demo status indicators.
- Automatic refresh.
- Manual refresh.
- Responsive layout.

The Admissions data page changes according to the signed-in role. Doctors can view selected clinical and demographic fields, while nurses receive only the common data view.

CORS support was added to allow the Vite frontend to communicate with the local FastAPI backend during development. The frontend production build has completed successfully.

## 4. Current End-to-End Workflow

The current system operates through the following workflow:

```text
UCI de-identified hospital records
                |
                v
Hospital admissions service
                |
                +--> Common admission API
                +--> Prometheus application metrics
                +--> Bounded workload endpoint
                |
                v
Docker container
                |
                v
Kubernetes Deployment and Service
                |
                +--> Health and readiness probes
                +--> Self-healing
                +--> Resource requests and limits
                +--> Reactive HPA
                |
                v
Prometheus and kube-state-metrics
                |
                +--> Current cluster metrics
                +--> Historical workload collection
                |
                v
Dataset preprocessing
                |
                v
Persistence baseline and LSTM pipeline
                |
                v
FastAPI integration backend
                |
                +--> Kubernetes status
                +--> Prometheus metrics
                +--> Prediction artifacts
                +--> Role-protected admission data
                |
                v
PulseGrid React dashboard
```

### Detailed workflow

1. The public UCI dataset is loaded by the hospital admissions service.
2. The service exposes a restricted common admission view and health endpoints.
3. The service runs inside a Docker container.
4. Kubernetes deploys and manages one or more replicas of the container.
5. Kubernetes probes verify whether the Pods are alive and ready.
6. Prometheus scrapes application and infrastructure metrics.
7. kube-state-metrics exposes the logical state of Kubernetes objects.
8. The HPA reacts to CPU pressure by increasing or decreasing replicas.
9. The load generator creates controlled demand profiles for HPA experiments.
10. Prometheus observations are collected as historical training data.
11. The preprocessing pipeline cleans and validates the historical dataset.
12. The baseline and LSTM pipelines produce workload predictions and evaluation results.
13. The FastAPI backend retrieves Kubernetes state, Prometheus metrics, predictions, and protected admission records.
14. A user logs into the React dashboard as either a doctor or nurse.
15. The backend issues a JWT and verifies that role on every protected data request.
16. The dashboard displays common data to both roles and selected clinical data only to the doctor role.

## 5. What Currently Works

The following features are implemented in source code and locally tested:

- Dataset-backed hospital admission records.
- Read-only admission endpoints.
- Health and readiness checks.
- Prometheus application metrics.
- Bounded workload generation.
- Docker packaging definition.
- Kubernetes baseline manifests.
- Kubernetes self-healing configuration.
- Prometheus and Grafana monitoring manifests.
- kube-state-metrics integration.
- Reactive HPA configuration.
- Load-testing profiles and experiment scripts.
- Historical metrics collection and preprocessing utilities.
- Persistence baseline and LSTM training pipeline.
- FastAPI integration API.
- JWT login and role enforcement.
- Doctor-only clinical endpoint.
- Nurse common-data endpoint.
- React PulseGrid dashboard.
- Frontend build and backend authorization tests.

Live Kubernetes behavior depends on the local Windows environment, Docker Desktop, Minikube, kubectl, and the successful startup of the cluster. The application source and validation scripts are prepared for that live demonstration.

## 6. Remaining Work

### 6.1 Predictive decision engine

The next major phase is to implement a decision engine that combines current workload, predicted workload, current replicas, resource availability, and safety thresholds. It should produce `scale_up`, `scale_down`, or `no_action` decisions.

The first version should operate in dry-run mode and should only recommend actions.

### 6.2 Guarded predictive scaling

After dry-run validation, the decision engine can be connected to the Kubernetes API. It must include:

- Minimum and maximum replica limits.
- Confidence thresholds.
- Cooldown periods.
- Maximum change per scaling action.
- Manual enable/disable controls.
- Failure handling.
- Audit records.
- Prevention of conflicting reactive and predictive actions.

### 6.3 Resource optimization

A resource-optimization module should score Kubernetes nodes using CPU availability, memory availability, workload, predicted demand, node health, and Pod distribution. The first implementation should provide recommendations rather than directly replace the Kubernetes scheduler.

### 6.4 PostgreSQL persistence

PostgreSQL should be added for durable storage of users, roles, predictions, scaling decisions, scaling events, optimization recommendations, and audit logs. Prometheus should remain responsible for time-series metrics.

### 6.5 Production authentication and security

The current login system is suitable only for a local demonstration. A production-oriented implementation should add:

- External identity provider or database-backed authentication.
- Password hashing.
- Secret management.
- HTTPS.
- Kubernetes RBAC.
- NetworkPolicies.
- Token refresh and revocation.
- Access auditing.
- Stronger privacy controls.
- Formal healthcare compliance review.

### 6.6 Fault-tolerance testing

The system should be tested under failure of the patient service, Prometheus, FastAPI backend, ML artifact, Kubernetes API, and predictive-scaling controller. The expected behavior should be safe degradation and no uncontrolled scaling.

### 6.7 Final evaluation

The final evaluation should compare:

1. Reactive HPA against predictive scaling.
2. The persistence baseline against the LSTM model.

Evaluation measures should include MAE, RMSE, scaling lead time, request latency, CPU usage, memory usage, replica count, unnecessary scaling events, service availability, and recovery time.

### 6.8 Final documentation

The final project documentation should include architecture diagrams, API documentation, deployment instructions, experiment results, model cards, limitations, security considerations, and a discussion of ethical use of de-identified healthcare data.

## 7. Project Limitations

The UCI dataset is historical and de-identified; it does not represent current hospital operations. It is appropriate for demonstrating data processing and access control but not for clinical decisions.

The local role credentials are demonstration credentials. They do not provide production-grade identity management.

The current FastAPI integration layer is primarily read-only. Predictive scaling has not yet been connected to automatic Kubernetes mutations.

The ML model's final performance cannot be claimed until a real historical Prometheus workload dataset has been collected, the models have been trained, and the evaluation outputs have been recorded.

The dashboard can show demo fallback data when the backend or Kubernetes environment is unavailable. A presentation should clearly distinguish live data from demo data.

## 8. Conclusion

The project has established a complete foundation for intelligent Kubernetes workload management in a hospital-cloud scenario. It now includes a real public de-identified hospital dataset, a containerized and Kubernetes-managed service, Prometheus and Grafana monitoring, reactive HPA experiments, historical-data and machine-learning pipelines, a FastAPI integration layer, and a role-aware React dashboard.

The remaining development is concentrated in the intelligence and production-hardening layers: predictive scaling, resource-optimization decisions, durable audit persistence, stronger authentication, Kubernetes security, fault-tolerance testing, and final comparative evaluation.

The next recommended implementation step is to build the predictive decision engine in dry-run mode. This will allow the project to demonstrate how LSTM predictions can be translated into safe scaling recommendations before any automated cluster changes are enabled.

## 9. References

1. Clore, J., Cios, K., DeShazo, J., & Strack, B. (2014). *Diabetes 130-US Hospitals for Years 1999–2008*. UCI Machine Learning Repository. https://doi.org/10.24432/C5230J
2. UCI Machine Learning Repository dataset page: https://archive.ics.uci.edu/dataset/296/diabetes+130+us+hospitals+for+years+1999+2008
3. Kubernetes Documentation: https://kubernetes.io/docs/
4. Prometheus Documentation: https://prometheus.io/docs/
5. Grafana Documentation: https://grafana.com/docs/
