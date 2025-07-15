import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from agents.ta_global import ta_global
from llm_utils import call_llm

st.set_page_config(page_title="AI Global Technical Macro Analyst", page_icon="🌍")

st.title("🌍 AI Global Macro Technical Analyst Demo")
st.markdown(
    """
    This demo fetches global market data, computes technical metrics, and asks the LLM to summarize the global technical outlook
    in both a professional (analyst) and plain-English (executive) format.
    """
)

# --- Get latest global technical summary
with st.spinner("Loading global technical summary..."):
    try:
        summary = ta_global()
        st.success("Fetched and computed global technical metrics.")
    except Exception as e:
        st.error(f"Error in ta_global(): {e}")
        st.stop()

# --- Prepare prompt for LLM
import json
json_summary = json.dumps(summary, indent=2)

# --- LLM Summaries at the top ---
st.subheader("LLM-Generated Summaries")
if st.button("Generate LLM Global Summaries", type="primary"):
    with st.spinner("Querying LLM..."):
        try:
            llm_output = call_llm("global", json_summary)
            if "Technical Summary" in llm_output and "Plain-English Summary" in llm_output:
                tech = llm_output.split("Plain-English Summary")[0].replace("Technical Summary", "").strip()
                plain = llm_output.split("Plain-English Summary")[1].strip()
                st.markdown("**Technical Summary**")
                st.info(tech)
                st.markdown("**Plain-English Summary**")
                st.success(plain)
            else:
                st.warning("LLM output did not match expected template. Full output below:")
                st.code(llm_output)
        except Exception as e:
            st.error(f"LLM error: {e}")

st.subheader("Raw Global Technical Data")
with st.expander("Show raw summary dict", expanded=False):
    st.json(summary)

# -----------------------------
# Chart definitions
# -----------------------------
charts = [
    {
        "ticker": "^GSPC",
        "label": "S&P 500 (Last 6 Months)",
        "explanation": "The S&P 500 is a broad-based index of large US companies across all sectors, often used as a barometer for global equity market risk sentiment."
    },
    {
        "ticker": "^IXIC",
        "label": "Nasdaq (Last 6 Months)",
        "explanation": "The Nasdaq tracks technology and growth stocks, giving insight into tech-sector leadership and risk-on appetite."
    },
    {
        "ticker": "^STOXX50E",
        "label": "EuroStoxx 50 (Last 6 Months)",
        "explanation": "EuroStoxx 50 covers leading blue-chip stocks in the Eurozone, a proxy for European equity sentiment."
    },
    {
        "ticker": "^N225",
        "label": "Nikkei 225 (Last 6 Months)",
        "explanation": "The Nikkei 225 tracks top companies in Japan, often moving in tandem with Asian and global growth sentiment."
    },
    {
        "ticker": "^HSI",
        "label": "Hang Seng Index (Last 6 Months)",
        "explanation": "The Hang Seng reflects Hong Kong/China's equities and is watched for China macro and risk trends."
    },
    {
        "ticker": "^FTSE",
        "label": "FTSE 100 (Last 6 Months)",
        "explanation": "FTSE 100 tracks top UK companies, reflecting both local and global trends due to heavy international exposure."
    },
    {
        "ticker": "^VIX",
        "label": "VIX Volatility Index (Last 6 Months)",
        "explanation": "VIX is the 'fear gauge'—a forward-looking measure of US equity volatility derived from options prices."
    },
    {
        "ticker": "^TNX",
        "label": "US 10Y Treasury Yield (Last 6 Months)",
        "explanation": "The 10-year Treasury yield is a benchmark for global interest rates and risk-free yield expectations."
    },
    {
        "ticker": "DX-Y.NYB",
        "label": "US Dollar Index (DXY) (Last 6 Months)",
        "explanation": "DXY measures the USD versus major currencies, moving with risk-off or risk-on and Fed expectations."
    },
    {
        "ticker": "USDSGD=X",
        "label": "USD/SGD FX Rate (Last 6 Months)",
        "explanation": "USD/SGD reflects the strength of the US dollar versus Singapore dollar, important for trade and capital flows in Asia."
    },
    {
        "ticker": "USDCNH=X",
        "label": "USD/CNH FX Rate (Last 6 Months)",
        "explanation": "USD/CNH tracks the US dollar against offshore Chinese yuan, watched for China policy and capital movement clues."
    },
    {
        "ticker": "GC=F",
        "label": "Gold Futures (Last 6 Months)",
        "explanation": "Gold is a classic safe-haven asset, responding to inflation, real yields, and geopolitical risk."
    },
    {
        "ticker": "BZ=F",
        "label": "Brent Crude Oil (Last 6 Months)",
        "explanation": "Brent is the global oil price benchmark, impacted by supply/demand, war, and macro cycles."
    },
]

