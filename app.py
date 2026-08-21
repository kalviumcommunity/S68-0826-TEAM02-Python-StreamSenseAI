"""Streamlit entry point for the StreamSense AI dashboard."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st


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


def status_card(column: st.delta_generator.DeltaGenerator, label: str, value: int | None, expected: int) -> None:
    """Render one data-readiness metric."""
    if value is None:
        column.metric(label, "Unavailable")
        return
    delta = "Expected count" if value == expected else f"Expected {expected:,}"
    column.metric(label, f"{value:,}", delta=delta, delta_color="normal" if value == expected else "off")


def render_overview() -> None:
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

    if page == "Overview":
        render_overview()
    elif page == "About":
        render_about()
    else:
        render_placeholder(page)


if __name__ == "__main__":
    main()
