"""Verify the generated analytics datasets and print a compact readiness summary."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.validation import validate_datasets

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
