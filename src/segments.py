"""Viewer segmentation adapters for Day 9 Streamlit UI."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.executive import user_engagement_data

SEGMENT_ORDER = [
    "Binge Watcher",
    "Casual Viewer",
    "Weekend Viewer",
    "Documentary Fan",
    "At-Risk Viewer",
]

SEGMENT_DESCRIPTIONS = {
    "Binge Watcher": "High session frequency and deep completion across episodes.",
    "Casual Viewer": "Light-to-moderate viewing with selective completion behavior.",
    "Weekend Viewer": "Usage spikes around weekends with concentrated session windows.",
    "Documentary Fan": "Strong preference for documentary content with steady completion.",
    "At-Risk Viewer": "Low engagement and completion patterns linked to churn risk.",
}

SUMMARY_FILE_CANDIDATES = [
    Path("data/processed/viewer_segment_summary.csv"),
    Path("data/processed/viewer_segments_summary.csv"),
]

ASSIGNMENT_FILE_CANDIDATES = [
    Path("data/processed/viewer_segments.csv"),
    Path("data/processed/viewer_segmentation.csv"),
    Path("data/processed/segment_assignments.csv"),
    Path("data/processed/viewer_clusters.csv"),
]


def _segment_column_name(frame: pd.DataFrame) -> str | None:
    for candidate in ("segment", "segment_name", "viewer_segment", "cluster_label", "persona", "viewer_persona"):
        if candidate in frame.columns:
            return candidate
    return None


def _standardize_segment_name(name: object) -> str:
    text = str(name).strip().lower()
    aliases = {
        "binge watcher": "Binge Watcher",
        "casual viewer": "Casual Viewer",
        "weekend viewer": "Weekend Viewer",
        "documentary fan": "Documentary Fan",
        "at-risk viewer": "At-Risk Viewer",
        "at risk viewer": "At-Risk Viewer",
    }
    return aliases.get(text, str(name).strip())


def _align_segment_rows(summary: pd.DataFrame) -> pd.DataFrame:
    base = pd.DataFrame({"segment_name": SEGMENT_ORDER})
    merged = base.merge(summary, on="segment_name", how="left")
    merged["user_count"] = merged["user_count"].fillna(0).astype(int)
    merged["engagement_score"] = merged["engagement_score"].fillna(0.0)
    merged["retention_rate"] = merged["retention_rate"].fillna(0.0)
    merged["description"] = merged["segment_name"].map(SEGMENT_DESCRIPTIONS)
    return merged


def _summary_from_file(frame: pd.DataFrame) -> pd.DataFrame | None:
    segment_col = _segment_column_name(frame)
    if segment_col is None:
        return None

    user_col = next((name for name in ("user_count", "users", "num_users", "count") if name in frame.columns), None)
    engagement_col = next(
        (name for name in ("engagement_score", "avg_engagement_score", "engagement") if name in frame.columns), None
    )
    retention_col = next((name for name in ("retention_rate", "avg_retention_rate", "retained_rate") if name in frame.columns), None)
    if user_col is None or engagement_col is None or retention_col is None:
        return None

    summary = frame[[segment_col, user_col, engagement_col, retention_col]].copy()
    summary.columns = ["segment_name", "user_count", "engagement_score", "retention_rate"]
    summary["segment_name"] = summary["segment_name"].map(_standardize_segment_name)
    return _align_segment_rows(summary)


def _summary_from_assignments(subscribers: pd.DataFrame, activity: pd.DataFrame, frame: pd.DataFrame) -> pd.DataFrame | None:
    segment_col = _segment_column_name(frame)
    if segment_col is None or "user_id" not in frame.columns:
        return None

    assignments = frame[["user_id", segment_col]].copy()
    assignments.columns = ["user_id", "segment_name"]
    assignments["segment_name"] = assignments["segment_name"].map(_standardize_segment_name)

    retained = subscribers[["user_id", "retention_status"]].copy()
    retained["is_retained"] = retained["retention_status"].eq("Retained")
    engagement = user_engagement_data(subscribers, activity)[["user_id", "engagement_score"]]

    joined = assignments.merge(retained[["user_id", "is_retained"]], on="user_id", how="left")
    joined = joined.merge(engagement, on="user_id", how="left")
    summary = joined.groupby("segment_name", as_index=False).agg(
        user_count=("user_id", "nunique"),
        engagement_score=("engagement_score", "mean"),
        retention_rate=("is_retained", "mean"),
    )
    summary["retention_rate"] = summary["retention_rate"].fillna(0.0) * 100
    summary["engagement_score"] = summary["engagement_score"].fillna(0.0)
    return _align_segment_rows(summary)


def load_viewer_segment_summary(
    project_root: Path, subscribers: pd.DataFrame, activity: pd.DataFrame
) -> tuple[pd.DataFrame | None, str, list[str]]:
    """Load Person 2 segmentation output, with explicit interim fallback messaging."""
    read_errors: list[str] = []

    for relative_path in SUMMARY_FILE_CANDIDATES:
        path = project_root / relative_path
        if not path.exists():
            continue
        try:
            summary_frame = pd.read_csv(path)
        except (OSError, pd.errors.ParserError) as error:
            read_errors.append(f"{relative_path}: {error}")
            continue
        summary = _summary_from_file(summary_frame)
        if summary is not None:
            return summary, f"Source: {relative_path}", read_errors
        read_errors.append(f"{relative_path}: required summary columns not found")

    for relative_path in ASSIGNMENT_FILE_CANDIDATES:
        path = project_root / relative_path
        if not path.exists():
            continue
        try:
            assignments_frame = pd.read_csv(path)
        except (OSError, pd.errors.ParserError) as error:
            read_errors.append(f"{relative_path}: {error}")
            continue
        summary = _summary_from_assignments(subscribers, activity, assignments_frame)
        if summary is not None:
            return summary, f"Source: {relative_path}", read_errors
        read_errors.append(f"{relative_path}: required assignment columns not found")

    if "viewer_persona" in subscribers.columns:
        fallback = subscribers[["user_id", "viewer_persona"]].rename(columns={"viewer_persona": "segment_name"})
        summary = _summary_from_assignments(subscribers, activity, fallback)
        if summary is not None:
            return summary, "Source: subscriber_data.csv (interim persona labels until Person 2 export is connected)", read_errors

    return None, "No segmentation output detected.", read_errors
