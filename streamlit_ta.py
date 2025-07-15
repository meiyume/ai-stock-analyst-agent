import streamlit as st
import json
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
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

# --- LLM Summaries at the top
st.subheader("LLM-Generated Summaries")
json_summary = json.dumps(summary, indent=2)

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

st.caption("If you do not see the summaries, check the console logs for LLM errors or ensure your OpenAI API key is correctly set.")

# --- Raw Data Section
st.subheader("Raw Global Technical Data")
with st.expander("Show raw summary dict", expanded=False):
    st.json(summary)

# --- Chart section helper ---
def find_col(possibles, columns):
    for p in possibles:
        for c in columns:
            if p in str(c).lower():
                return c
    return None

def plot_chart(ticker, label, explanation):
    with st.container():
        st.markdown(f"#### {label}")
        st.caption(explanation)
        try:
            end = datetime.today()
            start = end - timedelta(days=180)
            df = yf.download(ticker, start=start, end=end, interval="1d", auto_adjust=True, progress=False)
            if df is None or len(df) < 10:
                st.info(f"Not enough {label} data to plot.")
                return

            # Flatten MultiIndex columns, if needed
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = ['_'.join([str(i) for i in col if i]) for col in df.columns.values]
            df = df.reset_index()

            date_col = find_col(['date', 'datetime', 'index'], df.columns) or df.columns[0]
            close_col = find_col(['close'], df.columns)
            volume_col = find_col(['volume'], df.columns)

            if not date_col or not close_col:
                st.info(f"{label} chart failed to load: columns found: {list(df.columns)}")
                return

            # Clean data
            df = df.dropna(subset=[date_col, close_col])
            if len(df) < 10:
                st.info(f"Not enough {label} data to plot.")
                return

            # Calculate SMA20, SMA50
            df["SMA20"] = df[close_col].rolling(window=20).mean()
            df["SMA50"] = df[close_col].rolling(window=50).mean()

            # Calculate rolling volatility (20d stdev of Close)
            df["Volatility20"] = df[close_col].rolling(window=20).std()

            fig = go.Figure()
            # Main price line
            fig.add_trace(go.Scatter(
                x=df[date_col], y=df[close_col],
                mode='lines', name=label
            ))
            # SMA20
            fig.add_trace(go.Scatter(
                x=df[date_col], y=df["SMA20"],
                mode='lines', name='SMA 20', line=dict(dash='dot')
            ))
            # SMA50
            fig.add_trace(go.Scatter(
                x=df[date_col], y=df["SMA50"],
                mode='lines', name='SMA 50', line=dict(dash='dash')
            ))
            # Volatility overlay
            if "Volatility20" in df.columns and not df["Volatility20"].isna().all():
                fig.add_trace(go.Scatter(
                    x=df[date_col], y=df["Volatility20"],
                    mode='lines', name="Volatility (20d std)", line=dict(color="orange", dash='dashdot'),
                    yaxis="y3"
                ))
            # Volume (secondary axis)
            if volume_col and volume_col in df.columns:
                fig.add_trace(go.Bar(
                    x=df[date_col], y=df[volume_col],
                    name="Volume", yaxis="y2",
                    marker_color="rgba(0,160,255,0.16)",
                    opacity=0.5
                ))

            # Layout for dual axis (and 3rd for volatility)
            fig.update_layout(
                title=label,
                xaxis_title="Date",
                yaxis=dict(title="Price", showgrid=True),
                yaxis2=dict(
                    title="Volume", overlaying='y', side='right', showgrid=False, rangemode='tozero'
                ),
                yaxis3=dict(
                    title="Volatility", overlaying='y', side='left', anchor="x", position=0.05, showgrid=False, visible=True
                ),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                template="plotly_white",
                height=350,
                bargap=0
            )

            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.info(f"{label} chart failed to load: {e}")

