#!/usr/bin/env python3
"""Compare trained workload predictors without generating synthetic observations."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metrics", type=Path, default=Path("ml/models/metrics.json"))
    parser.add_argument("--output", type=Path, default=Path("results/model-evaluation.json"))
    args = parser.parse_args()
    if not args.metrics.exists():
        raise SystemExit(f"Metrics file not found: {args.metrics}. Run train_models.py first.")
    records = json.loads(args.metrics.read_text(encoding="utf-8"))
    by_model = {item["model"]: item for item in records}
    baseline = by_model.get("persistence_baseline")
    lstm = by_model.get("lstm")
    result = {
        "source_metrics": str(args.metrics),
        "models": records,
        "comparison": None,
    }
    if baseline and lstm:
        result["comparison"] = {
            "mae_improvement_percent": round((baseline["mae"] - lstm["mae"]) / baseline["mae"] * 100, 2) if baseline["mae"] else 0.0,
            "rmse_improvement_percent": round((baseline["rmse"] - lstm["rmse"]) / baseline["rmse"] * 100, 2) if baseline["rmse"] else 0.0,
            "winner_by_mae": "lstm" if lstm["mae"] < baseline["mae"] else "persistence_baseline",
            "winner_by_rmse": "lstm" if lstm["rmse"] < baseline["rmse"] else "persistence_baseline",
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
