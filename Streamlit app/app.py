"""Smart Campus Energy and EV Fleet dashboard."""

import logging

import matplotlib.pyplot as plt
import streamlit as st

from dashboard_components import (
    get_source_data,
    render_alert_center,
    render_csv_download,
    render_kpis,
    sidebar_filters,
)
from visualizations import build_dashboard_figure

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
st.set_page_config(page_title="Smart Campus Energy", page_icon="⚡", layout="wide")


def main() -> None:
    """Render the dashboard overview and its shared filters."""
    st.title("Executive KPI")
    st.caption("Energy delivery, charging costs, transaction dates, and fleet alerts")

    try:
        data = get_source_data()
    except (FileNotFoundError, ValueError, OSError) as exc:
        logging.exception("Could not load campus data")
        st.error(f"Could not load the campus data: {exc}")
        return

    filtered = sidebar_filters(data)
    render_kpis(data, filtered)
    st.divider()

    if filtered.empty:
        st.info("No sessions match these filters. Adjust the sidebar and try again.")
    else:
        st.subheader("Campus energy and charging patterns")
        figure = build_dashboard_figure(filtered)
        st.pyplot(figure, width="stretch")
        plt.close(figure)

    render_alert_center(filtered)
    st.subheader("Filtered session data")
    st.dataframe(filtered, width="stretch", hide_index=True)
    render_csv_download(filtered, key="overview_download")
    st.caption(
        "Solar generation is a modeled curve because measured solar data is not "
        "included in the supplied CSV files."
    )


page = st.navigation(
    [
        st.Page(
            main,
            title="Executive KPI",
            icon=":material/dashboard:",
            default=True,
        ),
        st.Page(
            "pages/1_Operations_Insights.py",
            title="Operations Insights",
            icon=":material/insights:",
        ),
        st.Page(
            "pages/2_Data_Quality.py",
            title="Data Quality",
            icon=":material/fact_check:",
        ),
    ],
    position="sidebar",
)
page.run()
