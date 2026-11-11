"""Part B: Functional Programming Pipeline for EV Charging Risk & Surcharge.

This section uses functional programming constructs (filter, map, reduce,
and list comprehensions) with lambda functions to process high-risk charging
sessions, apply surcharge multipliers, and compute total surcharge revenue.
"""
from functools import reduce
import pandas as pd

# Load dataset
df = pd.read_csv("ev_campus_dataset.csv")

# Convert DataFrame records to a list of dictionaries for functional processing
# (Memory efficient as it iterates through records lazily or via generators)
sessions = df.to_dict(orient="records")

# --- 1. Filter: Overstay > 20 mins AND Battery Temp > 40°C ---
# Lambda predicate defines criteria for high-risk alert sessions.
is_high_risk = lambda s: (s["Overstay_Mins"] > 20) and (s["Battery_Temp_C"] > 40.0)

# Using filter() combined with a lambda function
high_risk_sessions = list(filter(is_high_risk, sessions))


# --- 2. Map: Apply 15% Surcharge Multiplier to Base Fee ---
# Base fee calculation: AC = RM 6, DC = RM 15 (consistent with Part A)
def compute_base_fee(charger_type):
    return 6.0 if charger_type == "AC" else 15.0


# Lambda mapping function to calculate surcharge (15% multiplier on base fee + energy fee)
# Memory efficient: transforms records without altering the immutable raw dataset structure.
calculate_surcharge = lambda s: {
    **s,
    "Surcharge_RM": (compute_base_fee(s["Charger_Type"]) + (s["Energy_kWh"] * 0.50)) * 0.15
}

surcharged_sessions = list(map(calculate_surcharge, high_risk_sessions))


# --- 3. Reduce: Calculate Total Surcharge Revenue Across Alert Sessions ---
# Extract individual surcharge amounts
surcharge_values = [s["Surcharge_RM"] for s in surcharged_sessions]

# Using reduce() to aggregate total surcharge revenue generated
# Returns 0.0 if there are no matching alert sessions.
total_surcharge_revenue = reduce(lambda acc, val: acc + val, surcharge_values, 0.0)


# --- Execution and Output ---
print(f"Total High-Risk Alert Sessions: {len(high_risk_sessions)}")
print(f"Total Surcharge Revenue Generated: RM {total_surcharge_revenue:.2f}")