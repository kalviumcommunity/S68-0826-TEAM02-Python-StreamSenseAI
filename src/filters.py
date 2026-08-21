"""Reusable Streamlit filter controls for StreamSense AI dashboard pages."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Sequence

import streamlit as st


@dataclass(frozen=True)
class DashboardFilters:
    """A consistent set of viewer and content filters selected in the sidebar."""

    genres: tuple[str, ...]
    subscription_plan: str
    devices: tuple[str, ...]
    start_date: date
    end_date: date


def render_global_filters(
    genres: Sequence[str],
    subscription_plans: Sequence[str],
    devices: Sequence[str],
    min_date: date,
    max_date: date,
) -> DashboardFilters:
    """Render global dashboard filters and return their selected values.

    Data filtering remains the responsibility of each analytics page. This function
    only provides a shared, consistent interface for collecting user selections.
    """
    with st.sidebar:
        st.divider()
        st.markdown("### Filters")
        selected_genres = st.multiselect("Genre", options=sorted(genres), placeholder="All genres")
        subscription_plan = st.selectbox("Subscription type", options=["All plans", *sorted(subscription_plans)])
        selected_devices = st.multiselect("Device", options=sorted(devices), placeholder="All devices")
        date_range = st.date_input("Viewing date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)

    start_date, end_date = date_range
    return DashboardFilters(
        genres=tuple(selected_genres),
        subscription_plan=subscription_plan,
        devices=tuple(selected_devices),
        start_date=start_date,
        end_date=end_date,
    )
