#!/usr/bin/env python3
"""Collect a reproducible workload time series from Prometheus."""

from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


QUERIES = {
    "workload_rps": 'sum(rate(patient_service_requests_total{namespace="hospital"}[2m]))',
    "cpu_cores": 'sum(rate(container_cpu_usage_seconds_total{namespace="hospital",container!="POD",container!=""}[2m]))',
    "memory_bytes": 'sum(container_memory_working_set_bytes{namespace="hospital",container!="POD",container!=""})',
    "available_replicas": 'sum(kube_deployment_status_replicas_available{namespace="hospital",deployment="patient-service"})',
    "desired_replicas": 'sum(kube_deployment_spec_replicas{namespace="hospital",deployment="patient-service"})',
    "hpa_current_replicas": 'sum(kube_horizontalpodautoscaler_status_current_replicas{namespace="hospital",horizontalpodautoscaler="patient-service"})',
    "hpa_desired_replicas": 'sum(kube_horizontalpodautoscaler_status_desired_replicas{namespace="hospital",horizontalpodautoscaler="patient-service"})',
    "request_latency_p95_seconds": 'histogram_quantile(0.95, sum(rate(patient_service_request_duration_seconds_bucket{namespace="hospital"}[2m])) by (le))',
}


def query_prometheus(base_url: str, expression: str) -> float | None:
    params = urllib.parse.urlencode({"query": expression})
    request = urllib.request.Request(f"{base_url.rstrip('/')}/api/v1/query?{params}")
    with urllib.request.urlopen(request, timeout=15) as response:
        payload = json.load(response)
    results = payload.get("data", {}).get("result", [])
    if not results:
        return None
    try:
        return float(results[0]["value"][1])
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def collect(prometheus_url: str, output: Path, duration: int, interval: int) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = ["timestamp_utc", "elapsed_seconds", *QUERIES.keys()]
    started = time.monotonic()
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        while time.monotonic() - started <= duration:
            row = {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "elapsed_seconds": round(time.monotonic() - started, 2),
            }
            for name, expression in QUERIES.items():
                try:
                    value = query_prometheus(prometheus_url, expression)
                except OSError as error:
                    print(f"warning: query failed for {name}: {error}")
                    value = None
                row[name] = "" if value is None else value
            writer.writerow(row)
            handle.flush()
            print(json.dumps(row), flush=True)
            remaining = interval - (time.monotonic() - started - row["elapsed_seconds"])
            if remaining > 0:
                time.sleep(remaining)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prometheus-url", default="http://127.0.0.1:9090")
    parser.add_argument("--output", type=Path, default=Path("ml/data/raw_metrics.csv"))
    parser.add_argument("--duration-seconds", type=int, default=1800)
    parser.add_argument("--interval-seconds", type=int, default=15)
    args = parser.parse_args()
    if args.duration_seconds <= 0 or args.interval_seconds <= 0:
        parser.error("duration and interval must be positive")
    collect(args.prometheus_url, args.output, args.duration_seconds, args.interval_seconds)


if __name__ == "__main__":
    main()
