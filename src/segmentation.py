"""Interpretable StandardScaler and KMeans viewer segmentation utilities."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler


# Engagement score is deliberately excluded: it is derived from these behavioural
# signals, so including it would double-weight the same underlying behaviour.
SEGMENT_FEATURES = ["average_watch_duration", "average_completion_rate", "average_pause_count", "session_frequency"]


@dataclass(frozen=True)
class SegmentationResult:
    """Fitted segmentation artifacts and interpretable, data-derived outputs."""

    assignments: pd.DataFrame
    profile: pd.DataFrame
    cluster_evaluation: pd.DataFrame
    scaler: StandardScaler
    model: KMeans


def prepare_segmentation_features(viewer_analytics: pd.DataFrame) -> pd.DataFrame:
    """Select valid behavioural rows for clustering without fabricating missing values."""
    required = {"user_id", *SEGMENT_FEATURES}
    missing = sorted(required.difference(viewer_analytics.columns))
    if missing:
        raise ValueError(f"viewer_analytics is missing required columns: {', '.join(missing)}")
    prepared = viewer_analytics[["user_id", *SEGMENT_FEATURES]].drop_duplicates("user_id").copy()
    prepared[SEGMENT_FEATURES] = prepared[SEGMENT_FEATURES].apply(pd.to_numeric, errors="coerce")
    return prepared.dropna(subset=SEGMENT_FEATURES).reset_index(drop=True)


def evaluate_cluster_counts(prepared_features: pd.DataFrame, max_clusters: int = 6, random_state: int = 42) -> pd.DataFrame:
    """Evaluate feasible cluster counts using inertia and silhouette score."""
    if len(prepared_features) < 3:
        return pd.DataFrame(columns=["n_clusters", "inertia", "silhouette_score"])
    missing = sorted(set(SEGMENT_FEATURES).difference(prepared_features.columns))
    if missing:
        raise ValueError(f"prepared_features is missing required columns: {', '.join(missing)}")
    values = prepared_features[SEGMENT_FEATURES]
    scaled = StandardScaler().fit_transform(values)
    maximum = min(max_clusters, len(prepared_features) - 1)
    rows: list[dict[str, float | int]] = []
    for n_clusters in range(2, maximum + 1):
        model = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=20)
        labels = model.fit_predict(scaled)
        label_count = len(set(labels))
        if label_count < 2 or label_count >= len(prepared_features):
            continue
        try:
            score = float(silhouette_score(scaled, labels))
        except ValueError:
            continue
        rows.append({"n_clusters": n_clusters, "inertia": float(model.inertia_), "silhouette_score": score})
    return pd.DataFrame(rows)


def _cluster_label(row: pd.Series) -> str:
    """Describe a cluster from its measured profile rather than assumed personas."""
    strengths: list[str] = []
    if pd.isna(row["engagement_score"]) or pd.isna(row["engagement_score_median"]):
        strengths.append("engagement unavailable")
    elif row["engagement_score"] >= row["engagement_score_median"]:
        strengths.append("higher engagement")
    else:
        strengths.append("lower engagement")
    if row["average_pause_count"] >= row["average_pause_count_median"]:
        strengths.append("higher pause frequency")
    elif row["session_frequency"] >= row["session_frequency_median"]:
        strengths.append("more frequent sessions")
    else:
        strengths.append("lower session frequency")
    return f"Cluster {int(row['cluster'])}: " + "; ".join(strengths)


def fit_viewer_segmentation(viewer_analytics: pd.DataFrame, n_clusters: int | None = None, random_state: int = 42) -> SegmentationResult:
    """Fit StandardScaler followed by KMeans and return empirical cluster labels.

    If ``n_clusters`` is omitted, the feasible count with the largest silhouette
    score is selected. Labels are descriptions of the fitted profiles, not
    predefined personas and not predictions of future behaviour.
    """
    prepared = prepare_segmentation_features(viewer_analytics)
    evaluation = evaluate_cluster_counts(prepared, random_state=random_state)
    if n_clusters is None:
        if evaluation.empty:
            raise ValueError("no valid cluster count is available; provide at least three non-degenerate complete viewer rows")
        n_clusters = int(evaluation.sort_values(["silhouette_score", "n_clusters"], ascending=[False, True]).iloc[0]["n_clusters"])
    if n_clusters < 2 or n_clusters >= len(prepared):
        raise ValueError("n_clusters must be at least 2 and smaller than the number of complete viewer rows")

    scaler = StandardScaler()
    scaled = scaler.fit_transform(prepared[SEGMENT_FEATURES])
    model = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=20)
    assignments = prepared[["user_id"]].copy()
    assignments["cluster"] = model.fit_predict(scaled)
    if assignments["cluster"].nunique() < 2:
        raise ValueError("KMeans produced fewer than two distinct clusters; input features are degenerate")
    profile_input = assignments.merge(prepared, on="user_id", how="inner")
    if "engagement_score" in viewer_analytics.columns:
        engagement = viewer_analytics[["user_id", "engagement_score"]].drop_duplicates("user_id").copy()
        engagement["engagement_score"] = pd.to_numeric(engagement["engagement_score"], errors="coerce")
        profile_input = profile_input.merge(engagement, on="user_id", how="left")
    else:
        profile_input["engagement_score"] = float("nan")
    profile_features = [*SEGMENT_FEATURES, "engagement_score"]
    profile = profile_input.groupby("cluster", as_index=False)[profile_features].mean()
    for feature in profile_features:
        profile[f"{feature}_median"] = profile[feature].median()
    profile["segment_name"] = profile.apply(_cluster_label, axis=1)
    assignments = assignments.merge(profile[["cluster", "segment_name"]], on="cluster", how="left")
    return SegmentationResult(assignments=assignments, profile=profile, cluster_evaluation=evaluation, scaler=scaler, model=model)
