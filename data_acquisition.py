# =============================================================================
# FRED API Data Acquisition Script
# =============================================================================
# This script connects to the Federal Reserve Economic Data (FRED) API and
# downloads key financial and economic indicators used in our fintech demo.
# Each data series is saved as its own CSV file for later analysis.
# =============================================================================

import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

# -----------------------------------------------------------------------------
# CONFIGURATION
# Load environment variables from the .env file (where we store our API key
# securely, so it never gets hardcoded into the script).
# -----------------------------------------------------------------------------
load_dotenv()
API_KEY = os.getenv("FRED_API_KEY")

if not API_KEY:
    raise ValueError(
        "FRED_API_KEY not found. Please add it to your .env file. "
        "See .env.template for the expected format."
    )

# Base URL for all FRED API requests
FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

# Output folder where CSV files will be saved
OUTPUT_DIR = "data/raw"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# -----------------------------------------------------------------------------
# DATA SERIES TO PULL
# Each entry maps a FRED series ID to a human-readable name.
#
# DRCCLACBS    — Delinquency Rate on Credit Card Loans (banks)
# TERMCBCCALLNS — Interest Rate on Credit Card Plans (all accounts)
# TOTALSL      — Total Consumer Credit Outstanding
# UNRATE       — U.S. Unemployment Rate
# FEDFUNDS     — Federal Funds Effective Rate (benchmark interest rate)
# DPSACBW027SBOG — Deposits at Commercial Banks
# -----------------------------------------------------------------------------
SERIES = {
    "DRCCLACBS":       "Credit Card Delinquency Rate",
    "TERMCBCCALLNS":   "Credit Card Interest Rate",
    "TOTALSL":         "Total Consumer Credit",
    "UNRATE":          "Unemployment Rate",
    "FEDFUNDS":        "Federal Funds Rate",
    "DPSACBW027SBOG":  "Deposits at Commercial Banks",
}

# -----------------------------------------------------------------------------
# DATE RANGE
# Pull the last 10 years of data from today's date.
# -----------------------------------------------------------------------------
END_DATE   = datetime.today().strftime("%Y-%m-%d")
START_DATE = (datetime.today() - timedelta(days=365 * 10)).strftime("%Y-%m-%d")

print("=" * 60)
print("  FRED API Data Acquisition")
print(f"  Date range: {START_DATE}  →  {END_DATE}")
print("=" * 60)


# -----------------------------------------------------------------------------
# FETCH FUNCTION
# Makes a single API request to FRED for one data series and returns a
# cleaned pandas DataFrame with columns: date, value.
# -----------------------------------------------------------------------------
def fetch_series(series_id: str) -> pd.DataFrame:
    params = {
        "series_id":        series_id,
        "api_key":          API_KEY,
        "file_type":        "json",
        "observation_start": START_DATE,
        "observation_end":   END_DATE,
    }
    response = requests.get(FRED_BASE_URL, params=params, timeout=30)
    response.raise_for_status()

    observations = response.json().get("observations", [])
    if not observations:
        raise ValueError(f"No data returned for series '{series_id}'.")

    df = pd.DataFrame(observations)[["date", "value"]]

    # FRED uses "." to represent missing values — replace with NaN
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["date"]  = pd.to_datetime(df["date"])

    return df


# -----------------------------------------------------------------------------
# MAIN LOOP
# Iterate over each series, fetch the data, save to CSV, and print a summary.
# -----------------------------------------------------------------------------
summary_rows = []

for series_id, series_name in SERIES.items():
    print(f"\nFetching: {series_name} ({series_id}) ...")

    try:
        df = fetch_series(series_id)

        # Save to CSV — one file per series
        filename  = f"{series_id}.csv"
        filepath  = os.path.join(OUTPUT_DIR, filename)
        df.to_csv(filepath, index=False)

        missing = df["value"].isna().sum()
        summary_rows.append({
            "Series ID":    series_id,
            "Series Name":  series_name,
            "Start Date":   df["date"].min().strftime("%Y-%m-%d"),
            "End Date":     df["date"].max().strftime("%Y-%m-%d"),
            "Row Count":    len(df),
            "Missing Values": missing,
            "Saved To":     filepath,
        })
        print(f"  Saved {len(df)} rows → {filepath}")

    except Exception as e:
        print(f"  ERROR fetching {series_id}: {e}")
        summary_rows.append({
            "Series ID":    series_id,
            "Series Name":  series_name,
            "Start Date":   "ERROR",
            "End Date":     "ERROR",
            "Row Count":    0,
            "Missing Values": "N/A",
            "Saved To":     "N/A",
        })

# -----------------------------------------------------------------------------
# SUMMARY TABLE
# Print a formatted overview of everything that was downloaded.
# -----------------------------------------------------------------------------
print("\n")
print("=" * 60)
print("  Download Summary")
print("=" * 60)

summary_df = pd.DataFrame(summary_rows)
print(summary_df.to_string(index=False))
print("\nAll done! CSV files are in the", OUTPUT_DIR, "folder.")
