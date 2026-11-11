"""Operational trends and charging-risk detail page."""

import logging

import matplotlib.pyplot as plt
import streamlit as st

from dashboard_components import (
    get_source_data,
    render_alert_center,
    render_kpis,
    sidebar_filters,
)
from visualizations import build_dashboard_figure

def main() -> None:
    """Show the filtered operational chart panels and alert center."""
    st.title("Operations Insights")
    st.caption("Hourly demand, charging cost, battery temperature, and overstay risk")

    try:
        data = get_source_data()
    except (FileNotFoundError, ValueError, OSError) as exc:
        logging.exception("Could not load operations data")
        st.error(f"Could not load the campus data: {exc}")
        return

    filtered = sidebar_filters(data)
    render_kpis(data, filtered)
    if filtered.empty:
        st.info("No sessions match these filters.")
    else:
        figure = build_dashboard_figure(filtered)
        st.pyplot(figure, width="stretch")
        plt.close(figure)

    render_alert_center(filtered)
    st.info(
        "Hourly session energy is a demand proxy. The solar line is modeled "
        "because measured solar data is not supplied."
    )


main()
