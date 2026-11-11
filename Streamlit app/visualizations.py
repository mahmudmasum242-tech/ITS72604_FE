"""Three-panel Matplotlib and Seaborn views for EV charging sessions."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(__file__).resolve().parent / ".mplconfig")
)

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from data_pipeline import find_default_input, load_and_clean_data

USER_COLORS = {
    "Student": "#3674B5",
    "Staff": "#578FCA",
    "Visitor": "#A1E3F9",
}


def set_chart_style() -> None:
    """Apply readable defaults to dashboard and exported charts."""
    sns.set_theme(style="whitegrid", context="talk")
    plt.rcParams.update(
        {
            "figure.dpi": 130,
            "savefig.dpi": 240,
            "axes.titleweight": "bold",
            "axes.labelcolor": "#243447",
            "text.color": "#172B4D",
            "font.family": "DejaVu Sans",
        }
    )


def plot_hourly_demand(data: pd.DataFrame, axis: plt.Axes) -> None:
    """Plot hourly session-energy demand and an illustrative solar curve."""
    hourly = data.groupby("Start_Hour")["Energy_kWh"].sum()
    hourly = hourly.reindex(range(24), fill_value=0)
    solar_shape = np.maximum(np.sin(np.pi * (hourly.index - 6) / 12), 0)
    solar = solar_shape * (hourly.max() * 0.72 if hourly.max() else 0)

    axis.plot(
        hourly.index,
        hourly.values,
        color="#D55E00",
        linewidth=2.4,
        marker="o",
        label="Session energy (demand proxy)",
    )
    axis.plot(
        hourly.index,
        solar,
        color="#009E73",
        linewidth=2.4,
        label="Modeled solar generation",
    )
    axis.fill_between(hourly.index, solar, color="#009E73", alpha=0.12)
    axis.set(
        title="Hourly demand and solar",
        xlabel="Session start hour",
        ylabel="Energy (kWh)",
        xticks=range(0, 24, 3),
    )
    axis.legend(fontsize=8, loc="upper left")
    axis.text(
        0.02,
        0.02,
        "Solar curve is illustrative",
        transform=axis.transAxes,
        fontsize=8,
        color="#52606D",
    )


def plot_session_costs(data: pd.DataFrame, axis: plt.Axes) -> None:
    """Compare charging-session cost distributions by user type."""
    order = ["Student", "Staff", "Visitor"]
    plot_data = data.loc[data["User_Type"].isin(order)]
    sns.boxplot(
        data=plot_data,
        x="User_Type",
        y="Net_Billable_MYR",
        order=order,
        hue="User_Type",
        palette=USER_COLORS,
        legend=False,
        showfliers=False,
        ax=axis,
    )
    axis.set(
        title="Charging cost by user type",
        xlabel="User type",
        ylabel="Session cost (MYR)",
    )
    axis.tick_params(axis="x", rotation=15)


def plot_temperature_energy(data: pd.DataFrame, axis: plt.Axes) -> None:
    """Plot battery temperature and delivered energy with a linear trend."""
    sns.regplot(
        data=data,
        x="Battery_Temp_C",
        y="Energy_kWh",
        ci=None,
        scatter_kws={"alpha": 0.48, "s": 26, "color": "#3674B5"},
        line_kws={"color": "#D55E00", "linewidth": 2.5},
        ax=axis,
    )
    axis.set(
        title="Temperature and energy",
        xlabel="Battery temperature (C)",
        ylabel="Energy delivered (kWh)",
    )
    axis.text(
        0.02,
        0.02,
        "Linear trend",
        transform=axis.transAxes,
        fontsize=8,
        color="#52606D",
    )


def build_dashboard_figure(data: pd.DataFrame) -> plt.Figure:
    """Create hourly, user-cost, and temperature-energy chart panels."""
    if data.empty:
        raise ValueError("At least one session is required to create the charts.")
    set_chart_style()
    figure, axes = plt.subplots(1, 3, figsize=(18, 6), constrained_layout=True)
    figure.suptitle("Smart Campus Energy and EV Fleet", fontsize=20, weight="bold")

    plot_hourly_demand(data, axes[0])
    plot_session_costs(data, axes[1])
    plot_temperature_energy(data, axes[2])

    for axis in axes:
        axis.spines[["top", "right"]].set_visible(False)
        axis.grid(axis="y", alpha=0.25)
    return figure


def save_dashboard_figure(
    data: pd.DataFrame,
    output_path: Path | str = "energy_dashboard_panels.png",
) -> Path:
    """Save all panels as a PNG image and return the saved path."""
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure = build_dashboard_figure(data)
    figure.savefig(destination, bbox_inches="tight", facecolor="white")
    plt.close(figure)
    return destination


def main() -> int:
    """Create a chart image from the default or supplied EV dataset."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", help="Input EV session CSV")
    parser.add_argument("--output", default="energy_dashboard_panels.png")
    args = parser.parse_args()
    source = Path(args.input) if args.input else find_default_input()
    data = load_and_clean_data(source)
    if "Energy_kWh" not in data or "Battery_Temp_C" not in data:
        parser.error("Charts require an EV session dataset.")
    saved_path = save_dashboard_figure(data, args.output)
    print(f"Saved charts to {saved_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
