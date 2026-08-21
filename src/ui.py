"""Shared presentation components for the StreamSense AI Streamlit interface."""

from __future__ import annotations

import streamlit as st


def apply_global_styles() -> None:
    """Apply a small, consistent visual system to the Streamlit dashboard."""
    st.markdown(
        """
        <style>
            .stApp { background: #f7f8fc; }
            [data-testid="stSidebar"] { background: #101828; }
            [data-testid="stSidebar"] * { color: #f8fafc; }
            [data-testid="stSidebar"] .stCaption { color: #98a2b3 !important; }
            [data-testid="stSidebar"] [data-testid="stRadio"] label { border-radius: 8px; padding: 0.35rem 0.5rem; }
            [data-testid="stMetric"] { background: #ffffff; border: 1px solid #eaecf0; border-radius: 12px; padding: 1rem; }
            [data-testid="stMetricValue"] { color: #101828; }
            .dashboard-eyebrow { color: #475467; font-size: 0.75rem; font-weight: 700; letter-spacing: 0.09em; margin-bottom: 0.25rem; }
            .dashboard-heading { color: #101828; font-size: 2rem; font-weight: 700; margin: 0; }
            .dashboard-description { color: #667085; font-size: 1rem; margin-top: 0.35rem; }
            .section-heading { color: #101828; font-size: 1.18rem; font-weight: 700; margin-bottom: 0.2rem; }
            .section-description { color: #667085; margin-top: 0; }
            .empty-state { background: #ffffff; border: 1px dashed #d0d5dd; border-radius: 12px; color: #475467; padding: 2rem; text-align: center; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_page_header(eyebrow: str, title: str, description: str) -> None:
    """Render the shared page heading hierarchy."""
    st.markdown(f'<div class="dashboard-eyebrow">{eyebrow.upper()}</div>', unsafe_allow_html=True)
    st.markdown(f'<h1 class="dashboard-heading">{title}</h1>', unsafe_allow_html=True)
    st.markdown(f'<p class="dashboard-description">{description}</p>', unsafe_allow_html=True)


def render_section_header(title: str, description: str) -> None:
    """Render a consistent section title and supporting description."""
    st.markdown(f'<div class="section-heading">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<p class="section-description">{description}</p>', unsafe_allow_html=True)


def render_empty_state(title: str, description: str) -> None:
    """Render a clear placeholder for a scheduled dashboard section."""
    st.markdown(f'<div class="empty-state"><strong>{title}</strong><br>{description}</div>', unsafe_allow_html=True)
