"""Dataset validation helpers for the StreamSense AI project."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

EXPECTED_COUNTS = {
    "subscriber_data.csv": 1_000,
    "content_metadata.csv": 100,
    "viewer_activity.csv": 10_000,
}


def validate_datasets(raw_data_dir: str | Path) -> tuple[bool, list[str]]:
    """Validate the raw CSV files used by the analytics pipeline.

    Returns a tuple of (is_valid, issues).
    """
    root = Path(raw_data_dir)
    issues: list[str] = []

    for filename, expected_count in EXPECTED_COUNTS.items():
        path = root / filename
        if not path.exists():
            issues.append(f"Missing file: {filename}")
            continue

        try:
            df = pd.read_csv(path)
        except Exception as exc:  # pragma: no cover - defensive validation
            issues.append(f"Unreadable CSV: {filename} ({exc})")
            continue

        if len(df) != expected_count:
            issues.append(f"{filename} has {len(df):,} rows, expected {expected_count:,}.")

    subscriber_path = root / "subscriber_data.csv"
    if subscriber_path.exists():
        try:
            subscribers = pd.read_csv(subscriber_path)
            required_cols = {
                "user_id",
                "country",
                "subscription_plan",
                "signup_date",
                "viewer_persona",
                "retention_status",
            }
            missing = required_cols.difference(subscribers.columns)
            if missing:
                issues.append(f"subscriber_data.csv is missing required columns: {sorted(missing)}")
            if not subscribers["user_id"].is_unique:
                issues.append("subscriber_data.csv contains duplicate user_id values.")
        except Exception as exc:  # pragma: no cover - defensive validation
            issues.append(f"Could not validate subscriber schema: {exc}")

    content_path = root / "content_metadata.csv"
    if content_path.exists():
        try:
            content = pd.read_csv(content_path)
            if not content["show_id"].is_unique:
                issues.append("content_metadata.csv contains duplicate show_id values.")
        except Exception as exc:  # pragma: no cover - defensive validation
            issues.append(f"Could not validate content schema: {exc}")

    activity_path = root / "viewer_activity.csv"
    if activity_path.exists():
        try:
            activity = pd.read_csv(activity_path)
            if not activity["activity_id"].is_unique:
                issues.append("viewer_activity.csv contains duplicate activity_id values.")
            if not activity["completion_rate"].between(0, 100).all():
                issues.append("viewer_activity.csv contains completion_rate values outside 0-100.")
            if (activity["watch_duration_minutes"] <= 0).any():
                issues.append("viewer_activity.csv contains non-positive watch_duration_minutes values.")
        except Exception as exc:  # pragma: no cover - defensive validation
            issues.append(f"Could not validate activity schema: {exc}")

    return not issues, issues
