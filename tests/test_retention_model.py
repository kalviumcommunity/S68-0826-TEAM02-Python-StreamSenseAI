"""Tests for descriptive, non-causal retention relationship calculations."""

import math

import pandas as pd

from src.retention_model import retention_relationships


def _viewer_table() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "retention_status": ["Churned", "Churned", "Retained", "Retained"],
            "average_watch_duration": [10, 20, 50, 60],
            "average_completion_rate": [20, 30, 80, 90],
            "average_pause_count": [7, 6, 1, 0],
            "session_frequency": [1, 2, 10, 12],
            "engagement_score": [15, 25, 80, 95],
        }
    )


def test_retention_relationships_returns_all_features_and_association_language() -> None:
    relationships = retention_relationships(_viewer_table())
    assert len(relationships) == 5
    assert relationships.set_index("feature").loc["average_watch_duration", "pearson_correlation"] > 0
    assert "does not imply causation" in relationships.iloc[0]["interpretation"]


def test_retention_relationships_handles_missing_and_constant_inputs() -> None:
    viewers = _viewer_table()
    viewers["average_pause_count"] = 2
    viewers.loc[0, "average_completion_rate"] = None
    relationships = retention_relationships(viewers).set_index("feature")
    assert math.isnan(relationships.loc["average_pause_count", "pearson_correlation"])
    assert relationships.loc["average_completion_rate", "observations"] == 3
