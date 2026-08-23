"""Helpers for Content Analytics KPI and table outputs."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ContentKpis:
    """Headline metrics for the Content Analytics page."""

    total_shows: int
    average_rating: float
    average_completion: float
    average_watch_duration: float


def content_session_metrics(activity: pd.DataFrame, content: pd.DataFrame, subscribers: pd.DataFrame) -> pd.DataFrame:
    """Aggregate show-level performance metrics from filtered dashboard inputs."""
    joined = activity.merge(content[["show_id", "title", "genre", "rating"]], on="show_id", how="inner")
    joined = joined.merge(subscribers[["user_id", "retention_status"]], on="user_id", how="inner")
    joined["is_retained"] = joined["retention_status"].eq("Retained")
    metrics = joined.groupby(["show_id", "title", "genre", "rating"], as_index=False).agg(
        average_watch=("watch_duration_minutes", "mean"),
        average_completion=("completion_rate", "mean"),
        retention_rate=("is_retained", "mean"),
        sessions=("activity_id", "count"),
    )
    metrics["retention_rate"] *= 100
    return metrics


def calculate_content_kpis(content_metrics: pd.DataFrame) -> ContentKpis:
    """Calculate KPI cards from show-level performance data."""
    if content_metrics.empty:
        return ContentKpis(0, 0.0, 0.0, 0.0)

    return ContentKpis(
        total_shows=int(content_metrics["show_id"].nunique()),
        average_rating=float(content_metrics["rating"].mean()),
        average_completion=float(content_metrics["average_completion"].mean()),
        average_watch_duration=float(content_metrics["average_watch"].mean()),
    )


def build_content_ranking_table(content_metrics: pd.DataFrame) -> pd.DataFrame:
    """Build ranked show table required by the Content Analytics page."""
    ranking = content_metrics.sort_values(
        by=["retention_rate", "average_completion", "average_watch", "rating"],
        ascending=False,
    ).copy()
    ranking["Rank"] = range(1, len(ranking) + 1)
    ranking = ranking.rename(
        columns={
            "title": "Show",
            "genre": "Genre",
            "average_watch": "Avg Watch",
            "average_completion": "Completion",
            "retention_rate": "Retention",
            "rating": "Rating",
        }
    )
    ranking = ranking[["Rank", "Show", "Genre", "Avg Watch", "Completion", "Retention", "Rating"]]
    ranking["Avg Watch"] = ranking["Avg Watch"].round(1)
    ranking["Completion"] = ranking["Completion"].round(1)
    ranking["Retention"] = ranking["Retention"].round(1)
    ranking["Rating"] = ranking["Rating"].round(1)
    return ranking
