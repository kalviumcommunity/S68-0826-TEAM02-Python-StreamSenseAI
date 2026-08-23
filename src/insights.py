"""Business insight adapters for the StreamSense dashboard UI."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class BusinessInsight:
    """Single insight card payload."""

    identifier: str
    title: str
    message: str


@dataclass(frozen=True)
class BusinessInsightsPayload:
    """Business insights content for Day 12 UI."""

    insights: tuple[BusinessInsight, ...]
    acquisition_opportunity: str
    recommended_action: str
    source_note: str
    source_errors: tuple[str, ...]


def _pct(value: float) -> str:
    return f"{value:.1f}%"


def _parse_csv_insights(frame: pd.DataFrame) -> BusinessInsightsPayload | None:
    required = {"insight_id", "title", "message", "category"}
    if not required.issubset(frame.columns):
        return None

    mapped_rows = frame.copy()
    mapped_rows["category"] = mapped_rows["category"].astype(str).str.strip().str.lower()
    insights_rows = mapped_rows.loc[mapped_rows["category"].eq("insight")].head(3)
    if len(insights_rows) < 3:
        return None

    opportunity_rows = mapped_rows.loc[mapped_rows["category"].eq("acquisition_opportunity"), "message"]
    action_rows = mapped_rows.loc[mapped_rows["category"].eq("recommended_action"), "message"]
    if opportunity_rows.empty or action_rows.empty:
        return None

    insights = tuple(
        BusinessInsight(
            identifier=str(row.insight_id),
            title=str(row.title),
            message=str(row.message),
        )
        for row in insights_rows.itertuples(index=False)
    )
    return BusinessInsightsPayload(
        insights=insights,
        acquisition_opportunity=str(opportunity_rows.iloc[0]),
        recommended_action=str(action_rows.iloc[0]),
        source_note="Source: Person 2 business insights export",
        source_errors=(),
    )


def _parse_json_insights(payload: object) -> BusinessInsightsPayload | None:
    if not isinstance(payload, dict):
        return None
    raw_insights = payload.get("insights")
    opportunity = payload.get("acquisition_opportunity")
    action = payload.get("recommended_action")
    if not isinstance(raw_insights, list) or len(raw_insights) < 3 or not isinstance(opportunity, str) or not isinstance(action, str):
        return None

    cards: list[BusinessInsight] = []
    for item in raw_insights[:3]:
        if not isinstance(item, dict):
            return None
        cards.append(
            BusinessInsight(
                identifier=str(item.get("insight_id", f"INSIGHT {len(cards) + 1:02d}")),
                title=str(item.get("title", "")).strip(),
                message=str(item.get("message", "")).strip(),
            )
        )
    if any(not insight.title or not insight.message for insight in cards):
        return None

    return BusinessInsightsPayload(
        insights=tuple(cards),
        acquisition_opportunity=opportunity,
        recommended_action=action,
        source_note="Source: Person 2 business insights export",
        source_errors=(),
    )


def _build_fallback_insights(retention_features: pd.DataFrame, segment_summary: pd.DataFrame | None) -> BusinessInsightsPayload:
    completion_cutoff = float(retention_features["completion_rate"].median())
    high_completion = retention_features.loc[retention_features["completion_rate"] >= completion_cutoff, "retention"]
    low_completion = retention_features.loc[retention_features["completion_rate"] < completion_cutoff, "retention"]
    high_completion_rate = float(high_completion.mean() * 100) if not high_completion.empty else 0.0
    low_completion_rate = float(low_completion.mean() * 100) if not low_completion.empty else 0.0

    watch_cutoff = float(retention_features["watch_duration"].median())
    high_watch = retention_features.loc[retention_features["watch_duration"] >= watch_cutoff, "retention"]
    low_watch = retention_features.loc[retention_features["watch_duration"] < watch_cutoff, "retention"]
    high_watch_rate = float(high_watch.mean() * 100) if not high_watch.empty else 0.0
    low_watch_rate = float(low_watch.mean() * 100) if not low_watch.empty else 0.0

    pause_cutoff = float(retention_features["pause_count"].median())
    high_pause = retention_features.loc[retention_features["pause_count"] >= pause_cutoff, "retention"]
    low_pause = retention_features.loc[retention_features["pause_count"] < pause_cutoff, "retention"]
    high_pause_rate = float(high_pause.mean() * 100) if not high_pause.empty else 0.0
    low_pause_rate = float(low_pause.mean() * 100) if not low_pause.empty else 0.0

    if segment_summary is not None and not segment_summary.empty:
        best_segment = segment_summary.sort_values("retention_rate", ascending=False).iloc[0]
        acquisition_opportunity = (
            f"Focus acquisition campaigns on audiences similar to {best_segment['segment_name']} profiles "
            f"({best_segment['retention_rate']:.1f}% retention)."
        )
    else:
        acquisition_opportunity = (
            "Prioritize campaigns targeting high-engagement audiences where retention is already strongest."
        )

    recommended_action = (
        "Deploy an early-intervention journey for users with rising pause frequency and low completion, "
        "then monitor retention-lift by engagement band."
    )

    insights = (
        BusinessInsight(
            identifier="INSIGHT 01",
            title="Completion Matters",
            message=(
                f"Viewers above median completion retain at {_pct(high_completion_rate)} versus "
                f"{_pct(low_completion_rate)} below the median."
            ),
        ),
        BusinessInsight(
            identifier="INSIGHT 02",
            title="Longer Engagement Correlates With Loyalty",
            message=(
                f"Viewers above median watch duration retain at {_pct(high_watch_rate)} compared with "
                f"{_pct(low_watch_rate)} for shorter-watch audiences."
            ),
        ),
        BusinessInsight(
            identifier="INSIGHT 03",
            title="High Pause Frequency Is a Warning Signal",
            message=(
                f"High-pause viewers retain at {_pct(high_pause_rate)} versus {_pct(low_pause_rate)} "
                "for lower-pause cohorts."
            ),
        ),
    )
    return BusinessInsightsPayload(
        insights=insights,
        acquisition_opportunity=acquisition_opportunity,
        recommended_action=recommended_action,
        source_note="Source: derived from current filtered analytics (Person 2 export not found).",
        source_errors=(),
    )


def load_business_insights(
    project_root: Path, retention_features: pd.DataFrame, segment_summary: pd.DataFrame | None
) -> BusinessInsightsPayload:
    """Load Person 2 findings when present; otherwise return computed fallback insights."""
    source_errors: list[str] = []
    file_candidates = [
        Path("data/processed/business_insights.csv"),
        Path("data/processed/retention_findings.csv"),
        Path("reports/business_insights.csv"),
        Path("data/processed/business_insights.json"),
        Path("reports/business_insights.json"),
    ]

    for relative_path in file_candidates:
        absolute_path = project_root / relative_path
        if not absolute_path.exists():
            continue
        try:
            if absolute_path.suffix.lower() == ".csv":
                parsed = _parse_csv_insights(pd.read_csv(absolute_path))
            else:
                parsed = _parse_json_insights(json.loads(absolute_path.read_text(encoding="utf-8")))
        except (OSError, ValueError, pd.errors.ParserError) as error:
            source_errors.append(f"{relative_path}: {error}")
            continue
        if parsed is not None:
            return BusinessInsightsPayload(
                insights=parsed.insights,
                acquisition_opportunity=parsed.acquisition_opportunity,
                recommended_action=parsed.recommended_action,
                source_note=f"Source: {relative_path}",
                source_errors=tuple(source_errors),
            )
        source_errors.append(f"{relative_path}: required business insight fields not found")

    fallback = _build_fallback_insights(retention_features, segment_summary)
    return BusinessInsightsPayload(
        insights=fallback.insights,
        acquisition_opportunity=fallback.acquisition_opportunity,
        recommended_action=fallback.recommended_action,
        source_note=fallback.source_note,
        source_errors=tuple(source_errors),
    )
