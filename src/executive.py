"""Small presentation-ready KPI helpers for the executive dashboard."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ExecutiveKpis:
    """The six headline measures shown on the Overview page."""

    total_viewers: int
    retention_rate: float
    churn_rate: float
    average_watch_duration: float
    average_completion_rate: float
    engagement_score: float


def user_engagement_data(subscribers: pd.DataFrame, activity: pd.DataFrame) -> pd.DataFrame:
    """Create viewer-level engagement inputs for executive visualisations.

    This transparent interim calculation follows the agreed project weighting:
    40% completion, 40% average watch duration, and 20% session frequency.
    It can be replaced later by Person 2's KPI service without changing the UI.
    """
    grouped = activity.groupby("user_id", as_index=False).agg(
        average_watch_duration=("watch_duration_minutes", "mean"),
        average_completion_rate=("completion_rate", "mean"),
        session_frequency=("activity_id", "count"),
    )
    result = subscribers[["user_id", "retention_status"]].merge(grouped, on="user_id", how="inner")
    duration_score = (result["average_watch_duration"] / 60 * 100).clip(0, 100)
    frequency_score = (result["session_frequency"] / 15 * 100).clip(0, 100)
    result["engagement_score"] = (
        result["average_completion_rate"] * 0.4 + duration_score * 0.4 + frequency_score * 0.2
    )
    return result


def calculate_executive_kpis(subscribers: pd.DataFrame, activity: pd.DataFrame) -> ExecutiveKpis:
    """Calculate headline metrics for the currently filtered dashboard data."""
    total_viewers = int(subscribers["user_id"].nunique())
    retention_rate = float(subscribers["retention_status"].eq("Retained").mean() * 100) if total_viewers else 0.0
    user_data = user_engagement_data(subscribers, activity)
    engagement_score = float(user_data["engagement_score"].mean()) if not user_data.empty else 0.0
    return ExecutiveKpis(
        total_viewers=total_viewers,
        retention_rate=retention_rate,
        churn_rate=100 - retention_rate,
        average_watch_duration=float(activity["watch_duration_minutes"].mean()) if not activity.empty else 0.0,
        average_completion_rate=float(activity["completion_rate"].mean()) if not activity.empty else 0.0,
        engagement_score=engagement_score,
    )
