"""Reusable viewer, KPI, and content analytics for StreamSense AI.

The functions in this module accept DataFrames so that analytics can run against
Person 1's validated raw CSV inputs when they become available, without owning
or changing the data pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


ENGAGEMENT_WEIGHTS = {
    "completion_rate": 0.35,
    "average_watch_duration": 0.30,
    "session_frequency": 0.25,
    "pause_frequency": 0.10,
}


@dataclass(frozen=True)
class CoreKpis:
    """Headline KPIs calculated once per unique viewer."""

    total_viewers: int
    retention_rate: float
    churn_rate: float
    average_watch_duration: float
    average_completion_rate: float
    average_engagement_score: float


@dataclass(frozen=True)
class ContentAnalytics:
    """Show-level and genre-level content performance tables."""

    show_performance: pd.DataFrame
    genre_performance: pd.DataFrame


def _require_columns(frame: pd.DataFrame, columns: Iterable[str], frame_name: str) -> None:
    missing = sorted(set(columns).difference(frame.columns))
    if missing:
        raise ValueError(f"{frame_name} is missing required columns: {', '.join(missing)}")


def _safe_mean(series: pd.Series) -> float:
    value = pd.to_numeric(series, errors="coerce").mean()
    return float(value) if pd.notna(value) else 0.0


def calculate_engagement_score(
    average_watch_duration: pd.Series,
    average_completion_rate: pd.Series,
    session_frequency: pd.Series,
    average_pause_count: pd.Series,
) -> pd.Series:
    """Return a transparent 0--100 engagement score.

    Completion, average watch duration, and frequency are positive signals.
    Pause frequency is a smaller inverse friction signal. Duration and frequency
    are capped at 60 minutes and 15 sessions respectively so unusually active
    viewers do not dominate the score. Missing behavioural inputs remain missing.
    """
    inputs = pd.concat(
        [
            pd.to_numeric(average_watch_duration, errors="coerce"),
            pd.to_numeric(average_completion_rate, errors="coerce"),
            pd.to_numeric(session_frequency, errors="coerce"),
            pd.to_numeric(average_pause_count, errors="coerce"),
        ],
        axis=1,
    )
    inputs.columns = ["watch", "completion", "frequency", "pauses"]
    valid = inputs.notna().all(axis=1)

    score = (
        inputs["completion"].clip(0, 100) * ENGAGEMENT_WEIGHTS["completion_rate"]
        + (inputs["watch"].clip(0, 60) / 60 * 100) * ENGAGEMENT_WEIGHTS["average_watch_duration"]
        + (inputs["frequency"].clip(0, 15) / 15 * 100) * ENGAGEMENT_WEIGHTS["session_frequency"]
        + (100 - inputs["pauses"].clip(0, 8) / 8 * 100) * ENGAGEMENT_WEIGHTS["pause_frequency"]
    )
    return score.where(valid).clip(0, 100).rename("engagement_score")


def _category(series: pd.Series, bins: list[float], labels: list[str]) -> pd.Series:
    return pd.cut(pd.to_numeric(series, errors="coerce"), bins=bins, labels=labels, include_lowest=True)


def build_viewer_analytics(
    subscribers: pd.DataFrame, activity: pd.DataFrame, content: pd.DataFrame | None = None
) -> pd.DataFrame:
    """Build one row per subscriber with behavioural, retention, and preference features."""
    _require_columns(subscribers, ["user_id", "retention_status"], "subscribers")
    _require_columns(
        activity,
        ["user_id", "activity_id", "watch_duration_minutes", "completion_rate", "pause_count", "device"],
        "activity",
    )

    session_data = activity.copy()
    for column in ("watch_duration_minutes", "completion_rate", "pause_count"):
        session_data[column] = pd.to_numeric(session_data[column], errors="coerce")

    usage = session_data.groupby("user_id", as_index=False).agg(
        total_watch_duration=("watch_duration_minutes", "sum"),
        average_watch_duration=("watch_duration_minutes", "mean"),
        average_completion_rate=("completion_rate", "mean"),
        average_pause_count=("pause_count", "mean"),
        session_frequency=("activity_id", "nunique"),
    )
    result = subscribers[["user_id", "retention_status"]].drop_duplicates("user_id").merge(usage, on="user_id", how="left")
    result["retention_status"] = result["retention_status"].astype("string").str.strip()
    result["churn_status"] = np.where(
        result["retention_status"].eq("Churned"), "Churned", np.where(result["retention_status"].eq("Retained"), "Not churned", pd.NA)
    )

    device_counts = session_data.groupby(["user_id", "device"], dropna=True)["activity_id"].nunique().reset_index(name="sessions")
    if not device_counts.empty:
        primary_device = device_counts.sort_values(["user_id", "sessions", "device"], ascending=[True, False, True]).drop_duplicates("user_id")
        result = result.merge(primary_device[["user_id", "device"]].rename(columns={"device": "primary_device"}), on="user_id", how="left")
    else:
        result["primary_device"] = pd.NA

    result["primary_genre"] = pd.NA
    if content is not None:
        _require_columns(content, ["show_id", "genre"], "content")
        _require_columns(activity, ["show_id"], "activity")
        genre_counts = session_data.merge(content[["show_id", "genre"]], on="show_id", how="inner").groupby(
            ["user_id", "genre"], dropna=True
        )["activity_id"].nunique().reset_index(name="sessions")
        if not genre_counts.empty:
            primary_genre = genre_counts.sort_values(["user_id", "sessions", "genre"], ascending=[True, False, True]).drop_duplicates("user_id")
            result = result.drop(columns="primary_genre").merge(
                primary_genre[["user_id", "genre"]].rename(columns={"genre": "primary_genre"}), on="user_id", how="left"
            )

    result["engagement_score"] = calculate_engagement_score(
        result["average_watch_duration"], result["average_completion_rate"], result["session_frequency"], result["average_pause_count"]
    )
    result["engagement_level"] = _category(result["engagement_score"], [-np.inf, 45, 70, np.inf], ["Low", "Medium", "High"])
    result["watch_duration_category"] = _category(
        result["average_watch_duration"], [-np.inf, 20, 40, np.inf], ["Short", "Medium", "Long"]
    )
    result["completion_category"] = _category(
        result["average_completion_rate"], [-np.inf, 50, 75, np.inf], ["Low", "Medium", "High"]
    )
    return result


def calculate_core_kpis(viewer_analytics: pd.DataFrame) -> CoreKpis:
    """Calculate KPI values from a one-row-per-viewer analytics table."""
    _require_columns(
        viewer_analytics,
        ["user_id", "retention_status", "average_watch_duration", "average_completion_rate", "engagement_score"],
        "viewer_analytics",
    )
    viewers = viewer_analytics.drop_duplicates("user_id")
    total = len(viewers)
    retained = viewers["retention_status"].eq("Retained")
    retention_rate = float(retained.mean() * 100) if total else 0.0
    return CoreKpis(
        total_viewers=total,
        retention_rate=retention_rate,
        churn_rate=float(viewers["retention_status"].eq("Churned").mean() * 100) if total else 0.0,
        average_watch_duration=_safe_mean(viewers["average_watch_duration"]),
        average_completion_rate=_safe_mean(viewers["average_completion_rate"]),
        average_engagement_score=_safe_mean(viewers["engagement_score"]),
    )


def retention_breakdown(
    subscribers: pd.DataFrame, activity: pd.DataFrame, dimension: str, content: pd.DataFrame | None = None
) -> pd.DataFrame:
    """Calculate historical retention by genre, device, or subscription type without double-counting viewers per group."""
    _require_columns(subscribers, ["user_id", "retention_status"], "subscribers")
    retained = subscribers[["user_id", "retention_status"]].drop_duplicates("user_id").copy()
    retained["is_retained"] = retained["retention_status"].eq("Retained")

    if dimension == "subscription_plan":
        _require_columns(subscribers, ["subscription_plan"], "subscribers")
        grouped = retained.merge(subscribers[["user_id", "subscription_plan"]].drop_duplicates("user_id"), on="user_id", how="left")
    elif dimension == "device":
        _require_columns(activity, ["user_id", "device"], "activity")
        grouped = activity[["user_id", "device"]].drop_duplicates().merge(retained, on="user_id", how="inner")
    elif dimension == "genre":
        if content is None:
            raise ValueError("content is required for a genre breakdown")
        _require_columns(activity, ["user_id", "show_id"], "activity")
        _require_columns(content, ["show_id", "genre"], "content")
        grouped = activity[["user_id", "show_id"]].merge(content[["show_id", "genre"]], on="show_id", how="inner").drop_duplicates(["user_id", "genre"])
        grouped = grouped.merge(retained, on="user_id", how="inner")
    else:
        raise ValueError("dimension must be one of: genre, device, subscription_plan")

    return grouped.groupby(dimension, dropna=False, as_index=False).agg(
        viewers=("user_id", "nunique"), retention_rate=("is_retained", "mean")
    ).assign(retention_rate=lambda frame: frame["retention_rate"] * 100).sort_values("retention_rate", ascending=False)


def build_content_analytics(subscribers: pd.DataFrame, content: pd.DataFrame, activity: pd.DataFrame) -> ContentAnalytics:
    """Return descriptive show and genre metrics, including observed retention associations."""
    _require_columns(subscribers, ["user_id", "retention_status"], "subscribers")
    _require_columns(content, ["show_id", "title", "genre", "rating"], "content")
    _require_columns(activity, ["activity_id", "user_id", "show_id", "watch_duration_minutes", "completion_rate"], "activity")
    joined = activity.merge(content[["show_id", "title", "genre", "rating"]], on="show_id", how="inner")
    joined = joined.merge(subscribers[["user_id", "retention_status"]].drop_duplicates("user_id"), on="user_id", how="inner")
    for column in ("rating", "watch_duration_minutes", "completion_rate"):
        joined[column] = pd.to_numeric(joined[column], errors="coerce")
    joined["is_retained"] = joined["retention_status"].eq("Retained")
    shows = joined.groupby(["show_id", "title", "genre", "rating"], as_index=False, dropna=False).agg(
        sessions=("activity_id", "nunique"), viewers=("user_id", "nunique"), average_watch_duration=("watch_duration_minutes", "mean"),
        average_completion_rate=("completion_rate", "mean"), retention_rate=("is_retained", "mean"),
    )
    shows["retention_rate"] *= 100
    if not shows.empty:
        shows["engagement_score"] = 0.6 * shows["average_completion_rate"].clip(0, 100) + 0.4 * (shows["average_watch_duration"].clip(0, 60) / 60 * 100)
        low, high = shows["engagement_score"].quantile([0.25, 0.75])
        shows["engagement_band"] = np.select(
            [shows["engagement_score"].le(low), shows["engagement_score"].ge(high)], ["Lower observed engagement", "Higher observed engagement"], default="Typical observed engagement"
        )
    else:
        shows["engagement_score"] = pd.Series(dtype=float)
        shows["engagement_band"] = pd.Series(dtype="string")

    genre_usage = joined.groupby("genre", as_index=False).agg(
        average_watch_duration=("watch_duration_minutes", "mean"), average_completion_rate=("completion_rate", "mean")
    )
    genre_viewers = joined[["user_id", "genre", "is_retained"]].drop_duplicates(["user_id", "genre"]).groupby("genre", as_index=False).agg(
        viewers=("user_id", "nunique"), retention_rate=("is_retained", "mean")
    )
    genre_shows = shows.groupby("genre", as_index=False).agg(
        shows=("show_id", "nunique"), average_rating=("rating", "mean"), average_engagement_score=("engagement_score", "mean")
    )
    genres = genre_usage.merge(genre_viewers, on="genre", how="outer").merge(genre_shows, on="genre", how="outer")
    genres["retention_rate"] *= 100
    return ContentAnalytics(show_performance=shows, genre_performance=genres)
