"""Reusable Streamlit filter controls for StreamSense AI dashboard pages."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Sequence

import pandas as pd
import streamlit as st


@dataclass(frozen=True)
class DashboardFilters:
    """A consistent set of viewer and content filters selected in the sidebar."""

    genres: tuple[str, ...]
    subscription_plan: str
    devices: tuple[str, ...]
    start_date: date
    end_date: date


def _normalize_date_range(selection: object, default_start: date, default_end: date) -> tuple[date, date]:
    """Normalize Streamlit date input output into a reliable start and end date pair."""
    if isinstance(selection, date):
        return selection, selection
    if isinstance(selection, tuple) and len(selection) == 2 and all(isinstance(value, date) for value in selection):
        start_date, end_date = selection
        return (start_date, end_date) if start_date <= end_date else (end_date, start_date)
    return default_start, default_end


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

    start_date, end_date = _normalize_date_range(date_range, min_date, max_date)
    return DashboardFilters(
        genres=tuple(selected_genres),
        subscription_plan=subscription_plan,
        devices=tuple(selected_devices),
        start_date=start_date,
        end_date=end_date,
    )


def apply_dashboard_filters(
    subscribers: pd.DataFrame,
    content: pd.DataFrame,
    activity: pd.DataFrame,
    selected_filters: DashboardFilters | None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Apply sidebar selections to raw dashboard inputs without computing KPIs.

    The same filtered data can be passed to all dashboard views, ensuring the
    displayed metrics and charts respond consistently to user selections.
    """
    if selected_filters is None:
        return subscribers, content, activity

    filtered_subscribers = subscribers.copy()
    filtered_content = content.copy()
    filtered_activity = activity.copy()

    if selected_filters.subscription_plan != "All plans":
        filtered_subscribers = filtered_subscribers.loc[
            filtered_subscribers["subscription_plan"].eq(selected_filters.subscription_plan)
        ]
    if selected_filters.genres:
        filtered_content = filtered_content.loc[filtered_content["genre"].isin(selected_filters.genres)]
    if selected_filters.devices:
        filtered_activity = filtered_activity.loc[filtered_activity["device"].isin(selected_filters.devices)]

    watch_dates = pd.to_datetime(filtered_activity["watch_date"], errors="coerce").dt.date
    filtered_activity = filtered_activity.loc[
        watch_dates.between(selected_filters.start_date, selected_filters.end_date)
    ]
    filtered_activity = filtered_activity.loc[
        filtered_activity["user_id"].isin(filtered_subscribers["user_id"])
        & filtered_activity["show_id"].isin(filtered_content["show_id"])
    ]
    filtered_subscribers = filtered_subscribers.loc[
        filtered_subscribers["user_id"].isin(filtered_activity["user_id"])
    ]
    return filtered_subscribers, filtered_content, filtered_activity
