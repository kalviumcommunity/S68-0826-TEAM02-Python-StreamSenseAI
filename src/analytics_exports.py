"""DataFrame builders for optional analytics exports consumed by the dashboard."""

from __future__ import annotations

import pandas as pd


def build_segment_summary(assignments: pd.DataFrame, viewer_analytics: pd.DataFrame) -> pd.DataFrame:
    """Build the dashboard-compatible segment summary without writing project data."""
    required_assignments = {"user_id", "segment_name"}
    required_viewers = {"user_id", "engagement_score", "retention_status"}
    if missing := sorted(required_assignments.difference(assignments.columns)):
        raise ValueError(f"assignments is missing required columns: {', '.join(missing)}")
    if missing := sorted(required_viewers.difference(viewer_analytics.columns)):
        raise ValueError(f"viewer_analytics is missing required columns: {', '.join(missing)}")
    joined = assignments[["user_id", "segment_name"]].drop_duplicates("user_id").merge(
        viewer_analytics[["user_id", "engagement_score", "retention_status"]].drop_duplicates("user_id"), on="user_id", how="inner"
    )
    joined["is_retained"] = joined["retention_status"].eq("Retained")
    summary = joined.groupby("segment_name", as_index=False).agg(
        user_count=("user_id", "nunique"), engagement_score=("engagement_score", "mean"), retention_rate=("is_retained", "mean")
    )
    summary["retention_rate"] *= 100
    return summary


def build_business_insight_export(
    insights: pd.DataFrame, acquisition_opportunity: str, recommended_action: str
) -> pd.DataFrame:
    """Build the CSV contract consumed by the dashboard business-insights loader.

    Findings and actions are supplied by the caller after running real-data
    analysis; this function creates no claims or values on its own.
    """
    required = {"title", "message"}
    missing = sorted(required.difference(insights.columns))
    if missing:
        raise ValueError(f"insights is missing required columns: {', '.join(missing)}")
    findings = insights[["title", "message"]].dropna().copy()
    if "insight_id" in insights.columns:
        findings["insight_id"] = insights.loc[findings.index, "insight_id"].astype("string")
    else:
        findings["insight_id"] = [f"INSIGHT {index:02d}" for index in range(1, len(findings) + 1)]
    if len(findings) < 3:
        raise ValueError("at least three evidence-backed insight rows are required by the dashboard contract")
    findings["category"] = "insight"
    findings = findings[["insight_id", "title", "message", "category"]]
    context_rows = pd.DataFrame(
        [
            {"insight_id": "ACQUISITION_OPPORTUNITY", "title": "Acquisition Opportunity", "message": acquisition_opportunity, "category": "acquisition_opportunity"},
            {"insight_id": "RECOMMENDED_ACTION", "title": "Recommended Action", "message": recommended_action, "category": "recommended_action"},
        ]
    )
    if not acquisition_opportunity.strip() or not recommended_action.strip():
        raise ValueError("acquisition_opportunity and recommended_action must be non-empty evidence-backed statements")
    return pd.concat([findings, context_rows], ignore_index=True)
