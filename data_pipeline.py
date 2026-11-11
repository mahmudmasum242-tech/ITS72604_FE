"""Clean campus EV sessions and retail transactions from CSV files."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd

LOGGER = logging.getLogger(__name__)

DEFAULT_INPUTS = ("ev_campus_dataset.csv", "sales_data.csv")
DEFAULT_OUTPUT = "cleaned_energy_sales_data.csv"
CARBON_FACTOR = 0.475
PEAK_HOURS = range(17, 21)
PEAK_SURCHARGE = 0.25
OVERTIME_RATE_MYR = 0.50
CHARGER_RATES_MYR = {"AC": 6.0, "DC": 15.0}

EV_COLUMNS = {
    "Session_ID",
    "Charger_Type",
    "User_Type",
    "Start_Hour",
    "Duration_Mins",
    "Energy_kWh",
    "Overstay_Mins",
    "Battery_Temp_C",
    "Grid_Status_Label",
}
SALES_COLUMNS = {
    "Transaction_ID",
    "Transaction_Date",
    "Units_Sold",
    "Unit_Price_MYR",
    "Total_Revenue_MYR",
}
VALID_CATEGORIES = {
    "Charger_Type": {"AC", "DC"},
    "User_Type": {"Student", "Staff", "Visitor"},
    "Grid_Status_Label": {"Normal", "Grid_Surge", "Overheated"},
}


def find_default_input(folder: Path | str = ".") -> Path:
    """Return the first supported CSV found in a folder."""
    root = Path(folder)
    for name in DEFAULT_INPUTS:
        path = root / name
        if path.is_file():
            return path
    raise FileNotFoundError(
        "Place ev_campus_dataset.csv or sales_data.csv in the project folder."
    )


def _read_csv(path: Path) -> pd.DataFrame:
    """Read a non-empty CSV and raise a useful error on failure."""
    if not path.is_file():
        raise FileNotFoundError(f"CSV file not found: {path}")
    try:
        data = pd.read_csv(path)
    except (OSError, UnicodeDecodeError, pd.errors.ParserError) as exc:
        raise ValueError(f"Could not read {path.name}: {exc}") from exc
    if data.empty:
        raise ValueError(f"CSV contains no data rows: {path.name}")
    return data


def _fill_numeric_medians(data: pd.DataFrame, columns: list[str]) -> None:
    """Coerce numeric fields and replace missing values with column medians."""
    for column in columns:
        data[column] = pd.to_numeric(data[column], errors="coerce")
        missing = int(data[column].isna().sum())
        if missing:
            median = data[column].median()
            data[column] = data[column].fillna(0 if pd.isna(median) else median)
            LOGGER.info("Filled %s missing %s values with the median.", missing, column)


def _validate_categories(data: pd.DataFrame) -> None:
    """Trim categories and replace invalid EV categories with ``Unknown``."""
    for column in data.select_dtypes(include=["object", "string"]).columns:
        values = data[column].astype("string").str.strip()
        values = values.mask(values.eq("") | values.isna(), "Unknown")
        allowed = VALID_CATEGORIES.get(column)
        if allowed:
            canonical = {value.casefold(): value for value in allowed}
            normalized = values.str.casefold().map(canonical)
            invalid = normalized.isna() & values.ne("Unknown")
            if invalid.any():
                LOGGER.warning(
                    "Unknown categories in %s: %s",
                    column,
                    values[invalid].unique()[:5],
                )
            values = normalized.fillna("Unknown")
        data[column] = values.astype(str)


def _add_ev_features(data: pd.DataFrame) -> pd.DataFrame:
    """Calculate power, carbon savings, and session billing fields."""
    data["Duration_Hours"] = data["Duration_Mins"].clip(lower=0) / 60
    duration = data["Duration_Hours"].replace(0, np.nan)
    data["Power_Rate_kW"] = (data["Energy_kWh"] / duration).fillna(0)
    data["Carbon_Savings_kgCO2"] = data["Energy_kWh"] * CARBON_FACTOR

    rates = data["Charger_Type"].map(CHARGER_RATES_MYR).fillna(0)
    data["Base_Fee_MYR"] = data["Duration_Hours"] * rates
    peak = data["Start_Hour"].isin(PEAK_HOURS)
    data["Peak_Surge_MYR"] = data["Base_Fee_MYR"] * peak * PEAK_SURCHARGE
    data["Overstay_Fee_MYR"] = data["Overstay_Mins"] * OVERTIME_RATE_MYR
    data["Net_Billable_MYR"] = (
        data["Base_Fee_MYR"]
        + data["Peak_Surge_MYR"]
        + data["Overstay_Fee_MYR"]
    ).round(2)
    return data


def clean_dataset(raw: pd.DataFrame) -> pd.DataFrame:
    """Clean an EV-session or retail-sales DataFrame and add its features."""
    data = raw.copy()
    columns = set(data.columns)

    if EV_COLUMNS.issubset(columns):
        numeric_columns = [
            "Start_Hour",
            "Duration_Mins",
            "Energy_kWh",
            "Overstay_Mins",
            "Battery_Temp_C",
        ]
        _fill_numeric_medians(data, numeric_columns)
        _validate_categories(data)
        data["Start_Hour"] = data["Start_Hour"].clip(0, 23).round().astype(int)
        for column in ("Duration_Mins", "Energy_kWh", "Overstay_Mins"):
            data[column] = data[column].clip(lower=0)
        if "Session_Date" in data:
            data["Session_Date"] = pd.to_datetime(data["Session_Date"], errors="coerce")
        return _add_ev_features(data)

    if SALES_COLUMNS.issubset(columns):
        _fill_numeric_medians(
            data, ["Units_Sold", "Unit_Price_MYR", "Total_Revenue_MYR"]
        )
        _validate_categories(data)
        data["Transaction_Date"] = pd.to_datetime(
            data["Transaction_Date"], dayfirst=True, errors="coerce"
        )
        for column in ("Units_Sold", "Unit_Price_MYR", "Total_Revenue_MYR"):
            data[column] = data[column].clip(lower=0)
        data["Net_Billable_MYR"] = data["Total_Revenue_MYR"].round(2)
        return data

    raise ValueError(
        "CSV headers do not match the EV session or sales transaction schema."
    )


def _id_suffix(values: pd.Series) -> pd.Series:
    """Extract the numeric suffix used to align session and transaction IDs."""
    return values.astype("string").str.extract(r"(\d+)$", expand=False)


def attach_sales_dates(
    sessions: pd.DataFrame, sales: pd.DataFrame
) -> pd.DataFrame:
    """Attach transaction dates to sessions with matching numeric ID suffixes.

    The supplied files have 500 matching suffixes (1000 through 1499). The
    remaining sessions keep a missing date; the function does not invent dates.
    """
    if "Session_ID" not in sessions or "Transaction_ID" not in sales:
        return sessions

    sales_data = sales.copy()
    sales_data["Transaction_Date"] = pd.to_datetime(
        sales_data["Transaction_Date"], dayfirst=True, errors="coerce"
    )
    sales_data["_id_suffix"] = _id_suffix(sales_data["Transaction_ID"])
    if sales_data["_id_suffix"].duplicated().any():
        raise ValueError("Transaction ID suffixes must be unique to match sessions.")

    sales_data = sales_data[
        ["_id_suffix", "Transaction_Date", "Total_Revenue_MYR"]
    ].rename(
        columns={
            "Transaction_Date": "Matched_Transaction_Date",
            "Total_Revenue_MYR": "Sales_Revenue_MYR",
        }
    )
    result = sessions.copy()
    result["_id_suffix"] = _id_suffix(result["Session_ID"])
    if result["_id_suffix"].duplicated().any():
        raise ValueError("Session ID suffixes must be unique to match sales dates.")

    result = result.merge(
        sales_data,
        on="_id_suffix",
        how="left",
        validate="one_to_one",
    )
    if "Session_Date" in result:
        existing = pd.to_datetime(result["Session_Date"], errors="coerce")
        result["Session_Date"] = existing.fillna(result["Matched_Transaction_Date"])
        result = result.drop(columns="Matched_Transaction_Date")
    else:
        result = result.rename(
            columns={"Matched_Transaction_Date": "Session_Date"}
        )
    result["Sales_Revenue_MYR"] = result["Sales_Revenue_MYR"].fillna(0)
    result["Date_Matched"] = result["Session_Date"].notna()
    return result.drop(columns="_id_suffix")


def load_and_clean_data(
    path: Path | str,
    sales_dates_path: Path | str | None = None,
) -> pd.DataFrame:
    """Load a CSV, clean it, and attach sales dates to EV sessions if available."""
    source = Path(path)
    cleaned = clean_dataset(_read_csv(source))
    is_ev = EV_COLUMNS.issubset(cleaned.columns)
    if not is_ev:
        LOGGER.info("Loaded %s sales rows from %s", len(cleaned), source.name)
        return cleaned

    if sales_dates_path is None:
        sales_dates_path = source.parent / "sales_data.csv"
    sales_path = Path(sales_dates_path)
    if sales_path.is_file() and sales_path.resolve() != source.resolve():
        sales = clean_dataset(_read_csv(sales_path))
        if SALES_COLUMNS.issubset(sales.columns):
            cleaned = attach_sales_dates(cleaned, sales)
    LOGGER.info("Loaded %s EV sessions from %s", len(cleaned), source.name)
    return cleaned


def export_clean_data(
    data: pd.DataFrame, output_path: Path | str = DEFAULT_OUTPUT
) -> Path:
    """Write cleaned data to CSV and return its path."""
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(destination, index=False, date_format="%Y-%m-%d")
    return destination


def print_summary(data: pd.DataFrame) -> None:
    """Print row counts, missing values, and numeric summary statistics."""
    print("\nCLEANED DATA SUMMARY")
    print(f"Rows: {len(data):,} | Columns: {len(data.columns):,}")
    print("\nMissing values by column:")
    print(data.isna().sum().to_string())
    numeric = data.select_dtypes(include="number")
    if not numeric.empty:
        print("\nNumeric summary statistics:")
        print(numeric.describe().round(2).to_string())


def main() -> int:
    """Run the cleaning and export pipeline from the command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", help="Input EV session or sales CSV")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    try:
        source = Path(args.input) if args.input else find_default_input()
        cleaned = load_and_clean_data(source)
        output = export_clean_data(cleaned, args.output)
        print_summary(cleaned)
        print(f"\nCleaned dataset saved to: {output.resolve()}")
    except (FileNotFoundError, ValueError, OSError) as exc:
        LOGGER.error("Pipeline failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
