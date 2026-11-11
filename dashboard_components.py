"""Shared data loading, filters, metrics, alerts, and downloads."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from data_pipeline import (
    EV_COLUMNS,
    SALES_COLUMNS,
    attach_sales_dates,
    clean_dataset,
    find_default_input,
)

PROJECT_DIR = Path(__file__).resolve().parent


@st.cache_data(show_spinner="Loading campus data...")
def _load_data(
    session_path: str,
    session_modified: float,
    sales_path: str,
    sales_modified: float,
) -> pd.DataFrame:
    """Load the cleaned session CSV and refresh its sales date/revenue match."""
    del session_modified, sales_modified
    sessions = clean_dataset(pd.read_csv(session_path))
    sales = clean_dataset(pd.read_csv(sales_path))

    if not EV_COLUMNS.issubset(sessions.columns):
        raise ValueError(
            "cleaned_energy_sales_data.csv does not contain EV session columns."
        )
    if not SALES_COLUMNS.issubset(sales.columns):
        raise ValueError("sales_data.csv does not contain transaction columns.")

    # These fields are refreshed from the current sales file below.
    sessions = sessions.drop(
        columns=["Session_Date", "Sales_Revenue_MYR", "Date_Matched"],
        errors="ignore",
    )
    return attach_sales_dates(sessions, sales)


def get_source_data() -> pd.DataFrame:
    """Load cleaned EV sessions and the sales source used for dates/revenue."""
    session_path = PROJECT_DIR / "cleaned_energy_sales_data.csv"
    if not session_path.is_file():
        session_path = find_default_input(PROJECT_DIR)

    sales_path = PROJECT_DIR / "sales_data.csv"
    if not sales_path.is_file():
        raise FileNotFoundError(f"Sales data file not found: {sales_path}")

    sales_modified = sales_path.stat().st_mtime if sales_path.is_file() else 0.0
    return _load_data(
        str(session_path),
        session_path.stat().st_mtime,
        str(sales_path),
        sales_modified,
    )


def sidebar_filters(data: pd.DataFrame) -> pd.DataFrame:
    """Apply date, energy, and charger filters to all session records."""
    st.sidebar.header("Filters")
    filtered = data.copy()

    if "Session_Date" in data:
        session_dates = pd.to_datetime(data["Session_Date"], errors="coerce")
    else:
        session_dates = pd.Series(pd.NaT, index=data.index, dtype="datetime64[ns]")
    has_dates = session_dates.notna().any()
    if has_dates:
        date_values = session_dates.dropna()
        start_date = date_values.min().date()
        end_date = date_values.max().date()
        selected_dates = st.sidebar.date_input(
            "Session date range",
            value=(start_date, end_date),
            min_value=start_date,
            max_value=end_date,
            help="Dates are matched from sales_data.csv using the shared ID suffix.",
        )
        include_undated = st.sidebar.checkbox(
            "Include sessions without a matching sales date",
            value=True,
        )
        if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
            selected_start, selected_end = selected_dates
        else:
            selected_start = selected_end = selected_dates
        dates = session_dates.dt.date
        date_mask = dates.between(selected_start, selected_end)
        if include_undated:
            date_mask |= dates.isna()
        filtered = filtered.loc[date_mask]
        matched_count = int(session_dates.notna().sum())
        st.sidebar.caption(
            f"{matched_count:,} of {len(data):,} sessions have matched dates."
        )
    else:
        st.sidebar.date_input("Session date range", disabled=True)
        st.sidebar.caption("No session dates are available in the input files.")

    energy_max = max(float(data["Energy_kWh"].max()), 1.0)
    minimum_energy = st.sidebar.slider(
        "Minimum energy delivered (kWh)",
        min_value=0.0,
        max_value=round(energy_max, 1),
        value=0.0,
        step=0.5,
    )
    chargers = sorted(data["Charger_Type"].dropna().unique().tolist())
    selected_chargers = st.sidebar.multiselect(
        "Charger type",
        options=chargers,
        default=chargers,
    )

    filtered = filtered.loc[
        filtered["Energy_kWh"].ge(minimum_energy)
        & filtered["Charger_Type"].isin(selected_chargers)
    ]
    st.sidebar.caption(f"Showing {len(filtered):,} of {len(data):,} sessions.")
    return filtered


def _total_revenue(data: pd.DataFrame) -> float:
    """Add EV session billing and matched retail transaction revenue."""
    session_revenue = data["Net_Billable_MYR"].sum()
    sales_revenue = data.get("Sales_Revenue_MYR", pd.Series(0, index=data.index)).sum()
    return float(session_revenue + sales_revenue)


def render_kpis(data: pd.DataFrame, filtered: pd.DataFrame) -> None:
    """Show energy, carbon, combined revenue, and active alert metrics."""
    energy = float(filtered["Energy_kWh"].sum())
    carbon = float(filtered["Carbon_Savings_kgCO2"].sum())
    revenue = _total_revenue(filtered)
    all_revenue = _total_revenue(data)
    threshold = float(st.session_state.get("temperature_threshold", 42.0))
    active = (
        filtered["Battery_Temp_C"].ge(threshold)
        | filtered["Overstay_Mins"].ge(30)
    ).sum()

    metrics = st.columns(4)
    metrics[0].metric(
        "Total Energy Delivered",
        f"{energy:,.0f} kWh",
        f"{energy - data['Energy_kWh'].sum():+,.0f} kWh vs all sessions",
    )
    metrics[1].metric(
        "Carbon Offset",
        f"{carbon:,.0f} kg CO2",
        f"{carbon - data['Carbon_Savings_kgCO2'].sum():+,.0f} kg vs all sessions",
    )
    metrics[2].metric(
        "Total Revenue",
        f"RM {revenue:,.2f}",
        f"RM {revenue - all_revenue:+,.2f} vs all sessions",
    )
    metrics[3].metric("Active Alert Count", f"{active:,}", "temperature or overstay")


def render_alert_center(data: pd.DataFrame) -> None:
    """Show high-temperature and long-overstay session warnings."""
    st.subheader("High-Risk Overstay and Alert Center")
    threshold = st.slider(
        "Battery temperature alert threshold (C)",
        min_value=30.0,
        max_value=60.0,
        value=42.0,
        step=0.5,
        key="temperature_threshold",
    )
    hot = data.loc[data["Battery_Temp_C"].ge(threshold)]
    overstay = data.loc[data["Overstay_Mins"].ge(30)]

    if not hot.empty:
        st.error(f"{len(hot):,} session(s) are at or above {threshold:.1f} C.")
    if not overstay.empty:
        st.warning(f"{len(overstay):,} session(s) overstayed by at least 30 minutes.")
    if hot.empty and overstay.empty:
        st.success("No sessions meet the current alert rules.")

    risky_rows = data.loc[hot.index.union(overstay.index)]
    if not risky_rows.empty:
        columns = [
            "Session_ID",
            "Session_Date",
            "Charger_Type",
            "User_Type",
            "Energy_kWh",
            "Battery_Temp_C",
            "Overstay_Mins",
        ]
        columns = [column for column in columns if column in risky_rows]
        st.dataframe(
            risky_rows[columns].sort_values("Battery_Temp_C", ascending=False),
            width="stretch",
            hide_index=True,
        )


def render_csv_download(data: pd.DataFrame, key: str) -> None:
    """Download the current filtered session data as a CSV file."""
    st.download_button(
        "Download filtered sessions",
        data=data.to_csv(index=False).encode("utf-8"),
        file_name="filtered_campus_energy_sessions.csv",
        mime="text/csv",
        key=key,
    )
