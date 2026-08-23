"""Retention feature builders for the Retention Insights dashboard page."""

from __future__ import annotations

import pandas as pd

from src.executive import user_engagement_data


def build_retention_features(subscribers: pd.DataFrame, activity: pd.DataFrame) -> pd.DataFrame:
    """Build user-level retention features from filtered dashboard inputs."""
    if subscribers.empty or activity.empty:
        return pd.DataFrame()

    session_duration = (
        activity.assign(watch_date=pd.to_datetime(activity["watch_date"], errors="coerce").dt.date)
        .dropna(subset=["watch_date"])
        .groupby(["user_id", "watch_date"], as_index=False)["watch_duration_minutes"]
        .sum()
        .groupby("user_id", as_index=False)["watch_duration_minutes"]
        .mean()
        .rename(columns={"watch_duration_minutes": "session_duration"})
    )
    usage = activity.groupby("user_id", as_index=False).agg(
        watch_duration=("watch_duration_minutes", "mean"),
        completion_rate=("completion_rate", "mean"),
        pause_count=("pause_count", "mean"),
    )
    engagement = user_engagement_data(subscribers, activity)[["user_id", "engagement_score"]]
    retained = subscribers[["user_id", "retention_status"]].copy()
    retained["retention"] = retained["retention_status"].eq("Retained").astype(int)

    result = retained.merge(usage, on="user_id", how="inner")
    result = result.merge(session_duration, on="user_id", how="left")
    result = result.merge(engagement, on="user_id", how="left")
    result["session_duration"] = result["session_duration"].fillna(result["watch_duration"])
    result["engagement_score"] = result["engagement_score"].fillna(0.0)

    watch_score = (result["watch_duration"] / 60 * 100).clip(0, 100)
    session_score = (result["session_duration"] / 75 * 100).clip(0, 100)
    pause_penalty = (result["pause_count"] / 8 * 100).clip(0, 100)
    retention_score = (
        result["engagement_score"] * 0.45
        + result["completion_rate"] * 0.25
        + watch_score * 0.15
        + session_score * 0.15
        - pause_penalty * 0.25
    ).clip(0, 100)
    result["churn_probability"] = (100 - retention_score).clip(0, 100)

    result["engagement_band"] = pd.cut(
        result["engagement_score"],
        bins=[-1, 45, 70, 101],
        labels=["Low Engagement", "Medium Engagement", "High Engagement"],
    )
    return result


def retention_by_engagement_band(features: pd.DataFrame) -> pd.DataFrame:
    """Return retention rates for high, medium, and low engagement groups."""
    order = ["High Engagement", "Medium Engagement", "Low Engagement"]
    summary = features.groupby("engagement_band", observed=False, as_index=False).agg(retention_rate=("retention", "mean"))
    summary["retention_rate"] = summary["retention_rate"].fillna(0.0) * 100
    summary["engagement_band"] = summary["engagement_band"].astype(str)
    summary = summary.set_index("engagement_band").reindex(order, fill_value=0).reset_index()
    return summary
