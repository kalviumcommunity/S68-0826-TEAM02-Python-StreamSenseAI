"""Descriptive retention relationship analysis for StreamSense AI."""

from __future__ import annotations

import pandas as pd


RETENTION_FEATURES = (
    "average_watch_duration",
    "average_completion_rate",
    "average_pause_count",
    "session_frequency",
    "engagement_score",
)


def retention_relationships(viewer_analytics: pd.DataFrame) -> pd.DataFrame:
    """Measure historical Pearson associations between behavioural features and retention.

    Retention is encoded as one for ``Retained`` and zero for ``Churned``. The
    resulting coefficient is descriptive only; it must not be interpreted as a
    causal effect or as a prediction for an individual viewer.
    """
    required = {"retention_status", *RETENTION_FEATURES}
    missing = sorted(required.difference(viewer_analytics.columns))
    if missing:
        raise ValueError(f"viewer_analytics is missing required columns: {', '.join(missing)}")

    result_rows: list[dict[str, object]] = []
    retention = viewer_analytics["retention_status"].map({"Retained": 1.0, "Churned": 0.0})
    for feature in RETENTION_FEATURES:
        paired = pd.DataFrame({"feature": pd.to_numeric(viewer_analytics[feature], errors="coerce"), "retention": retention}).dropna()
        coefficient = paired["feature"].corr(paired["retention"]) if len(paired) >= 2 and paired.nunique().min() > 1 else float("nan")
        result_rows.append(
            {
                "feature": feature,
                "observations": len(paired),
                "pearson_correlation": coefficient,
                "interpretation": "Historical association with retention; correlation does not imply causation.",
            }
        )
    return pd.DataFrame(result_rows)