# --- Chart definitions and explanations ---
chart_list = [
    {
        "ticker": "^GSPC",
        "label": "S&P 500 (Last 6 Months)",
        "explanation": "The S&P 500 is a broad-based index representing large-cap US equities across economic sectors. Analysts study it to assess overall US market health and risk sentiment."
    },
    {
        "ticker": "^VIX",
        "label": "VIX (Volatility Index)",
        "explanation": "The VIX reflects expected US stock market volatility (fear/greed). A rising VIX signals heightened investor anxiety."
    },
    {
        "ticker": "^IXIC",
        "label": "Nasdaq Composite",
        "explanation": "Tracks over 3,000 technology and growth-oriented companies. Used to monitor tech sector momentum and risk appetite."
    },
    {
        "ticker": "^STOXX50E",
        "label": "EuroStoxx 50",
        "explanation": "Major European blue-chip index, often a proxy for Eurozone market health and capital flows."
    },
    {
        "ticker": "^N225",
        "label": "Nikkei 225",
        "explanation": "The benchmark for Japanese equities and an indicator of Asia-Pacific risk trends."
    },
    {
        "ticker": "^HSI",
        "label": "Hang Seng Index",
        "explanation": "The Hang Seng represents the Hong Kong equity market and is closely watched for signs of China/Asia sentiment shifts."
    },
    {
        "ticker": "^FTSE",
        "label": "FTSE 100",
        "explanation": "The FTSE 100 is the primary UK equity index, tracking the largest London-listed companies and reflecting European market trends."
    },
    {
        "ticker": "^TNX",
        "label": "US 10-Year Treasury Yield",
        "explanation": "The 10-year yield is a global benchmark for interest rates, influencing borrowing costs and risk assets worldwide."
    },
    {
        "ticker": "^IRX",
        "label": "US 2-Year Treasury Yield",
        "explanation": "Short-term US government bond yield. Rising 2-year yields can signal shifting Fed policy expectations."
    },
    {
        "ticker": "DX-Y.NYB",
        "label": "US Dollar Index (DXY)",
        "explanation": "DXY measures the US dollar's strength against a basket of major currencies. It affects global trade and capital flows."
    },
    {
        "ticker": "USDSGD=X",
        "label": "USD/SGD FX Rate",
        "explanation": "The USD/SGD exchange rate is closely monitored as an indicator of Singapore’s economic health and regional capital flows."
    },
    {
        "ticker": "JPY=X",
        "label": "USD/JPY FX Rate",
        "explanation": "Tracks the US dollar against the Japanese yen. Used to gauge risk sentiment and monetary policy trends in Asia."
    },
    {
        "ticker": "EURUSD=X",
        "label": "EUR/USD FX Rate",
        "explanation": "The EUR/USD rate is the world's most traded FX pair, serving as a barometer of global macro and policy divergence."
    },
    {
        "ticker": "USDCNH=X",
        "label": "USD/CNH FX Rate",
        "explanation": "Reflects the offshore yuan versus the US dollar. A gauge of global investor sentiment towards China."
    },
    {
        "ticker": "GC=F",
        "label": "Gold Futures",
        "explanation": "Gold is a traditional safe-haven asset. Its price movement signals inflation and global risk sentiment."
    },
    {
        "ticker": "BZ=F",
        "label": "Brent Crude Oil",
        "explanation": "Brent is the world’s key oil price benchmark. It affects inflation, trade balances, and energy markets."
    },
    {
        "ticker": "CL=F",
        "label": "WTI Crude Oil",
        "explanation": "WTI is the US oil benchmark, important for tracking energy prices and economic activity."
    },
    {
        "ticker": "HG=F",
        "label": "Copper Futures",
        "explanation": "Copper is an industrial bellwether, used to assess the strength of global manufacturing and economic growth."
    },
]

# --- Plot all charts ---
st.subheader("Global Market Charts")
for chart in chart_list:
    plot_chart(chart["ticker"], chart["label"], chart["explanation"])







