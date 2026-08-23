"""KPI helpers for the Viewer Analytics dashboard page."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ViewerKpis:
    """Headline metrics for the Viewer Analytics page."""

    average_watch_duration: float
    average_session_duration: float
    completion_rate: float
    average_pause_count: float


def calculate_viewer_kpis(activity: pd.DataFrame) -> ViewerKpis:
    """Calculate viewer-level KPI cards from filtered activity sessions."""
    if activity.empty:
        return ViewerKpis(0.0, 0.0, 0.0, 0.0)

    per_day_sessions = (
        activity.assign(watch_date=pd.to_datetime(activity["watch_date"], errors="coerce").dt.date)
        .dropna(subset=["watch_date"])
        .groupby(["user_id", "watch_date"], as_index=False)["watch_duration_minutes"]
        .sum()
    )
    average_session_duration = (
        float(per_day_sessions["watch_duration_minutes"].mean()) if not per_day_sessions.empty else 0.0
    )

    return ViewerKpis(
        average_watch_duration=float(activity["watch_duration_minutes"].mean()),
        average_session_duration=average_session_duration,
        completion_rate=float(activity["completion_rate"].mean()),
        average_pause_count=float(activity["pause_count"].mean()),
    )
