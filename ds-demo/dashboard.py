import os
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# -----------------------------------------------------------------------------
# PAGE CONFIG — must be the first Streamlit call
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Credit Risk Intelligence | Internal Banking Tool",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# STYLING
# Dark sidebar, clean white main area, professional typography
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #0f1923;
    }
    [data-testid="stSidebar"] * {
        color: #c9d4e0 !important;
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #ffffff !important;
    }

    /* Main area */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        background-color: #ffffff;
    }

    /* Metric cards */
    [data-testid="metric-container"] {
        background-color: #f8f9fb;
        border: 1px solid #e4e8ef;
        border-radius: 8px;
        padding: 1rem;
    }

    /* Header strip */
    .header-strip {
        background-color: #0f1923;
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        margin-bottom: 1.5rem;
    }
    .header-strip h2 { color: white; margin: 0; font-size: 1.1rem; font-weight: 400; }
    .header-strip h1 { color: white; margin: 0; font-size: 1.8rem; font-weight: 700; }

    /* Compliance doc */
    .compliance-doc {
        font-family: 'Courier New', monospace;
        font-size: 0.72rem;
        line-height: 1.6;
        white-space: pre-wrap;
        color: #c9d4e0;
    }

    /* Divider */
    hr { border-color: #e4e8ef; }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# DATA LOADING
# -----------------------------------------------------------------------------
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")

@st.cache_data
def load_data():
    df     = pd.read_csv(os.path.join(OUTPUT_DIR, "processed_data.csv"), index_col=0, parse_dates=True)
    spikes = pd.read_csv(os.path.join(OUTPUT_DIR, "spikes.csv"), parse_dates=["date"])
    with open(os.path.join(OUTPUT_DIR, "compliance_documentation.txt")) as f:
        compliance = f.read()
    return df, spikes, compliance

try:
    df, spikes, compliance_text = load_data()
except FileNotFoundError:
    st.error(
        "Data files not found. Run `python3 ds-demo/analysis.py` first to generate the required outputs."
    )
    st.stop()

# -----------------------------------------------------------------------------
# SIDEBAR — Compliance Documentation
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🏦 Credit Risk Intelligence")
    st.markdown("**Internal Use Only** — Model Risk Management")
    st.markdown("---")
    st.markdown("#### Compliance Documentation")
    st.markdown(f'<div class="compliance-doc">{compliance_text}</div>', unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# MAIN HEADER
# -----------------------------------------------------------------------------
st.markdown("""
<div class="header-strip">
    <h2>Consumer Credit Risk Dashboard</h2>
    <h1>Delinquency Rate & Unemployment Analysis</h1>
</div>
""", unsafe_allow_html=True)

# Summary metrics
col1, col2, col3, col4 = st.columns(4)
latest_delinq = df["delinquency_rate"].iloc[-1]
peak_delinq   = df["delinquency_rate"].max()
latest_unemp  = df["unemployment_rate"].iloc[-1]
largest_spike = spikes["change"].max()

col1.metric("Current Delinquency Rate", f"{latest_delinq:.2f}%")
col2.metric("10-Year Peak Delinquency", f"{peak_delinq:.2f}%")
col3.metric("Current Unemployment Rate", f"{latest_unemp:.1f}%")
col4.metric("Largest Single-Quarter Spike", f"+{largest_spike:.2f} pp")

st.markdown("---")

# -----------------------------------------------------------------------------
# CHART 1 — Delinquency Rate with Spike Annotations
# -----------------------------------------------------------------------------
st.markdown("#### Credit Card Delinquency Rate — 10-Year Trend with Key Stress Events")

fig1 = go.Figure()

fig1.add_trace(go.Scatter(
    x=df.index,
    y=df["delinquency_rate"],
    mode="lines",
    name="Delinquency Rate",
    line=dict(color="#1a56db", width=2.5),
    fill="tozeroy",
    fillcolor="rgba(26, 86, 219, 0.08)",
))

# Spike markers and labels
colors = ["#e3342f", "#f6993f", "#ffed4a"]
for i, row in spikes.iterrows():
    spike_date = pd.Timestamp(row["date"])
    spike_val  = row["rate"]
    label      = spike_date.strftime("%b '%y")

    fig1.add_trace(go.Scatter(
        x=[spike_date],
        y=[spike_val],
        mode="markers+text",
        name=f"Spike {i+1}: {label}",
        marker=dict(size=12, color=colors[i], symbol="diamond", line=dict(width=1.5, color="white")),
        text=[f"  Spike {i+1}<br>  {label}<br>  {spike_val:.2f}%"],
        textposition="top right",
        textfont=dict(size=11, color=colors[i]),
    ))

fig1.update_layout(
    height=380,
    margin=dict(l=0, r=0, t=10, b=0),
    plot_bgcolor="white",
    paper_bgcolor="white",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    xaxis=dict(showgrid=True, gridcolor="#f0f0f0", title=""),
    yaxis=dict(showgrid=True, gridcolor="#f0f0f0", title="Delinquency Rate (%)", ticksuffix="%"),
    hovermode="x unified",
)

st.plotly_chart(fig1, use_container_width=True)

st.markdown("---")

# -----------------------------------------------------------------------------
# CHART 2 — Delinquency vs. Unemployment (dual axis)
# -----------------------------------------------------------------------------
st.markdown("#### Delinquency Rate vs. Unemployment Rate — Macroeconomic Correlation")

fig2 = make_subplots(specs=[[{"secondary_y": True}]])

fig2.add_trace(go.Scatter(
    x=df.index,
    y=df["delinquency_rate"],
    name="Delinquency Rate",
    line=dict(color="#1a56db", width=2.5),
    mode="lines",
), secondary_y=False)

fig2.add_trace(go.Scatter(
    x=df.index,
    y=df["unemployment_rate"],
    name="Unemployment Rate",
    line=dict(color="#e3342f", width=2, dash="dot"),
    mode="lines",
), secondary_y=True)

fig2.update_layout(
    height=380,
    margin=dict(l=0, r=0, t=10, b=0),
    plot_bgcolor="white",
    paper_bgcolor="white",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    xaxis=dict(showgrid=True, gridcolor="#f0f0f0", title=""),
    hovermode="x unified",
)
fig2.update_yaxes(
    title_text="Delinquency Rate (%)",
    ticksuffix="%",
    showgrid=True,
    gridcolor="#f0f0f0",
    secondary_y=False,
)
fig2.update_yaxes(
    title_text="Unemployment Rate (%)",
    ticksuffix="%",
    showgrid=False,
    secondary_y=True,
)

st.plotly_chart(fig2, use_container_width=True)

# Caption
st.caption(
    "Data source: Federal Reserve Bank of St. Louis (FRED). "
    "Series: DRCCLACBS (Delinquency Rate on Credit Card Loans) and UNRATE (Unemployment Rate). "
    "Both series resampled to quarterly frequency. Internal use only."
)
