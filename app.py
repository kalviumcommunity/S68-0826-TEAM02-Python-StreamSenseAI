"""Streamlit entry point for the StreamSense AI dashboard."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.filters import DashboardFilters, render_global_filters
from src.ui import apply_global_styles, render_empty_state, render_page_header, render_section_header
from src.visualization import completion_rate_trend, genre_performance, retention_by_signup_cohort, watch_duration_trend

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
    render_section_header("Engagement Overview", "Which behaviours and content areas are associated with stronger retention?")
    overview_data = load_overview_data()
    if overview_data is None:
        st.info("Generate the raw datasets to view the engagement overview charts.")
    else:
        subscribers_data, content_data, activity_data = overview_data
        st.plotly_chart(retention_by_signup_cohort(subscribers_data), width="stretch")
        st.caption("Business question: How does retention differ across subscriber signup cohorts?")
        first_chart, second_chart = st.columns(2)
        with first_chart:
            st.plotly_chart(watch_duration_trend(activity_data), width="stretch")
            st.caption("Business question: Is average viewing time changing over time?")
        with second_chart:
            st.plotly_chart(completion_rate_trend(activity_data), width="stretch")
            st.caption("Business question: Are viewers completing more of what they start?")
        st.plotly_chart(genre_performance(activity_data, content_data, subscribers_data), width="stretch")
        st.caption("Business question: Which genres combine stronger viewer retention with completion?")

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
    elif page == "About":
        render_about()
    else:
        render_placeholder(page)


if __name__ == "__main__":
    main()
