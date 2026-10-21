#!/usr/bin/env python3
"""Train a persistence baseline and optional LSTM workload predictor."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error


def make_windows(values: np.ndarray, window: int) -> tuple[np.ndarray, np.ndarray]:
    features = []
    targets = []
    for index in range(window, len(values)):
        features.append(values[index - window : index])
        targets.append(values[index])
    return np.asarray(features), np.asarray(targets)


def load_workload(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = {"timestamp_utc", "workload_rps"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
    frame["timestamp_utc"] = pd.to_datetime(frame["timestamp_utc"], utc=True, errors="coerce")
    frame["workload_rps"] = pd.to_numeric(frame["workload_rps"], errors="coerce")
    frame = frame.dropna(subset=["timestamp_utc", "workload_rps"]).sort_values("timestamp_utc")
    frame["workload_rps"] = frame["workload_rps"].clip(lower=0.0)
    if len(frame) < 60:
        raise ValueError("At least 60 valid observations are required for chronological train/validation/test splits.")
    return frame.reset_index(drop=True)


def regression_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    return {
        "mae": float(mean_absolute_error(actual, predicted)),
        "rmse": float(np.sqrt(mean_squared_error(actual, predicted))),
    }


def train_baseline(frame: pd.DataFrame, output_dir: Path, window: int) -> dict:
    values = frame["workload_rps"].to_numpy(dtype=float)
    split = int(len(values) * 0.7)
    test_start = int(len(values) * 0.85)
    actual = values[test_start:]
    predicted = values[test_start - 1 : -1]
    metrics = regression_metrics(actual, predicted)
    predictions = pd.DataFrame({
        "timestamp_utc": frame["timestamp_utc"].iloc[test_start:].dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "actual_workload_rps": actual,
        "baseline_predicted_workload_rps": predicted,
    })
    predictions.to_csv(output_dir / "baseline_predictions.csv", index=False)
    return {"model": "persistence_baseline", "window": window, "train_rows": split, "test_rows": len(actual), **metrics}


def train_lstm(frame: pd.DataFrame, output_dir: Path, window: int, epochs: int, batch_size: int) -> dict:
    try:
        import tensorflow as tf
    except ImportError as error:
        raise RuntimeError("TensorFlow is not installed. Install ml/requirements-lstm.txt, preferably in WSL2 on Windows.") from error

    values = frame["workload_rps"].to_numpy(dtype=float)
    train_end = int(len(values) * 0.7)
    validation_end = int(len(values) * 0.85)
    minimum = values[:train_end].min()
    maximum = values[:train_end].max()
    scale = maximum - minimum
    if scale == 0:
        scale = 1.0
    normalized = (values - minimum) / scale
    all_x, all_y = make_windows(normalized, window)
    target_indices = np.arange(window, len(values))
    train_mask = target_indices < train_end
    validation_mask = (target_indices >= train_end) & (target_indices < validation_end)
    test_mask = target_indices >= validation_end
    x_train = all_x[train_mask][..., np.newaxis]
    y_train = all_y[train_mask]
    x_validation = all_x[validation_mask][..., np.newaxis]
    y_validation = all_y[validation_mask]
    x_test = all_x[test_mask][..., np.newaxis]
    y_test = all_y[test_mask]
    if not len(x_train) or not len(x_validation) or not len(x_test):
        raise ValueError("The dataset is too short for the requested window and chronological splits.")

    tf.random.set_seed(42)
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(window, 1)),
        tf.keras.layers.LSTM(32),
        tf.keras.layers.Dense(16, activation="relu"),
        tf.keras.layers.Dense(1),
    ])
    model.compile(optimizer="adam", loss="mse", metrics=["mae"])
    model.fit(
        x_train,
        y_train,
        validation_data=(x_validation, y_validation),
        epochs=epochs,
        batch_size=batch_size,
        verbose=1,
        callbacks=[tf.keras.callbacks.EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True)],
    )
    predicted_normalized = model.predict(x_test, verbose=0).reshape(-1)
    predicted = predicted_normalized * scale + minimum
    actual = y_test * scale + minimum
    model.save(output_dir / "lstm_workload.keras")
    predictions = pd.DataFrame({
        "timestamp_utc": frame["timestamp_utc"].iloc[target_indices[test_mask]].dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ").to_numpy(),
        "actual_workload_rps": actual,
        "lstm_predicted_workload_rps": predicted,
    })
    predictions.to_csv(output_dir / "lstm_predictions.csv", index=False)
    (output_dir / "lstm_scaler.json").write_text(json.dumps({"minimum": float(minimum), "maximum": float(maximum), "scale": float(scale)}), encoding="utf-8")
    return {"model": "lstm", "window": window, "epochs_requested": epochs, "train_rows": int(len(x_train)), "validation_rows": int(len(x_validation)), "test_rows": int(len(x_test)), **regression_metrics(actual, predicted)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("ml/data/clean_metrics.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("ml/models"))
    parser.add_argument("--window", type=int, default=12, help="Number of historical samples used per prediction")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--skip-lstm", action="store_true")
    args = parser.parse_args()
    if args.window < 2:
        parser.error("window must be at least 2")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    frame = load_workload(args.input)
    results = [train_baseline(frame, args.output_dir, args.window)]
    if not args.skip_lstm:
        results.append(train_lstm(frame, args.output_dir, args.window, args.epochs, args.batch_size))
    (args.output_dir / "metrics.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
