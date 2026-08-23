"""Plotly chart builders for the StreamSense AI dashboard."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
from plotly.graph_objects import Figure

from src.executive import user_engagement_data


PRIMARY = "#6d5dfc"
ACCENT = "#14b8a6"
WARNING = "#f59e0b"
CHART_LAYOUT = {"template": "plotly_white", "margin": {"l": 12, "r": 12, "t": 58, "b": 12}}


def retention_by_signup_cohort(subscribers: pd.DataFrame) -> Figure:
    """Show historical retention rate by the month in which users signed up."""
    cohort_data = subscribers.copy()
    cohort_data["signup_date"] = pd.to_datetime(cohort_data["signup_date"])
    cohort_data["signup_month"] = cohort_data["signup_date"].dt.to_period("M").dt.to_timestamp()
    cohort_data["is_retained"] = cohort_data["retention_status"].eq("Retained")
    summary = cohort_data.groupby("signup_month", as_index=False)["is_retained"].mean()
    summary["retention_rate"] = summary["is_retained"] * 100

    fig = px.line(
        summary,
        x="signup_month",
        y="retention_rate",
        markers=True,
        labels={"signup_month": "Signup month", "retention_rate": "Retention rate (%)"},
        title="Retention by subscriber cohort",
    )
    fig.update_traces(line_color=PRIMARY, marker_color=PRIMARY, line_width=3)
    fig.update_layout(**CHART_LAYOUT, yaxis_ticksuffix="%", yaxis_range=[0, 100])
    return fig


def watch_duration_trend(activity: pd.DataFrame) -> Figure:
    """Show average minutes watched by month."""
    trend_data = activity.copy()
    trend_data["watch_date"] = pd.to_datetime(trend_data["watch_date"])
    trend_data["month"] = trend_data["watch_date"].dt.to_period("M").dt.to_timestamp()
    summary = trend_data.groupby("month", as_index=False)["watch_duration_minutes"].mean()

    fig = px.bar(
        summary,
        x="month",
        y="watch_duration_minutes",
        labels={"month": "Viewing month", "watch_duration_minutes": "Average minutes watched"},
        title="Watch duration over time",
        color_discrete_sequence=[ACCENT],
    )
    fig.update_layout(**CHART_LAYOUT)
    return fig


def completion_rate_trend(activity: pd.DataFrame) -> Figure:
    """Show the average episode-completion rate by month."""
    trend_data = activity.copy()
    trend_data["watch_date"] = pd.to_datetime(trend_data["watch_date"])
    trend_data["month"] = trend_data["watch_date"].dt.to_period("M").dt.to_timestamp()
    summary = trend_data.groupby("month", as_index=False)["completion_rate"].mean()

    fig = px.line(
        summary,
        x="month",
        y="completion_rate",
        markers=True,
        labels={"month": "Viewing month", "completion_rate": "Average completion rate (%)"},
        title="Episode completion over time",
    )
    fig.update_traces(line_color=WARNING, marker_color=WARNING, line_width=3)
    fig.update_layout(**CHART_LAYOUT, yaxis_ticksuffix="%", yaxis_range=[0, 100])
    return fig


def genre_performance(activity: pd.DataFrame, content: pd.DataFrame, subscribers: pd.DataFrame) -> Figure:
    """Compare genre retention, weighted by the sessions viewers actually watched."""
    joined = activity.merge(content[["show_id", "genre"]], on="show_id", how="inner")
    joined = joined.merge(subscribers[["user_id", "retention_status"]], on="user_id", how="inner")
    joined["is_retained"] = joined["retention_status"].eq("Retained")
    summary = joined.groupby("genre", as_index=False).agg(
        retention_rate=("is_retained", "mean"),
        average_completion=("completion_rate", "mean"),
    )
    summary["retention_rate"] *= 100
    summary = summary.sort_values("retention_rate", ascending=True)

    fig = px.bar(
        summary,
        x="retention_rate",
        y="genre",
        orientation="h",
        color="average_completion",
        color_continuous_scale="Teal",
        labels={
            "retention_rate": "Retention rate (%)",
            "genre": "Genre",
            "average_completion": "Avg. completion (%)",
        },
        title="Genre performance: retention and completion",
    )
    fig.update_layout(**CHART_LAYOUT, xaxis_ticksuffix="%", coloraxis_colorbar_title="Completion")
    return fig


def engagement_vs_retention(subscribers: pd.DataFrame, activity: pd.DataFrame) -> Figure:
    """Show the relationship between each viewer's engagement and retained status."""
    user_data = user_engagement_data(subscribers, activity)
    fig = px.scatter(
        user_data,
        x="engagement_score",
        y="average_completion_rate",
        color="retention_status",
        size="session_frequency",
        size_max=18,
        opacity=0.72,
        color_discrete_map={"Retained": ACCENT, "Churned": "#f97316"},
        labels={
            "engagement_score": "Engagement score",
            "average_completion_rate": "Average completion rate (%)",
            "session_frequency": "Sessions",
            "retention_status": "Retention status",
        },
        title="Engagement versus retention",
    )
    fig.update_layout(**CHART_LAYOUT, xaxis_range=[0, 100], yaxis_range=[0, 100])
    return fig


def content_performance(activity: pd.DataFrame, content: pd.DataFrame, subscribers: pd.DataFrame) -> Figure:
    """Map content performance using completion, retention, ratings, and session volume."""
    joined = activity.merge(content[["show_id", "title", "genre", "rating"]], on="show_id", how="inner")
    joined = joined.merge(subscribers[["user_id", "retention_status"]], on="user_id", how="inner")
    joined["is_retained"] = joined["retention_status"].eq("Retained")
    summary = joined.groupby(["show_id", "title", "genre", "rating"], as_index=False).agg(
        average_completion=("completion_rate", "mean"),
        retention_rate=("is_retained", "mean"),
        sessions=("activity_id", "count"),
    )
    summary["retention_rate"] *= 100
    fig = px.scatter(
        summary,
        x="average_completion",
        y="retention_rate",
        size="sessions",
        color="genre",
        hover_name="title",
        size_max=26,
        labels={
            "average_completion": "Average completion (%)",
            "retention_rate": "Viewer retention (%)",
            "sessions": "Viewing sessions",
        },
        title="Content performance map",
    )
    fig.update_layout(**CHART_LAYOUT, xaxis_range=[0, 100], yaxis_range=[0, 100])
    return fig
