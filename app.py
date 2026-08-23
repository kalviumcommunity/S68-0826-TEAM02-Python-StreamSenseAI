"""Streamlit entry point for the StreamSense AI dashboard."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.content import build_content_ranking_table, calculate_content_kpis, content_session_metrics
from src.executive import calculate_executive_kpis
from src.filters import DashboardFilters, apply_dashboard_filters, render_global_filters
from src.insights import load_business_insights
from src.retention import build_retention_features, retention_by_engagement_band
from src.segments import load_viewer_segment_summary
from src.ui import apply_global_styles, render_empty_state, render_page_header, render_section_header
from src.viewer import calculate_viewer_kpis
from src.visualization import (
    content_genre_performance,
    completion_distribution,
    completion_rate_trend,
    content_performance,
    episode_completion_by_genre,
    engagement_vs_retention,
    genre_performance,
    pause_vs_completion,
    pause_frequency_vs_completion,
    rating_vs_retention,
    retention_by_viewer_segment_chart,
    retention_correlation_heatmap,
    retention_by_signup_cohort,
    top_shows,
    viewing_by_device,
    watch_duration_distribution,
    watch_duration_trend,
)

PROJECT_ROOT = Path(__file__).resolve().parent
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
DATASETS = {
    "Subscribers": ("subscriber_data.csv", 1_000),
    "Shows": ("content_metadata.csv", 100),
    "Viewing sessions": ("viewer_activity.csv", 10_000),
}

st.set_page_config(page_title="StreamSense AI", page_icon="TV", layout="wide", initial_sidebar_state="expanded")


@st.cache_data(show_spinner=False)
def load_dataset_row_counts() -> tuple[dict[str, int], list[str]]:
    """Return raw-data row counts and missing or unreadable file names."""
    counts: dict[str, int] = {}
    errors: list[str] = []
    for label, (filename, _) in DATASETS.items():
        path = RAW_DATA_DIR / filename
        if not path.exists():
            errors.append(filename)
            continue
        try:
            counts[label] = len(pd.read_csv(path))
        except (OSError, pd.errors.ParserError):
            errors.append(filename)
    return counts, errors


@st.cache_data(show_spinner=False)
def load_filter_options() -> tuple[list[str], list[str], list[str], object, object] | None:
    """Load only the fields needed to populate the shared filter controls."""
    try:
        subscribers = pd.read_csv(RAW_DATA_DIR / "subscriber_data.csv", usecols=["subscription_plan"])
        content = pd.read_csv(RAW_DATA_DIR / "content_metadata.csv", usecols=["genre"])
        activity = pd.read_csv(RAW_DATA_DIR / "viewer_activity.csv", usecols=["device", "watch_date"])
    except (FileNotFoundError, OSError, ValueError, pd.errors.ParserError):
        return None

    watch_dates = pd.to_datetime(activity["watch_date"], errors="coerce").dropna()
    if watch_dates.empty:
        return None
    return (
        content["genre"].dropna().unique().tolist(),
        subscribers["subscription_plan"].dropna().unique().tolist(),
        activity["device"].dropna().unique().tolist(),
        watch_dates.min().date(),
        watch_dates.max().date(),
    )


@st.cache_data(show_spinner=False)
def load_overview_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame] | None:
    """Load dashboard chart inputs without introducing a separate analytics pipeline."""
    try:
        subscribers = pd.read_csv(RAW_DATA_DIR / "subscriber_data.csv")
        content = pd.read_csv(RAW_DATA_DIR / "content_metadata.csv")
        activity = pd.read_csv(RAW_DATA_DIR / "viewer_activity.csv")
    except (FileNotFoundError, OSError, pd.errors.ParserError):
        return None
    return subscribers, content, activity


def status_card(column: st.delta_generator.DeltaGenerator, label: str, value: int | None, expected: int) -> None:
    """Render one data-readiness metric."""
    if value is None:
        column.metric(label, "Unavailable")
        return
    delta = "Expected count" if value == expected else f"Expected {expected:,}"
    column.metric(label, f"{value:,}", delta=delta, delta_color="normal" if value == expected else "off")


def render_overview(selected_filters: DashboardFilters | None) -> None:
    """Render the Day 3 data-status overview."""
    render_page_header(
        "Overview",
        "Viewer Intelligence Dashboard",
        "Understand the engagement signals behind subscriber retention and better content decisions.",
    )
    st.divider()
    render_section_header("Dataset Status", "A live readiness check for the data powering this dashboard.")

    counts, errors = load_dataset_row_counts()
    expected_counts_match = all(counts.get(label) == expected for label, (_, expected) in DATASETS.items())
    if not errors and expected_counts_match:
        st.success("Data loaded and ready for analysis.")
    elif errors:
        st.warning(f"Data is not ready yet. Missing or unreadable file(s): {', '.join(errors)}.")
        st.code(r".\.venv\Scripts\python.exe scripts\generate_data.py", language="powershell")
    else:
        st.warning("Data loaded, but one or more datasets do not contain the expected number of records.")

    subscribers, shows, activities = st.columns(3)
    status_card(subscribers, "Subscribers", counts.get("Subscribers"), DATASETS["Subscribers"][1])
    status_card(shows, "Shows", counts.get("Shows"), DATASETS["Shows"][1])
    status_card(activities, "Viewing sessions", counts.get("Viewing sessions"), DATASETS["Viewing sessions"][1])

    st.divider()
    render_section_header("Executive Snapshot", "The key viewing and retention signals for the selected audience.")
    overview_data = load_overview_data()
    if overview_data is None:
        st.info("Generate the raw datasets to view the executive dashboard.")
    else:
        subscribers_data, content_data, activity_data = apply_dashboard_filters(*overview_data, selected_filters)
        if activity_data.empty:
            st.warning("No viewing sessions match the current filters. Adjust the sidebar filters to continue.")
            return

        kpis = calculate_executive_kpis(subscribers_data, activity_data)
        row_one = st.columns(3)
        row_one[0].metric("Total viewers", f"{kpis.total_viewers:,}")
        row_one[1].metric("Retention rate", f"{kpis.retention_rate:.1f}%")
        row_one[2].metric("Churn rate", f"{kpis.churn_rate:.1f}%")
        row_two = st.columns(3)
        row_two[0].metric("Avg. watch duration", f"{kpis.average_watch_duration:.1f} min")
        row_two[1].metric("Avg. completion rate", f"{kpis.average_completion_rate:.1f}%")
        row_two[2].metric("Engagement score", f"{kpis.engagement_score:.1f}/100")

        st.divider()
        render_section_header("Retention and engagement", "Where is engagement strongest, and how does it align with retention?")
        retention_chart, engagement_chart = st.columns(2)
        with retention_chart:
            st.plotly_chart(retention_by_signup_cohort(subscribers_data), width="stretch")
            st.caption("How does retention differ across subscriber signup cohorts?")
        with engagement_chart:
            st.plotly_chart(engagement_vs_retention(subscribers_data, activity_data), width="stretch")
            st.caption("Do higher engagement signals align with retained viewers?")

        st.divider()
        render_section_header("Content opportunity", "Which genres and titles show the strongest engagement-retention signals?")
        genre_chart, content_chart = st.columns(2)
        with genre_chart:
            st.plotly_chart(genre_performance(activity_data, content_data, subscribers_data), width="stretch")
            st.caption("Which genres combine stronger viewer retention with completion?")
        with content_chart:
            st.plotly_chart(content_performance(activity_data, content_data, subscribers_data), width="stretch")
            st.caption("Which titles balance completion, retention, and viewing volume?")

        st.divider()
        render_section_header("Engagement trends", "How are viewer attention and episode completion changing over time?")
        first_chart, second_chart = st.columns(2)
        with first_chart:
            st.plotly_chart(watch_duration_trend(activity_data), width="stretch")
            st.caption("Is average viewing time changing over time?")
        with second_chart:
            st.plotly_chart(completion_rate_trend(activity_data), width="stretch")
            st.caption("Are viewers completing more of what they start?")

    st.divider()
    render_section_header("What this means", "The next analytics pages will build on this shared data foundation.")
    st.write(
        "Once all three datasets are ready, the dashboard can connect viewing behaviour "
        "with subscriber retention. Upcoming pages will turn this foundation into viewer, "
        "content, and retention insights."
    )
    if selected_filters:
        st.caption(
            "Global filters are ready. Analytical pages will apply them as their data services are added."
        )


def render_placeholder(page: str) -> None:
    """Keep planned pages visible while their analytical content is delivered."""
    descriptions = {
        "Viewer Analytics": "Explore viewing habits, completion patterns, pauses, and devices.",
        "Content Analytics": "Compare content performance to support acquisition decisions.",
        "Retention Insights": "Identify engagement patterns associated with subscriber loyalty.",
    }
    render_page_header("Dashboard", page, descriptions[page])
    st.divider()
    render_empty_state("Analytics in progress", "This page will connect to the validated analytics outputs in a later milestone.")


def render_viewer_analytics(selected_filters: DashboardFilters | None) -> None:
    """Render the Day 8 Viewer Analytics page using validated activity inputs."""
    render_page_header(
        "Viewer analytics",
        "Viewer Analytics",
        "Understand session behavior, completion habits, pause friction, and device-level viewing patterns.",
    )
    st.divider()
    overview_data = load_overview_data()
    if overview_data is None:
        st.info("Generate the raw datasets to view viewer analytics.")
        return

    subscribers_data, content_data, activity_data = apply_dashboard_filters(*overview_data, selected_filters)
    del content_data
    if activity_data.empty:
        st.warning("No viewing sessions match the current filters. Adjust the sidebar filters to continue.")
        return

    render_section_header("Viewer KPIs", "How are viewers consuming content across their sessions?")
    kpis = calculate_viewer_kpis(activity_data)
    kpi_columns = st.columns(4)
    kpi_columns[0].metric("Average watch duration", f"{kpis.average_watch_duration:.1f} min")
    kpi_columns[1].metric("Average session duration", f"{kpis.average_session_duration:.1f} min")
    kpi_columns[2].metric("Completion rate", f"{kpis.completion_rate:.1f}%")
    kpi_columns[3].metric("Average pause count", f"{kpis.average_pause_count:.2f}")

    st.divider()
    render_section_header("Session distributions", "Where do most sessions cluster for watch depth and completion?")
    chart_left, chart_right = st.columns(2)
    with chart_left:
        st.plotly_chart(watch_duration_distribution(activity_data), width="stretch")
        st.caption("How is watch duration distributed across viewer sessions?")
    with chart_right:
        st.plotly_chart(completion_distribution(activity_data), width="stretch")
        st.caption("How concentrated are sessions at higher versus lower completion?")

    st.divider()
    render_section_header("Behavior relationships", "Which interaction patterns may signal stronger or weaker viewer outcomes?")
    chart_left, chart_right = st.columns(2)
    with chart_left:
        st.plotly_chart(pause_vs_completion(activity_data), width="stretch")
        st.caption("Does frequent pausing correspond with lower completion?")
    with chart_right:
        st.plotly_chart(viewing_by_device(activity_data), width="stretch")
        st.caption("Which devices drive the most sessions and stronger completion outcomes?")

    st.divider()
    render_section_header("Viewer segments", "How do key audience segments compare on engagement and retention?")
    segment_summary, segment_source, segment_errors = load_viewer_segment_summary(
        PROJECT_ROOT, subscribers_data, activity_data
    )
    if segment_errors:
        st.caption("Segmentation file checks: " + " | ".join(segment_errors))

    if segment_summary is None:
        st.warning(
            "Viewer segmentation output is not available yet. Add Person 2's segmentation export to data/processed/ to display this section."
        )
    else:
        st.caption(segment_source)
        card_columns = st.columns(5)
        for card, segment_row in zip(card_columns, segment_summary.itertuples(index=False), strict=True):
            with card:
                with st.container(border=True):
                    st.markdown(f"**{segment_row.segment_name}**")
                    st.metric("Users", f"{segment_row.user_count:,}")
                    st.metric("Engagement score", f"{segment_row.engagement_score:.1f}/100")
                    st.metric("Retention rate", f"{segment_row.retention_rate:.1f}%")
                    st.caption(segment_row.description)

        st.dataframe(
            segment_summary.rename(
                columns={
                    "segment_name": "Segment",
                    "user_count": "Users",
                    "engagement_score": "Engagement Score",
                    "retention_rate": "Retention Rate (%)",
                    "description": "Behavior",
                }
            ),
            width="stretch",
            hide_index=True,
        )


def render_content_analytics(selected_filters: DashboardFilters | None) -> None:
    """Render the Day 10 Content Analytics page."""
    render_page_header(
        "Content analytics",
        "Content Analytics",
        "Compare show and genre performance to support content acquisition and prioritization decisions.",
    )
    st.divider()
    overview_data = load_overview_data()
    if overview_data is None:
        st.info("Generate the raw datasets to view content analytics.")
        return

    subscribers_data, content_data, activity_data = apply_dashboard_filters(*overview_data, selected_filters)
    if activity_data.empty:
        st.warning("No viewing sessions match the current filters. Adjust the sidebar filters to continue.")
        return

    content_metrics = content_session_metrics(activity_data, content_data, subscribers_data)
    if content_metrics.empty:
        st.warning("No content performance records are available for the current filters.")
        return

    render_section_header("Content KPIs", "How are titles performing on quality, completion, and retention outcomes?")
    kpis = calculate_content_kpis(content_metrics)
    kpi_columns = st.columns(4)
    kpi_columns[0].metric("Total shows", f"{kpis.total_shows:,}")
    kpi_columns[1].metric("Average rating", f"{kpis.average_rating:.2f}/10")
    kpi_columns[2].metric("Average completion", f"{kpis.average_completion:.1f}%")
    kpi_columns[3].metric("Average watch duration", f"{kpis.average_watch_duration:.1f} min")

    st.divider()
    render_section_header("Content drivers", "Which genres and titles are creating stronger retained viewing?")
    chart_left, chart_right = st.columns(2)
    with chart_left:
        st.plotly_chart(content_genre_performance(activity_data, content_data, subscribers_data), width="stretch")
        st.caption("Which genres currently show stronger retention and completion performance?")
    with chart_right:
        st.plotly_chart(top_shows(activity_data, content_data, subscribers_data), width="stretch")
        st.caption("Which shows rank highest on retention-supported engagement outcomes?")

    st.divider()
    render_section_header("Quality and completion patterns", "How do ratings and episode completion align with retention?")
    chart_left, chart_right = st.columns(2)
    with chart_left:
        st.plotly_chart(rating_vs_retention(activity_data, content_data, subscribers_data), width="stretch")
        st.caption("Do higher-rated shows consistently retain viewers better?")
    with chart_right:
        st.plotly_chart(episode_completion_by_genre(activity_data, content_data, subscribers_data), width="stretch")
        st.caption("Which genres drive stronger episode completion rates?")

    st.divider()
    render_section_header("Show ranking", "A ranked view of title-level performance for decision support.")
    st.dataframe(build_content_ranking_table(content_metrics), width="stretch", hide_index=True)


def render_retention_insights(selected_filters: DashboardFilters | None) -> None:
    """Render the Day 11 Retention Insights page."""
    render_page_header(
        "Retention insights",
        "Retention Insights",
        "Identify engagement patterns associated with subscriber retention.",
    )
    st.divider()
    overview_data = load_overview_data()
    if overview_data is None:
        st.info("Generate the raw datasets to view retention insights.")
        return

    subscribers_data, content_data, activity_data = apply_dashboard_filters(*overview_data, selected_filters)
    del content_data
    if activity_data.empty or subscribers_data.empty:
        st.warning("No retention records match the current filters. Adjust the sidebar filters to continue.")
        return

    retention_features = build_retention_features(subscribers_data, activity_data)
    if retention_features.empty:
        st.warning("Retention feature inputs are unavailable for the current filters.")
        return
    segment_summary, segment_source, segment_errors = load_viewer_segment_summary(
        PROJECT_ROOT, subscribers_data, activity_data
    )

    render_section_header("Engagement bands", "How does retention differ across high, medium, and low engagement viewers?")
    engagement_summary = retention_by_engagement_band(retention_features)
    band_columns = st.columns(3)
    for column, row in zip(band_columns, engagement_summary.itertuples(index=False), strict=True):
        column.metric(row.engagement_band, f"{row.retention_rate:.1f}%")

    st.divider()
    render_section_header("Retention drivers", "What behavioral relationships are most associated with retention outcomes?")
    chart_left, chart_right = st.columns(2)
    with chart_left:
        st.plotly_chart(retention_correlation_heatmap(retention_features), width="stretch")
        st.caption("Which engagement variables are most strongly correlated with retention and churn probability?")
    with chart_right:
        if segment_errors:
            st.caption("Segmentation file checks: " + " | ".join(segment_errors))
        if segment_summary is None:
            st.warning("Viewer segment data is unavailable. Add Person 2 segmentation output to data/processed/.")
        else:
            st.plotly_chart(retention_by_viewer_segment_chart(segment_summary), width="stretch")
            st.caption("Which viewer segments currently retain subscribers most effectively?")
            st.caption(segment_source)

    st.divider()
    render_section_header("Friction and loyalty", "How do pauses, completion behavior, and engagement align with retention?")
    chart_left, chart_right = st.columns(2)
    with chart_left:
        st.plotly_chart(pause_frequency_vs_completion(retention_features), width="stretch")
        st.caption("Does higher pause frequency correspond to lower completion rates?")
    with chart_right:
        st.plotly_chart(engagement_vs_retention(subscribers_data, activity_data), width="stretch")
        st.caption("How does engagement level separate retained and churned viewers?")

    st.divider()
    render_section_header("Business insights", "Action-oriented findings to support acquisition and retention decisions.")
    insights_payload = load_business_insights(PROJECT_ROOT, retention_features, segment_summary)
    if insights_payload.source_errors:
        st.caption("Business insight file checks: " + " | ".join(insights_payload.source_errors))
    st.caption(insights_payload.source_note)

    insight_columns = st.columns(3)
    for column, insight in zip(insight_columns, insights_payload.insights, strict=True):
        with column:
            with st.container(border=True):
                st.caption(insight.identifier)
                st.markdown(f"**{insight.title}**")
                st.write(insight.message)

    opportunity_column, action_column = st.columns(2)
    with opportunity_column:
        with st.container(border=True):
            st.markdown("**Acquisition Opportunity**")
            st.write(insights_payload.acquisition_opportunity)
    with action_column:
        with st.container(border=True):
            st.markdown("**Recommended Action**")
            st.write(insights_payload.recommended_action)

    st.caption(
        "Insights are based on historical/synthetic analytics data and should support—not replace—business judgment."
    )


def render_about() -> None:
    """Describe the project without claiming unimplemented analytics."""
    render_page_header("About", "About StreamSense AI", "Turning viewer behaviour into clearer content-acquisition decisions.")
    st.divider()
    st.write(
        "StreamSense AI helps acquisition teams identify viewer-engagement patterns "
        "associated with subscriber retention before greenlighting content."
    )


def main() -> None:
    """Render app navigation and the selected page."""
    apply_global_styles()
    with st.sidebar:
        st.title("StreamSense AI")
        st.caption("VIEWER INTELLIGENCE")
        st.divider()
        st.caption("WORKSPACE")
        page = st.radio(
            "Navigation",
            ["Overview", "Viewer Analytics", "Content Analytics", "Retention Insights", "About"],
            label_visibility="collapsed",
        )

    filter_options = load_filter_options()
    selected_filters = None
    if filter_options:
        selected_filters = render_global_filters(*filter_options)
    else:
        with st.sidebar:
            st.divider()
            st.markdown("### Filters")
            st.caption("Generate the raw datasets to enable filters.")

    if page == "Overview":
        render_overview(selected_filters)
    elif page == "Viewer Analytics":
        render_viewer_analytics(selected_filters)
    elif page == "Content Analytics":
        render_content_analytics(selected_filters)
    elif page == "Retention Insights":
        render_retention_insights(selected_filters)
    elif page == "About":
        render_about()
    else:
        render_placeholder(page)


if __name__ == "__main__":
    main()
