"""Focused tests for the DataFrame-first analytics feature layer."""

import math

import pandas as pd

from src.analytics_features import (
    build_content_analytics,
    build_viewer_analytics,
    calculate_core_kpis,
    calculate_engagement_score,
    retention_breakdown,
)


def _frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    subscribers = pd.DataFrame(
        {
            "user_id": ["u1", "u2", "u3"],
            "retention_status": ["Retained", "Churned", "Retained"],
            "subscription_plan": ["Premium", "Basic", "Premium"],
        }
    )
    activity = pd.DataFrame(
        {
            "activity_id": ["a1", "a2", "a3"],
            "user_id": ["u1", "u1", "u2"],
            "show_id": ["s1", "s2", "s1"],
            "watch_duration_minutes": [50, 40, 10],
            "completion_rate": [100, 80, 20],
            "pause_count": [0, 2, 6],
            "device": ["TV", "Mobile", "TV"],
        }
    )
    content = pd.DataFrame(
        {"show_id": ["s1", "s2"], "title": ["Show One", "Show Two"], "genre": ["Drama", "Comedy"], "rating": [8.0, 6.0]}
    )
    return subscribers, activity, content


def test_viewer_features_are_one_row_per_viewer_and_preserve_missing_behaviour() -> None:
    subscribers, activity, content = _frames()
    viewers = build_viewer_analytics(subscribers, activity, content)

    assert viewers["user_id"].is_unique
    u1 = viewers.set_index("user_id").loc["u1"]
    assert u1["total_watch_duration"] == 90
    assert u1["session_frequency"] == 2
    assert u1["primary_device"] == "Mobile"  # deterministic alphabetical tie-break
    assert u1["primary_genre"] == "Comedy"
    assert viewers.set_index("user_id").loc["u3", "engagement_score"] != viewers.set_index("user_id").loc["u3", "engagement_score"]


def test_engagement_score_is_interpretable_bounded_and_does_not_invent_missing_values() -> None:
    score = calculate_engagement_score(pd.Series([60, None]), pd.Series([100, 100]), pd.Series([15, 15]), pd.Series([0, 0]))
    assert score.iloc[0] == 100
    assert math.isnan(score.iloc[1])


def test_core_kpis_use_unique_viewers_not_sessions() -> None:
    subscribers, activity, content = _frames()
    kpis = calculate_core_kpis(build_viewer_analytics(subscribers, activity, content))
    assert kpis.total_viewers == 3
    assert round(kpis.retention_rate, 2) == 66.67
    assert round(kpis.churn_rate, 2) == 33.33


def test_core_kpis_handle_an_empty_viewer_table() -> None:
    empty = pd.DataFrame(
        columns=["user_id", "retention_status", "average_watch_duration", "average_completion_rate", "engagement_score"]
    )
    kpis = calculate_core_kpis(empty)
    assert kpis.total_viewers == 0
    assert kpis.retention_rate == 0
    assert kpis.churn_rate == 0


def test_breakdowns_deduplicate_a_viewer_within_each_group() -> None:
    subscribers, activity, content = _frames()
    by_device = retention_breakdown(subscribers, activity, "device")
    by_genre = retention_breakdown(subscribers, activity, "genre", content)
    assert by_device.set_index("device").loc["TV", "viewers"] == 2
    assert by_genre.set_index("genre").loc["Drama", "viewers"] == 2
    assert retention_breakdown(subscribers, activity, "subscription_plan").set_index("subscription_plan").loc["Premium", "viewers"] == 2


def test_content_analysis_returns_show_and_genre_metrics() -> None:
    subscribers, activity, content = _frames()
    result = build_content_analytics(subscribers, content, activity)
    assert set(result.show_performance["show_id"]) == {"s1", "s2"}
    assert set(result.genre_performance["genre"]) == {"Drama", "Comedy"}


def test_content_genre_metrics_deduplicate_viewers_and_coerce_invalid_values() -> None:
    subscribers, activity, content = _frames()
    activity.loc[len(activity)] = ["a4", "u1", "s1", "not-a-number", "invalid", 1, "TV"]
    content.loc[len(content)] = ["s3", "Show Three", "Drama", "not-a-rating"]
    activity.loc[len(activity)] = ["a5", "u1", "s3", 20, 70, 1, "TV"]
    result = build_content_analytics(subscribers, content, activity)
    drama = result.genre_performance.set_index("genre").loc["Drama"]
    assert drama["viewers"] == 2
    assert drama["retention_rate"] == 50
    assert "engagement_band" in result.show_performance.columns
