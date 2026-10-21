# Autoscaling and Load-Testing Baseline

This phase establishes the **reactive Kubernetes HPA baseline**. Predictive scaling will be compared against this baseline later; it is not enabled yet.

## Apply the HPA

After the Kubernetes and Metrics Server checkpoints pass:

```bash
kubectl apply -k k8s/
kubectl -n hospital get hpa patient-service
```

The HPA targets 60% average CPU utilization, keeps 2–6 replicas, scales up quickly but by bounded increments, and waits 120 seconds before scaling down.

## Expose the service locally

```bash
kubectl -n hospital port-forward service/patient-service 8001:8000
```

Keep that terminal running.

## Run traffic profiles

From the repository root:

```bash
python3 scripts/load_generator.py --url http://127.0.0.1:8001 --profile normal
python3 scripts/load_generator.py --url http://127.0.0.1:8001 --profile high
python3 scripts/load_generator.py --url http://127.0.0.1:8001 --profile spike
python3 scripts/load_generator.py --url http://127.0.0.1:8001 --profile decreasing
```

In another terminal, observe scaling:

```bash
kubectl -n hospital get hpa patient-service --watch
kubectl -n hospital get pods --watch
kubectl top pods -n hospital
```

Save the terminal output for later comparison. The load generator prints JSON snapshots containing the selected profile, concurrency, successful requests, and errors.

## Expected behavior

- Normal traffic should remain near the minimum replica count.
- High or spike traffic should increase CPU usage and may increase replicas up to six if the local cluster has enough capacity.
- Decreasing traffic should eventually return toward two replicas after the scale-down stabilization window.
- HPA is reactive, so scale-up occurs only after CPU pressure is observed. This delay is an important baseline for the later predictive controller.

## Checkpoint

The phase passes when the load generator produces repeatable traffic, Metrics Server reports CPU usage, and HPA transitions are observable. Record actual timings and replica counts rather than assuming the example values will occur on every laptop.
