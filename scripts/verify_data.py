"""Verify the generated analytics datasets and print a compact readiness summary."""

from __future__ import annotations

from pathlib import Path

from src.validation import validate_datasets

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"


if __name__ == "__main__":
    valid, issues = validate_datasets(RAW_DATA_DIR)
    if valid:
        print("Data readiness check: PASS")
        print("All expected CSV files are present, valid, and internally consistent.")
    else:
        print("Data readiness check: FAIL")
        for issue in issues:
            print(f"- {issue}")
