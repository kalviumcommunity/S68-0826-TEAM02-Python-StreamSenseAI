"""Plotly chart builders for the StreamSense AI dashboard."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
from plotly.graph_objects import Figure

from src.content import content_session_metrics
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


def watch_duration_distribution(activity: pd.DataFrame) -> Figure:
    """Show the spread of watch duration across all filtered sessions."""
    fig = px.histogram(
        activity,
        x="watch_duration_minutes",
        nbins=28,
        labels={"watch_duration_minutes": "Watch duration (minutes)", "count": "Sessions"},
        title="Watch duration distribution",
        color_discrete_sequence=[PRIMARY],
    )
    fig.update_layout(**CHART_LAYOUT, bargap=0.05)
    return fig


def completion_distribution(activity: pd.DataFrame) -> Figure:
    """Show completion-rate distribution to highlight drop-off concentration."""
    fig = px.histogram(
        activity,
        x="completion_rate",
        nbins=25,
        labels={"completion_rate": "Completion rate (%)", "count": "Sessions"},
        title="Completion distribution",
        color_discrete_sequence=[ACCENT],
    )
    fig.update_layout(**CHART_LAYOUT, bargap=0.05, xaxis_range=[0, 100])
    return fig


def pause_vs_completion(activity: pd.DataFrame) -> Figure:
    """Plot pause frequency against completion to detect friction patterns."""
    fig = px.scatter(
        activity,
        x="pause_count",
        y="completion_rate",
        color="watch_duration_minutes",
        color_continuous_scale="Teal",
        opacity=0.65,
        labels={
            "pause_count": "Pause count",
            "completion_rate": "Completion rate (%)",
            "watch_duration_minutes": "Watch duration (minutes)",
        },
        title="Pause count versus completion",
    )
    fig.update_layout(**CHART_LAYOUT, yaxis_range=[0, 100], coloraxis_colorbar_title="Watch duration")
    return fig


def viewing_by_device(activity: pd.DataFrame) -> Figure:
    """Compare session volume and completion outcomes across devices."""
    summary = activity.groupby("device", as_index=False).agg(
        sessions=("activity_id", "count"),
        average_completion=("completion_rate", "mean"),
    )
    summary = summary.sort_values("sessions", ascending=False)
    fig = px.bar(
        summary,
        x="device",
        y="sessions",
        color="average_completion",
        color_continuous_scale="Blues",
        labels={"device": "Device", "sessions": "Viewing sessions", "average_completion": "Avg. completion (%)"},
        title="Viewing by device",
    )
    fig.update_layout(**CHART_LAYOUT, coloraxis_colorbar_title="Completion")
    return fig


def content_genre_performance(activity: pd.DataFrame, content: pd.DataFrame, subscribers: pd.DataFrame) -> Figure:
    """Compare genre-level completion and retention performance."""
    metrics = content_session_metrics(activity, content, subscribers)
    summary = metrics.groupby("genre", as_index=False).agg(
        average_completion=("average_completion", "mean"),
        retention_rate=("retention_rate", "mean"),
        shows=("show_id", "nunique"),
    )
    summary = summary.sort_values("retention_rate", ascending=False)
    fig = px.bar(
        summary,
        x="genre",
        y="retention_rate",
        color="average_completion",
        color_continuous_scale="Teal",
        labels={
            "genre": "Genre",
            "retention_rate": "Retention rate (%)",
            "average_completion": "Avg. completion (%)",
        },
        title="Genre performance",
    )
    fig.update_layout(**CHART_LAYOUT, yaxis_ticksuffix="%", coloraxis_colorbar_title="Completion")
    return fig


def top_shows(activity: pd.DataFrame, content: pd.DataFrame, subscribers: pd.DataFrame, limit: int = 10) -> Figure:
    """Show top titles ranked by retention and completion outcomes."""
    metrics = content_session_metrics(activity, content, subscribers)
    ranked = metrics.sort_values(
        by=["retention_rate", "average_completion", "average_watch", "rating"],
        ascending=False,
    ).head(limit)
    ranked = ranked.sort_values("retention_rate", ascending=True)
    fig = px.bar(
        ranked,
        x="retention_rate",
        y="title",
        orientation="h",
        color="average_completion",
        color_continuous_scale="Blues",
        labels={
            "retention_rate": "Retention rate (%)",
            "title": "Show",
            "average_completion": "Avg. completion (%)",
        },
        title="Top shows",
    )
    fig.update_layout(**CHART_LAYOUT, xaxis_ticksuffix="%", coloraxis_colorbar_title="Completion")
    return fig


def rating_vs_retention(activity: pd.DataFrame, content: pd.DataFrame, subscribers: pd.DataFrame) -> Figure:
    """Evaluate whether higher-rated titles are retaining viewers better."""
    metrics = content_session_metrics(activity, content, subscribers)
    fig = px.scatter(
        metrics,
        x="rating",
        y="retention_rate",
        size="sessions",
        color="genre",
        hover_name="title",
        size_max=26,
        labels={"rating": "Rating", "retention_rate": "Retention rate (%)", "sessions": "Viewing sessions"},
        title="Rating versus retention",
    )
    fig.update_layout(**CHART_LAYOUT, yaxis_ticksuffix="%", yaxis_range=[0, 100])
    return fig


def episode_completion_by_genre(activity: pd.DataFrame, content: pd.DataFrame, subscribers: pd.DataFrame) -> Figure:
    """Compare episode completion rates by genre."""
    metrics = content_session_metrics(activity, content, subscribers)
    summary = metrics.groupby("genre", as_index=False).agg(average_completion=("average_completion", "mean"))
    summary = summary.sort_values("average_completion", ascending=False)
    fig = px.bar(
        summary,
        x="genre",
        y="average_completion",
        color="average_completion",
        color_continuous_scale="Viridis",
        labels={"genre": "Genre", "average_completion": "Average completion rate (%)"},
        title="Episode completion by genre",
    )
    fig.update_layout(**CHART_LAYOUT, yaxis_ticksuffix="%", yaxis_range=[0, 100], coloraxis_showscale=False)
    return fig


def retention_correlation_heatmap(features: pd.DataFrame) -> Figure:
    """Show feature relationships connected to retention outcomes."""
    correlation_input = features[
        [
            "watch_duration",
            "session_duration",
            "completion_rate",
            "pause_count",
            "engagement_score",
            "retention",
            "churn_probability",
        ]
    ].copy()
    correlation_matrix = correlation_input.corr(numeric_only=True)
    labels = {
        "watch_duration": "Watch Duration",
        "session_duration": "Session Duration",
        "completion_rate": "Completion Rate",
        "pause_count": "Pause Count",
        "engagement_score": "Engagement Score",
        "retention": "Retention",
        "churn_probability": "Churn Probability",
    }
    correlation_matrix = correlation_matrix.rename(index=labels, columns=labels)
    fig = px.imshow(
        correlation_matrix,
        text_auto=".2f",
        color_continuous_scale="RdBu",
        zmin=-1,
        zmax=1,
        title="Correlation heatmap",
    )
    fig.update_layout(**CHART_LAYOUT, coloraxis_colorbar_title="Correlation")
    return fig


def retention_by_viewer_segment_chart(segment_summary: pd.DataFrame) -> Figure:
    """Compare retention rates across viewer segments."""
    summary = segment_summary.sort_values("retention_rate", ascending=False)
    fig = px.bar(
        summary,
        x="segment_name",
        y="retention_rate",
        color="engagement_score",
        color_continuous_scale="Teal",
        labels={
            "segment_name": "Viewer segment",
            "retention_rate": "Retention rate (%)",
            "engagement_score": "Engagement score",
        },
        title="Retention by viewer segment",
    )
    fig.update_layout(**CHART_LAYOUT, yaxis_ticksuffix="%", coloraxis_colorbar_title="Engagement")
    return fig


def pause_frequency_vs_completion(features: pd.DataFrame) -> Figure:
    """Relate pause frequency to completion at the viewer level."""
    fig = px.scatter(
        features,
        x="pause_count",
        y="completion_rate",
        color="retention_status",
        size="watch_duration",
        size_max=22,
        opacity=0.7,
        color_discrete_map={"Retained": ACCENT, "Churned": "#f97316"},
        labels={
            "pause_count": "Average pause count",
            "completion_rate": "Average completion rate (%)",
            "watch_duration": "Average watch duration (minutes)",
            "retention_status": "Retention status",
        },
        title="Pause frequency versus completion",
    )
    fig.update_layout(**CHART_LAYOUT, yaxis_range=[0, 100])
    return fig
