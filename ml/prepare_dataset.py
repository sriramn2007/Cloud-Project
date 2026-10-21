#!/usr/bin/env python3
"""Clean and validate Prometheus metrics for time-series modeling."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

NUMERIC_COLUMNS = [
    "elapsed_seconds",
    "workload_rps",
    "cpu_cores",
    "memory_bytes",
    "available_replicas",
    "desired_replicas",
    "hpa_current_replicas",
    "hpa_desired_replicas",
    "request_latency_p95_seconds",
]


def prepare(input_path: Path, output_path: Path, report_path: Path) -> dict:
    frame = pd.read_csv(input_path)
    required = {"timestamp_utc", *NUMERIC_COLUMNS}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    frame["timestamp_utc"] = pd.to_datetime(frame["timestamp_utc"], utc=True, errors="coerce")
    frame = frame.dropna(subset=["timestamp_utc"]).sort_values("timestamp_utc")
    for column in NUMERIC_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    missing_before = frame.isna().sum().to_dict()
    frame[NUMERIC_COLUMNS] = frame[NUMERIC_COLUMNS].interpolate(limit_direction="both")
    frame[NUMERIC_COLUMNS] = frame[NUMERIC_COLUMNS].fillna(0.0)
    frame["workload_rps"] = frame["workload_rps"].clip(lower=0.0)
    frame["cpu_cores"] = frame["cpu_cores"].clip(lower=0.0)
    frame["memory_bytes"] = frame["memory_bytes"].clip(lower=0.0)
    frame["timestamp_utc"] = frame["timestamp_utc"].dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)
    report = {
        "input": str(input_path),
        "output": str(output_path),
        "rows": int(len(frame)),
        "columns": list(frame.columns),
        "start_timestamp": frame["timestamp_utc"].iloc[0] if len(frame) else None,
        "end_timestamp": frame["timestamp_utc"].iloc[-1] if len(frame) else None,
        "missing_values_before_interpolation": missing_before,
        "missing_values_after_interpolation": {key: int(value) for key, value in frame.isna().sum().items()},
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("ml/data/raw_metrics.csv"))
    parser.add_argument("--output", type=Path, default=Path("ml/data/clean_metrics.csv"))
    parser.add_argument("--report", type=Path, default=Path("ml/data/data_quality.json"))
    args = parser.parse_args()
    print(json.dumps(prepare(args.input, args.output, args.report), indent=2))


if __name__ == "__main__":
    main()
