"""Dataset coverage, feature notes, and clean CSV download."""

import logging

import streamlit as st

from dashboard_components import get_source_data, render_csv_download, sidebar_filters

def main() -> None:
    """Show cleaning coverage and the currently filtered records."""
    st.title("Data Quality")
    st.caption("Review the cleaned session data and its calculated fields")

    try:
        data = get_source_data()
    except (FileNotFoundError, ValueError, OSError) as exc:
        logging.exception("Could not load data quality page")
        st.error(f"Could not load the campus data: {exc}")
        return

    filtered = sidebar_filters(data)
    date_matches = (
        int(data["Date_Matched"].sum()) if "Date_Matched" in data else 0
    )
    undated_sessions = len(data) - date_matches
    metrics = st.columns(3)
    metrics[0].metric("EV sessions", f"{len(data):,}")
    metrics[1].metric("Sales date matches", f"{date_matches:,}")
    metrics[2].metric("Sessions without a match", f"{undated_sessions:,}")

    st.subheader("Feature definitions")
    st.markdown(
        "- **Power rate:** Energy_kWh divided by Duration_Hours.\n"
        "- **Carbon savings:** Energy_kWh multiplied by 0.475 kg CO2 per kWh.\n"
        "- **Session bill:** time-based charger fee, peak surcharge, "
        "and overstay fee.\n"
        "- **Date matching:** Pair session and transaction IDs by numeric suffix."
    )
    st.caption(
        "Unmatched sessions retain a blank Session_Date. Their dates are not guessed."
    )
    st.subheader("Filtered cleaned data")
    st.dataframe(filtered, width="stretch", hide_index=True)
    render_csv_download(filtered, key="quality_download")


main()
