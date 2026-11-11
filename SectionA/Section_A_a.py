"""Part A: NumPy and Pandas Processing for EV Campus Grid Telemetry.

This section demonstrates 2D array slicing, boolean masking, missing value
imputation, and group-wise revenue calculations following PEP 8 standards.
"""
import csv
import numpy as np
import pandas as pd

df = pd.read_csv("ev_campus_dataset.csv")

def numpy_peak_hours(df):
    """Calculate hourly energy totals and identify peak load hours using NumPy.

    Performs 2D array slicing for peak hours (08:00 to 17:59).
    """
    data = df[["Start_Hour", "Energy_kWh"]].to_numpy()
    hours = data[:, 0]
    energy = np.nan_to_num(data[:, 1], nan=0.0)

    totals = np.zeros(24)
    for i in range(len(hours)):
        h = int(hours[i])
        totals[h] += energy[i]

    peak_window = totals[8:18]
    peak_hour = int(totals.argmax())

    return totals, peak_window, peak_hour


def numpy_mask(df):
    """Apply boolean masking via NumPy to detect critical battery temperatures."""
    temp_data = df["Battery_Temp_C"].to_numpy()
    temp_data = np.nan_to_num(temp_data, nan=0.0)

    Exceed_temp_mask = temp_data > 45.0
    critical_temps = temp_data[Exceed_temp_mask]

    return Exceed_temp_mask, critical_temps


def pandas_impute_missing(df):
    """Handle missing power/energy data using median imputation in Pandas."""
    median_val = df["Energy_kWh"].median()
    df["Energy_kWh_Imputed"] = df["Energy_kWh"].fillna(median_val)
    print(f"Imputed missing Energy_kWh with median: {median_val:.2f}")
    return df


def pandas_group_revenue(df):
    """Compute group-wise charging revenue using .groupby().

    Base fees: AC = RM 6, DC = RM 15.
    """
    df["Base_Fee_RM"] = df["Charger_Type"].map(
        {"AC": 6.0, "DC": 15.0}
    )
    df["Total_Revenue_RM"] = df["Base_Fee_RM"] + (
        df["Energy_kWh_Imputed"] * 0.50
    )

    grouped_revenue = (
        df.groupby("Charger_Type")["Total_Revenue_RM"]
        .sum()
        .reset_index()
    )
    return grouped_revenue

# --- Execution and Output Generation ---
# 1. Run the functions
totals, peak_window, peak_hour = numpy_peak_hours(df)
Exceed_temp_mask, critical_temps = numpy_mask(df)
df = pandas_impute_missing(df)
revenue_summary = pandas_group_revenue(df)

# 2. Add flags back to dataframe
df["Is_Peak_Window"] = (df["Start_Hour"] >= 8) & (df["Start_Hour"] < 18)
df["Is_Peak_Hour"] = (df["Start_Hour"] == peak_hour)
df["Is_High_Temp"] = Exceed_temp_mask

# 3. Save the final processed dataset to a new CSV at the very end
df.to_csv("ev_campus_dataset_processed.csv", index=False)
print("Processed dataset successfully saved to 'ev_campus_dataset_processed.csv'.")