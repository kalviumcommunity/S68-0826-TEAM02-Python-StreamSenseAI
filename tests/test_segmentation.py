"""Tests for StandardScaler followed by KMeans behavioural segmentation."""

import pandas as pd
import pytest

from src.analytics_exports import build_segment_summary
from src.segmentation import evaluate_cluster_counts, fit_viewer_segmentation, prepare_segmentation_features


def _viewers() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "user_id": ["a", "b", "c", "d", "e", "f"],
            "average_watch_duration": [10, 12, 14, 50, 55, 60],
            "average_completion_rate": [20, 25, 30, 80, 85, 90],
            "average_pause_count": [6, 5, 6, 1, 1, 0],
            "session_frequency": [1, 2, 2, 10, 11, 12],
            "engagement_score": [15, 20, 25, 80, 85, 95],
            "retention_status": ["Churned", "Churned", "Churned", "Retained", "Retained", "Retained"],
        }
    )


def test_preprocessing_drops_incomplete_rows_without_imputation() -> None:
    viewers = _viewers()
    viewers.loc[0, "average_watch_duration"] = None
    prepared = prepare_segmentation_features(viewers)
    assert len(prepared) == 5
    assert prepared.isna().sum().sum() == 0


def test_scaler_and_kmeans_return_reproducible_assignments_and_profiles() -> None:
    result = fit_viewer_segmentation(_viewers(), n_clusters=2, random_state=7)
    repeat = fit_viewer_segmentation(_viewers(), n_clusters=2, random_state=7)
    assert len(result.assignments) == 6
    assert result.assignments["cluster"].nunique() == 2
    assert result.model.n_clusters == 2
    assert result.scaler.mean_.shape[0] == 4
    assert result.profile["segment_name"].str.len().gt(0).all()
    assert result.assignments[["user_id", "cluster"]].equals(repeat.assignments[["user_id", "cluster"]])


def test_cluster_count_evaluation_and_small_input_edge_case() -> None:
    evaluation = evaluate_cluster_counts(prepare_segmentation_features(_viewers()))
    assert set(evaluation.columns) == {"n_clusters", "inertia", "silhouette_score"}
    assert not evaluation.empty
    with pytest.raises(ValueError, match="at least three"):
        fit_viewer_segmentation(_viewers().head(2))


def test_degenerate_features_are_skipped_with_a_clear_error() -> None:
    viewers = _viewers()
    for column in ["average_watch_duration", "average_completion_rate", "average_pause_count", "session_frequency"]:
        viewers[column] = 1
    evaluation = evaluate_cluster_counts(prepare_segmentation_features(viewers))
    assert evaluation.empty
    with pytest.raises(ValueError, match="no valid cluster count"):
        fit_viewer_segmentation(viewers)


def test_segment_summary_matches_dashboard_column_contract() -> None:
    viewers = _viewers()
    result = fit_viewer_segmentation(viewers, n_clusters=2)
    summary = build_segment_summary(result.assignments, viewers)
    assert {"segment_name", "user_count", "engagement_score", "retention_rate"}.issubset(summary.columns)
    assert summary["user_count"].sum() == len(viewers)


def test_business_insight_export_matches_dashboard_contract() -> None:
    from src.analytics_exports import build_business_insight_export

    insights = pd.DataFrame({"title": ["One", "Two", "Three"], "message": ["Evidence 1", "Evidence 2", "Evidence 3"]})
    export = build_business_insight_export(insights, "Evidence-backed opportunity", "Evidence-backed action")
    assert {"insight_id", "title", "message", "category"}.issubset(export.columns)
    assert export["category"].value_counts().to_dict() == {"insight": 3, "acquisition_opportunity": 1, "recommended_action": 1}
