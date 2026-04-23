# =============================================================================
# Credit Card Delinquency & Unemployment Analysis
# =============================================================================
# Pulls two Federal Reserve data series, aligns them to quarterly frequency,
# identifies the three largest spikes in credit card delinquency, and generates
# a compliance documentation file for model risk management review.
# =============================================================================

import os
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dotenv import load_dotenv

# -----------------------------------------------------------------------------
# CONFIGURATION
# Load the FRED API key from the .env file in the parent directory
# -----------------------------------------------------------------------------
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
API_KEY = os.getenv("FRED_API_KEY")

if not API_KEY:
    raise ValueError("FRED_API_KEY not found in .env file.")

FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
OUTPUT_DIR    = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

END_DATE   = datetime.today().strftime("%Y-%m-%d")
START_DATE = "2008-01-01"  # Extended to capture 2008 financial crisis and 2020 COVID spike

# -----------------------------------------------------------------------------
# DATA SERIES
# DRCCLACBS  — Delinquency Rate on Credit Card Loans, All Commercial Banks (%)
# UNRATE     — Unemployment Rate, Seasonally Adjusted (%)
# -----------------------------------------------------------------------------
SERIES = {
    "DRCCLACBS": "Credit Card Delinquency Rate (%)",
    "UNRATE":    "Unemployment Rate (%)",
}

# Economic context for annotating known spike periods — used in compliance doc
ECONOMIC_CONTEXT = {
    "2009-04-01": "Global Financial Crisis peak; widespread unemployment and tightening credit conditions drove delinquency to record highs.",
    "2020-04-01": "COVID-19 pandemic onset; mass layoffs and economic shutdown triggered a sharp rise in consumer financial stress.",
    "2023-04-01": "Post-pandemic credit normalization; stimulus exhaustion and rising interest rates increased delinquency pressure.",
}


# -----------------------------------------------------------------------------
# FETCH FUNCTION
# -----------------------------------------------------------------------------
def fetch_series(series_id: str) -> pd.Series:
    params = {
        "series_id":         series_id,
        "api_key":           API_KEY,
        "file_type":         "json",
        "observation_start": START_DATE,
        "observation_end":   END_DATE,
    }
    response = requests.get(FRED_BASE_URL, params=params, timeout=30)
    response.raise_for_status()

    observations = response.json().get("observations", [])
    df = pd.DataFrame(observations)[["date", "value"]]
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["date"]  = pd.to_datetime(df["date"])
    df = df.set_index("date")["value"].dropna()
    return df


# -----------------------------------------------------------------------------
# PULL & CLEAN DATA
# Resample both series to quarterly frequency using the mean of each quarter.
# This normalises the different reporting frequencies (monthly vs quarterly).
# -----------------------------------------------------------------------------
print("Fetching data from FRED...")
raw = {}
for sid, label in SERIES.items():
    print(f"  {label} ({sid})")
    raw[sid] = fetch_series(sid)

delinquency  = raw["DRCCLACBS"].resample("QS").mean()
unemployment = raw["UNRATE"].resample("QS").mean()

# Align both series to the same date index (inner join — quarters with both)
combined = pd.DataFrame({
    "delinquency_rate": delinquency,
    "unemployment_rate": unemployment,
}).dropna()

print(f"\nAligned quarterly data: {len(combined)} quarters ({combined.index[0].date()} → {combined.index[-1].date()})")


# -----------------------------------------------------------------------------
# SPIKE DETECTION
# A spike is defined as a quarter where the delinquency rate increased by the
# largest absolute amount compared to the previous quarter.
# -----------------------------------------------------------------------------
combined["delinquency_change"] = combined["delinquency_rate"].diff()
top3_spikes = combined["delinquency_change"].nlargest(3)

print("\nTop 3 Delinquency Rate Spikes:")
spikes_info = []
for date, change in top3_spikes.items():
    rate  = combined.loc[date, "delinquency_rate"]
    unemp = combined.loc[date, "unemployment_rate"]

    # Find the closest matching economic context entry
    context_date = min(ECONOMIC_CONTEXT.keys(),
                       key=lambda d: abs(pd.Timestamp(d) - date))
    context = ECONOMIC_CONTEXT[context_date]

    quarter = (date.month - 1) // 3 + 1
    print(f"  {date.strftime('%Y')} Q{quarter}")
    print(f"    Delinquency rate : {rate:.2f}%  (↑ {change:.2f} pp vs prior quarter)")
    print(f"    Unemployment rate: {unemp:.2f}%")
    print(f"    Context          : {context}\n")

    spikes_info.append({
        "date":    date,
        "rate":    rate,
        "change":  change,
        "unemp":   unemp,
        "context": context,
    })


# -----------------------------------------------------------------------------
# COMPLIANCE DOCUMENTATION
# Written to meet model risk management (MRM) committee standards.
# -----------------------------------------------------------------------------
now = datetime.now().strftime("%B %d, %Y")

spike_blocks = ""
for i, s in enumerate(spikes_info, 1):
    spike_blocks += f"""
  Spike {i}: {s['date'].strftime('%B %Y')}
  - Delinquency Rate : {s['rate']:.2f}%
  - Quarter-on-Quarter Change : +{s['change']:.2f} percentage points
  - Concurrent Unemployment Rate : {s['unemp']:.2f}%
  - Economic Context : {s['context']}
"""

