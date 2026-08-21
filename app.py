"""Streamlit entry point for the StreamSense AI dashboard."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.filters import DashboardFilters, render_global_filters

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


def status_card(column: st.delta_generator.DeltaGenerator, label: str, value: int | None, expected: int) -> None:
    """Render one data-readiness metric."""
    if value is None:
        column.metric(label, "Unavailable")
        return
    delta = "Expected count" if value == expected else f"Expected {expected:,}"
    column.metric(label, f"{value:,}", delta=delta, delta_color="normal" if value == expected else "off")


def render_overview(selected_filters: DashboardFilters | None) -> None:
    """Render the Day 3 data-status overview."""
    st.title("StreamSense AI")
    st.caption("Viewer engagement intelligence for smarter content decisions")
    st.divider()
    st.subheader("Dataset Status")
    st.write("A live readiness check for the data powering the dashboard.")

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
    st.markdown("#### What this means")
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
    st.title(page)
    st.info("This page is being prepared and will be connected to the analytics outputs soon.")


def render_about() -> None:
    """Describe the project without claiming unimplemented analytics."""
    st.title("About StreamSense AI")
    st.write(
        "StreamSense AI helps acquisition teams identify viewer-engagement patterns "
        "associated with subscriber retention before greenlighting content."
    )


def main() -> None:
    """Render app navigation and the selected page."""
    with st.sidebar:
        st.title("StreamSense AI")
        st.caption("Viewer Intelligence")
        st.divider()
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
