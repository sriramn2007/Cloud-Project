from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FEATURES = ROOT / "data" / "uci" / "diabetic_data_features.csv"
TARGETS = ROOT / "data" / "uci" / "diabetic_data_targets.csv"

COMMON_FIELDS = [
    "encounter_index",
    "admission_type_id",
    "time_in_hospital",
    "num_lab_procedures",
    "num_procedures",
    "num_medications",
    "number_outpatient",
    "number_emergency",
    "number_inpatient",
    "readmitted",
]
DOCTOR_FIELDS = COMMON_FIELDS + [
    "age",
    "gender",
    "race",
    "medical_specialty",
    "diag_1",
    "diag_2",
    "diag_3",
    "number_diagnoses",
    "max_glu_serum",
    "A1Cresult",
    "diabetesMed",
]


def _read_rows(limit: int | None = None) -> list[dict[str, Any]]:
    if not FEATURES.exists() or not TARGETS.exists():
        raise FileNotFoundError("UCI dataset files are missing from data/uci")
    with FEATURES.open(newline="", encoding="utf-8") as feature_handle, TARGETS.open(newline="", encoding="utf-8") as target_handle:
        features = csv.DictReader(feature_handle)
        targets = csv.DictReader(target_handle)
        rows = []
        for index, (feature, target) in enumerate(zip(features, targets), start=1):
            row = {"encounter_index": index, **feature, **target}
            rows.append(row)
            if limit and len(rows) >= limit:
                break
        return rows


def _clean(row: dict[str, Any], fields: list[str]) -> dict[str, Any]:
    return {field: row.get(field, "") for field in fields}


def common_records(limit: int = 25) -> list[dict[str, Any]]:
    return [_clean(row, COMMON_FIELDS) for row in _read_rows(limit)]


def clinical_records(limit: int = 25) -> list[dict[str, Any]]:
    return [_clean(row, DOCTOR_FIELDS) for row in _read_rows(limit)]


def summary() -> dict[str, Any]:
    records = _read_rows()
    admissions = [float(row["time_in_hospital"]) for row in records if str(row.get("time_in_hospital", "")).isdigit()]
    readmitted = sum(1 for row in records if row.get("readmitted") == "<30")
    return {
        "dataset": "Diabetes 130-US Hospitals for Years 1999-2008",
        "source": "UCI Machine Learning Repository dataset 296",
        "license": "CC BY 4.0",
        "deidentified": True,
        "rows": len(records),
        "readmitted_under_30_days": readmitted,
        "average_length_of_stay_days": round(sum(admissions) / len(admissions), 2) if admissions else None,
    }