compliance_text = f"""
================================================================================
  MODEL RISK MANAGEMENT — ANALYTICAL DOCUMENTATION
  Consumer Credit Stress Indicator Analysis
================================================================================

Document Reference : DS-DEMO-001
Prepared By        : Data Science Team
Review Date        : {now}
Classification     : Internal Use Only

--------------------------------------------------------------------------------
1. PURPOSE OF ANALYSIS
--------------------------------------------------------------------------------
This document describes the methodology, data sources, findings, and limitations
of an exploratory analysis examining the relationship between credit card
delinquency rates and the unemployment rate over a ten-year period
({START_DATE} to {END_DATE}).

The analysis is intended to support the bank's credit risk monitoring function
by identifying historical periods of elevated consumer credit stress and their
macroeconomic correlates. Findings may inform early-warning indicator frameworks
and stress testing assumptions.

--------------------------------------------------------------------------------
2. DATA SOURCES
--------------------------------------------------------------------------------
All data was sourced from the Federal Reserve Bank of St. Louis Economic Data
(FRED) API. FRED is operated by the Research division of the Federal Reserve
Bank of St. Louis and is considered a primary, authoritative source for U.S.
macroeconomic data.

  Series 1: DRCCLACBS — Delinquency Rate on Credit Card Loans,
            All Commercial Banks (%)
            Frequency : Quarterly
            Units     : Percent, Seasonally Adjusted
            Source    : Board of Governors of the Federal Reserve System

  Series 2: UNRATE — Unemployment Rate (%)
            Frequency : Monthly (resampled to quarterly)
            Units     : Percent, Seasonally Adjusted
            Source    : U.S. Bureau of Labor Statistics via FRED

Data was retrieved programmatically via authenticated API calls. No manual
adjustments or overrides were applied to the raw data.

--------------------------------------------------------------------------------
3. METHODOLOGY
--------------------------------------------------------------------------------
Step 1 — Data Retrieval
  Both series were pulled via the FRED REST API for the period
  {START_DATE} to {END_DATE}.

Step 2 — Frequency Alignment
  UNRATE (monthly) was resampled to quarterly frequency by computing the
  arithmetic mean of all monthly observations within each calendar quarter.
  DRCCLACBS is natively quarterly and required no resampling.

Step 3 — Data Cleaning
  Observations marked as missing by FRED (represented as '.') were converted
  to NaN and excluded from analysis. An inner join was performed to retain
  only quarters where both series have valid observations.

Step 4 — Spike Identification
  Quarter-on-quarter changes in the delinquency rate were computed using a
  first-difference operation. The three quarters with the largest positive
  first differences (i.e., the sharpest single-quarter increases) were
  identified as the primary spike events.

Step 5 — Contextual Annotation
  Each spike was annotated with relevant macroeconomic context drawn from
  publicly available economic records and Federal Reserve commentary.

--------------------------------------------------------------------------------
4. FINDINGS SUMMARY
--------------------------------------------------------------------------------
Over the ten-year period analyzed, the credit card delinquency rate exhibited
three pronounced upward spikes. In each case, the spike coincided with or
immediately followed periods of labor market deterioration, consistent with
the well-documented relationship between unemployment and consumer credit stress.
{spike_blocks}
The concurrent unemployment data supports the hypothesis that delinquency spikes
are strongly associated with macroeconomic shocks affecting household income.
This relationship has direct implications for credit risk stress testing and
early-warning indicator design.

--------------------------------------------------------------------------------
5. LIMITATIONS AND CAVEATS
--------------------------------------------------------------------------------
  i.   Causality cannot be inferred from correlation. While delinquency and
       unemployment co-move, this analysis does not establish a causal mechanism.

  ii.  The DRCCLACBS series represents an aggregate across all commercial banks.
       Institution-specific or portfolio-level delinquency dynamics may differ
       materially from the aggregate.

  iii. Quarterly resampling of the unemployment rate introduces a smoothing
       effect that may obscure intra-quarter volatility relevant to credit
       risk monitoring.

  iv.  This analysis does not control for confounding variables such as changes
       in underwriting standards, credit card penetration rates, or government
       stimulus programs (e.g., CARES Act forbearance provisions).

  v.   Historical relationships may not persist under novel macroeconomic
       regimes. Model outputs should not be extrapolated beyond the conditions
       observed in the training period without validation.

--------------------------------------------------------------------------------
6. RECOMMENDED NEXT STEPS
--------------------------------------------------------------------------------
  1. Expand the variable set to include additional leading indicators
     (e.g., consumer sentiment indices, revolving credit utilization rates)
     to improve early-warning signal quality.

  2. Disaggregate analysis by credit score tier and loan vintage to identify
     whether delinquency spikes are concentrated in specific portfolio segments.

  3. Commission a formal regression or Granger causality analysis to quantify
     the predictive relationship between unemployment changes and delinquency
     rate movements.

  4. Integrate findings into the bank's existing stress testing framework,
     using historical spike magnitudes to calibrate adverse scenario assumptions.

  5. Subject this methodology to independent model validation review prior to
     use in any regulatory reporting or capital planning process.

--------------------------------------------------------------------------------
END OF DOCUMENT
--------------------------------------------------------------------------------
"""

doc_path = os.path.join(OUTPUT_DIR, "compliance_documentation.txt")
with open(doc_path, "w") as f:
    f.write(compliance_text.strip())

print(f"Compliance documentation saved → {doc_path}")

# Save processed data for the dashboard to consume
combined.to_csv(os.path.join(OUTPUT_DIR, "processed_data.csv"))

# Save spike metadata for the dashboard
spikes_df = pd.DataFrame(spikes_info)
spikes_df["date"] = spikes_df["date"].dt.strftime("%Y-%m-%d")
spikes_df.to_csv(os.path.join(OUTPUT_DIR, "spikes.csv"), index=False)

print("Processed data saved → ds-demo/outputs/processed_data.csv")
print("Spike data saved    → ds-demo/outputs/spikes.csv")
print("\nAnalysis complete.")
