"""Part C: Data Visualization using Matplotlib and Seaborn.

This section demonstrates both Matplotlib (low-level, manual control) and
Seaborn (high-level statistical abstraction) implementations for executive reporting.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# Load processed dataset
df = pd.read_csv("ev_campus_dataset_processed.csv")


# 1. CHART TYPE 1: Multi-Bar Plot (Hourly Revenue: AC vs. DC)

def plot_multibar_matplotlib(data_frame: pd.DataFrame):
    """Generate multi-bar plot using pure Matplotlib (manual grouping & offsets)."""
    plt.figure(figsize=(12, 6))

    # Prepare data
    hourly_revenue = (
        data_frame.groupby(["Start_Hour", "Charger_Type"])["Total_Revenue_RM"]
        .sum()
        .unstack(fill_value=0)
    )

    hours = hourly_revenue.index
    ac_vals = hourly_revenue.get("AC", np.zeros(len(hours)))
    dc_vals = hourly_revenue.get("DC", np.zeros(len(hours)))

    width = 0.35
    x = np.arange(len(hours))

    # Manual bar placement
    plt.bar(x - width / 2, ac_vals, width, label="AC Charger", color="#2b5c8f")
    plt.bar(x + width / 2, dc_vals, width, label="DC Charger", color="#e76f51")

    plt.title("Hourly Charging Revenue Split (Matplotlib - Manual Positioning)")
    plt.xlabel("Hour of the Day (00:00 - 23:00)")
    plt.ylabel("Total Revenue (RM)")
    plt.xticks(x, hours)
    plt.legend()
    plt.tight_layout()
    plt.savefig("hourly_revenue_matplotlib.png", dpi=300)
    plt.close()


def plot_multibar_seaborn(data_frame: pd.DataFrame):
    """Generate multi-bar plot using Seaborn (automatic grouping via hue)."""
    plt.figure(figsize=(12, 6))

    hourly_revenue = (
        data_frame.groupby(["Start_Hour", "Charger_Type"])["Total_Revenue_RM"]
        .sum()
        .reset_index()
    )

    # Seaborn automatically manages group offsets and legends via 'hue'
    sns.barplot(
        data=hourly_revenue,
        x="Start_Hour",
        y="Total_Revenue_RM",
        hue="Charger_Type",
        palette={"AC": "#2b5c8f", "DC": "#e76f51"},
    )

    plt.title("Hourly Charging Revenue Split (Seaborn - Automated Hue Grouping)")
    plt.xlabel("Hour of the Day (00:00 - 23:00)")
    plt.ylabel("Total Revenue (RM)")
    plt.legend(title="Charger Type")
    plt.tight_layout()
    plt.savefig("hourly_revenue_seaborn.png", dpi=300)
    plt.close()

# 2. CHART TYPE 2: Correlation Heatmap

def plot_heatmap_matplotlib(data_frame: pd.DataFrame):
    """Generate correlation heatmap using pure Matplotlib (imshow and manual text annotations)."""
    plt.figure(figsize=(8, 6))

    cols_to_corr = ["Battery_Temp_C", "Duration_Mins", "Energy_kWh", "Overstay_Mins"]
    corr_matrix = data_frame[cols_to_corr].corr().values

    # Matplotlib imshow
    cax = plt.imshow(corr_matrix, cmap="coolwarm", vmin=-1, vmax=1)
    plt.colorbar(cax, label="Pearson Correlation Coefficient")

    # Manual ticks and labels
    plt.xticks(np.arange(len(cols_to_corr)), cols_to_corr, rotation=45, ha="right")
    plt.yticks(np.arange(len(cols_to_corr)), cols_to_corr)

    # Manual cell text annotations loop
    for i in range(len(cols_to_corr)):
        for j in range(len(cols_to_corr)):
            plt.text(j, i, f"{corr_matrix[i, j]:.2f}", ha="center", va="center", color="black")

    plt.title("Telemetry Correlation Heatmap (Matplotlib)")
    plt.tight_layout()
    plt.savefig("telemetry_heatmap_matplotlib.png", dpi=300)
    plt.close()


def plot_heatmap_seaborn(data_frame: pd.DataFrame):
    """Generate correlation heatmap using Seaborn (native matrix handling and annotations)."""
    plt.figure(figsize=(8, 6))

    cols_to_corr = ["Battery_Temp_C", "Duration_Mins", "Energy_kWh", "Overstay_Mins"]
    corr_matrix = data_frame[cols_to_corr].corr()

    # Seaborn native heatmap with built-in formatting
    sns.heatmap(
        corr_matrix,
        annot=True,
        fmt=".2f",
        cmap="coolwarm",
        vmin=-1,
        vmax=1,
        linewidths=0.5,
        cbar_kws={"label": "Pearson Correlation Coefficient"},
    )

    plt.title("Telemetry Correlation Heatmap (Seaborn)")
    plt.tight_layout()
    plt.savefig("telemetry_heatmap_seaborn.png", dpi=300)
    plt.close()


def main():
    """Execute all Matplotlib and Seaborn visualization functions."""
    plot_multibar_matplotlib(df)
    plot_multibar_seaborn(df)
    plot_heatmap_matplotlib(df)
    plot_heatmap_seaborn(df)
    print("All Matplotlib and Seaborn visualization charts generated successfully!")


if __name__ == "__main__":
    main()