def plot_chart(ticker, label, explanation):
    import plotly.subplots as sp

    end = datetime.today()
    start = end - timedelta(days=180)
    df = yf.download(ticker, start=start, end=end, interval="1d", auto_adjust=True, progress=False)

    if df is None or len(df) < 5:
        st.info(f"Not enough data to plot: {ticker}")
        return

    df = df.reset_index()
    # ---- Identify columns
    date_col = None
    close_col = None
    volume_col = None
    for col in df.columns:
        cl = col.lower() if isinstance(col, str) else ""
        if cl in ["date", "datetime", "index"]:
            date_col = col
        if "close" in cl:
            close_col = col
        if "vol" in cl:
            volume_col = col

    if date_col is None:
        date_col = df.columns[0]
    if close_col is None:
        st.info(f"{label}: No close price column found.")
        return

    # Drop rows with NaN date or close
    df = df.dropna(subset=[date_col, close_col])

    # Compute SMAs
    df["SMA_20"] = df[close_col].rolling(20, min_periods=1).mean()
    df["SMA_50"] = df[close_col].rolling(50, min_periods=1).mean()
    # Compute volatility (rolling 30d stdev, annualized for equities)
    df["Volatility"] = df[close_col].pct_change().rolling(30, min_periods=1).std() * np.sqrt(252)
    # Compute RSI (14)
    delta = df[close_col].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14, min_periods=1).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14, min_periods=1).mean()
    rs = gain / (loss + 1e-9)
    df["RSI_14"] = 100 - (100 / (1 + rs))

    # Subplots: main chart, volume, and RSI
    fig = sp.make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.65, 0.15, 0.20],
        subplot_titles=(label, "Volume", "RSI (14)")
    )

    # Price and SMAs
    fig.add_trace(go.Scatter(
        x=df[date_col],
        y=df[close_col],
        mode='lines',
        name='Price',
        line=dict(color='#222', width=2)
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=df[date_col],
        y=df["SMA_20"],
        mode='lines',
        name='SMA 20',
        line=dict(color='royalblue', width=1, dash="dot")
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=df[date_col],
        y=df["SMA_50"],
        mode='lines',
        name='SMA 50',
        line=dict(color='orange', width=1, dash="dash")
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=df[date_col],
        y=df["Volatility"],
        mode='lines',
        name='Volatility (30d stdev)',
        yaxis="y2",
        line=dict(color='firebrick', width=1, dash="dash")
    ), row=1, col=1)

    # Volume (if available)
    if volume_col is not None:
        fig.add_trace(go.Bar(
            x=df[date_col],
            y=df[volume_col],
            name='Volume',
            marker=dict(color='lightblue', opacity=0.45),
        ), row=2, col=1)

    # RSI (sub-panel)
    fig.add_trace(go.Scatter(
        x=df[date_col],
        y=df["RSI_14"],
        mode='lines',
        name='RSI (14)',
        line=dict(color='green', width=1)
    ), row=3, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="blue", row=3, col=1)

    fig.update_layout(
        height=700,
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Volatility", overlaying="y", side="right", row=1, col=1, showgrid=False)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    fig.update_yaxes(title_text="RSI", row=3, col=1, range=[0, 100])

    # Display
    st.markdown(f"#### {label}")
    st.caption(explanation)
    st.plotly_chart(fig, use_container_width=True)

st.header("Global Markets Technical Charts")
for chart in charts:
    plot_chart(chart["ticker"], chart["label"], chart["explanation"])

st.caption("If any chart fails to load, check the console logs or data source. Some instruments may have sparse or missing data.")





