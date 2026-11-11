# Smart Campus Energy and EV Fleet

A simple Streamlit dashboard and CSV pipeline for campus EV charging sessions.

## Run locally

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe data_pipeline.py
.\.venv\Scripts\python.exe visualizations.py ev_campus_dataset.csv --output energy_dashboard_panels.png
.\.venv\Scripts\python.exe -m streamlit run app.py
```

The `.python-version` file targets Python 3.14. For Streamlit Community
Cloud, select Python 3.14 in the deployment dialog's **Advanced settings**;
the cloud runtime is selected separately from `requirements.txt`.

The app has an **Executive KPI** page, **Operations Insights**, and **Data Quality**.
The dashboard reads EV sessions from `cleaned_energy_sales_data.csv` and uses
`sales_data.csv` to refresh matched transaction dates and revenue. It matches
numeric suffixes in session and transaction IDs. The supplied files have 500
matching IDs and 700 unmatched sessions. Unmatched dates remain blank rather
than being invented. The date filter includes undated sessions by default, with
an option to exclude them. If the cleaned file is missing, the app falls back to
`ev_campus_dataset.csv`.

The pipeline can also clean the sales CSV directly:

```powershell
.\.venv\Scripts\python.exe data_pipeline.py sales_data.csv --output cleaned_energy_sales_data.csv
```

## Data and billing assumptions

- Numeric gaps are filled with the column median. Invalid EV categories are
  changed to `Unknown` and logged. Negative durations, energy, units, and
  prices are clipped to zero.
- Power rate is `Energy_kWh / Duration_Hours`; zero duration yields 0 kW.
- Carbon savings use `0.475 kg CO2/kWh`.
- AC and DC tariffs are modeled at RM 6 and RM 15 per hour. The model adds a
  25% surcharge to sessions starting from 17:00 through 20:59 and RM 0.50 per
  overstay minute. Confirm these assumptions against the campus tariff before
  using the output for billing.
- The source files contain no measured solar generation or interval meter
  readings. Hourly session energy is a grid-demand proxy, and the solar curve
  is modeled for illustration.

## Project files

- `data_pipeline.py`: cleaning, date matching, feature engineering, and export.
- `visualizations.py`: three-panel Matplotlib and Seaborn charts.
- `app.py` and `pages/`: interactive multi-page Streamlit dashboard.
- `dashboard_components.py`: shared filters, KPIs, alerts, and downloads.
- `cleaned_energy_sales_data.csv`: generated clean dataset.
