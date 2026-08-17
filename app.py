"""Entry point for the StreamSense AI dashboard."""

import streamlit as st


st.set_page_config(
    page_title="StreamSense AI",
    page_icon="📺",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main() -> None:
    """Render the initial product shell while data modules are developed."""
    st.sidebar.title("📺 StreamSense AI")
    page = st.sidebar.radio(
        "Navigation",
        [
            "Overview",
            "Viewer Analytics",
            "Content Analytics",
            "Retention Insights",
            "About",
        ],
    )

    if page == "Overview":
        st.title("StreamSense AI")
        st.subheader("Viewer engagement intelligence for smarter content decisions")
        st.info(
            "The analytics pipeline is being prepared. Dashboard metrics and "
            "interactive insights will appear here once the synthetic data is generated."
        )
        st.markdown(
            """
            **Our question:** Which viewing behaviours—watch duration, pause frequency,
            and episode completion—are associated with subscriber retention?
            """
        )
    elif page == "About":
        st.title("About StreamSense AI")
        st.write(
            "StreamSense AI helps acquisition teams turn viewer behaviour into "
            "evidence-based content greenlighting decisions."
        )
    else:
        st.title(page)
        st.info("This section will be connected to the analytics dataset in the next build stage.")


if __name__ == "__main__":
    main()
