import streamlit as st
import json
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go

from agents.ta_global import ta_global
from llm_utils import call_llm

# -- Chart dictionary: label, explanation, and key as returned from ta_global()
CHARTS = [
    {
        "key": "sp500",
        "label": "S&P 500 (Last 6 Months)",
        "explanation": "S&P 500 is a broad-based US equity index representing leading companies from every major sector. Analysts use it to gauge overall market sentiment and economic health.",
    },
    {
        "key": "nasdaq",
        "label": "Nasdaq (Last 6 Months)",
        "explanation": "Nasdaq represents technology and growth stocks, providing insight into the performance of the tech sector and market risk appetite.",
    },
    {
        "key": "eurostoxx50",
        "label": "EuroStoxx 50 (Last 6 Months)",
        "explanation": "EuroStoxx 50 tracks leading blue-chip companies in the Eurozone and is often used as a proxy for European equity sentiment.",
    },
    {
        "key": "nikkei",
        "label": "Nikkei 225 (Last 6 Months)",
        "explanation": "Nikkei 225 is the main index of Japanese equities and is a key indicator of Asia-Pacific economic momentum.",
    },
    {
        "key": "hangseng",
        "label": "Hang Seng Index (Last 6 Months)",
        "explanation": "Hang Seng Index is the primary barometer of the Hong Kong stock market and reflects the health of China-related equities.",
    },
    {
        "key": "ftse100",
        "label": "FTSE 100 (Last 6 Months)",
        "explanation": "FTSE 100 tracks the largest companies on the London Stock Exchange and is a benchmark for the UK economy.",
    },
    {
        "key": "vix",
        "label": "VIX Volatility Index (Last 6 Months)",
        "explanation": "VIX measures US stock market volatility. Rising VIX indicates market fear or uncertainty, while low VIX reflects calm markets.",
    },
    {
        "key": "us10y",
        "label": "US 10Y Treasury Yield (Last 6 Months)",
        "explanation": "US 10-Year Treasury Yield is a global benchmark for risk-free rates and economic growth expectations.",
    },
    {
        "key": "us2y",
        "label": "US 2Y Yield (Last 6 Months)",
        "explanation": "US 2-Year Yield reflects near-term interest rate expectations and monetary policy outlook.",
    },
    {
        "key": "dxy",
        "label": "US Dollar Index (DXY) (Last 6 Months)",
        "explanation": "DXY tracks the value of the US dollar versus a basket of major world currencies. A rising DXY indicates USD strength.",
    },
    {
        "key": "usdsgd",
        "label": "USD/SGD FX Rate (Last 6 Months)",
        "explanation": "USD/SGD is the exchange rate between US Dollar and Singapore Dollar, relevant for Asian FX flows.",
    },
    {
        "key": "usdcnh",
        "label": "USD/CNH FX Rate (Last 6 Months)",
        "explanation": "USD/CNH is the US Dollar to Chinese offshore Yuan, reflecting China's capital flow and trade sentiment.",
    },
    {
        "key": "eur_usd",
        "label": "EUR/USD FX Rate (Last 6 Months)",
        "explanation": "EUR/USD is the world's most traded currency pair, key for global capital flows and central bank policy.",
    },
    {
        "key": "gold",
        "label": "Gold Futures (Last 6 Months)",
        "explanation": "Gold is a global safe haven and inflation hedge. Its price trends are watched by investors for risk sentiment.",
    },
    {
        "key": "oil_brent",
        "label": "Brent Crude Oil (Last 6 Months)",
        "explanation": "Brent oil is a benchmark for global crude prices, influencing inflation, trade, and geopolitical risk.",
    },
    {
        "key": "oil_wti",
        "label": "WTI Crude Oil (Last 6 Months)",
        "explanation": "WTI is the key benchmark for North American crude oil, closely tracked by energy analysts and traders.",
    },
    {
        "key": "copper",
        "label": "Copper Futures (Last 6 Months)",
        "explanation": "Copper prices are an indicator of global industrial demand and economic cycles.",
    },
]

def plot_chart(df, label, explanation):
    # -- Defensive: flatten multiindex if needed --
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ['_'.join([str(i) for i in col if i]) for col in df.columns.values]
    cols = [str(c).lower() for c in df.columns]
    # -- Find date, close, volume columns robustly --
    date_col = None
    close_col = None
    volume_col = None
    for c in df.columns:
        c_str = str(c).lower()
        if any(x in c_str for x in ["date", "datetime", "index"]):
            date_col = c
        if "close" in c_str and "adj" not in c_str:
            close_col = c
        if "vol" in c_str and "notional" not in c_str:
            volume_col = c
    # Fallbacks
    if date_col is None: date_col = df.columns[0]
    if close_col is None:
        for c in df.columns:
            if "close" in str(c).lower():
                close_col = c
                break
    if close_col is None:
        st.info(f"{label}: No close price column found.")
        return

    # Drop NaN
    df = df.dropna(subset=[date_col, close_col])
    if len(df) < 5:
        st.info(f"Not enough {label} data to plot.")
        return

    # Calculate SMA 20, SMA 50, and rolling volatility (stdev)
    df = df.copy()
    df["sma20"] = df[close_col].rolling(20).mean()
    df["sma50"] = df[close_col].rolling(50).mean()
    df["volatility20"] = df[close_col].rolling(20).std()
    # Prepare chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df[date_col], y=df[close_col], mode='lines', name=label,
        line=dict(color='royalblue', width=2)
    ))
    fig.add_trace(go.Scatter(
        x=df[date_col], y=df["sma20"], mode='lines', name='SMA 20',
        line=dict(color='red', dash='dot')
    ))
    fig.add_trace(go.Scatter(
        x=df[date_col], y=df["sma50"], mode='lines', name='SMA 50',
        line=dict(color='teal', dash='dash')
    ))
    # Volatility overlay (as line, 2nd y)
    fig.add_trace(go.Scatter(
        x=df[date_col], y=df["volatility20"], name="20d Volatility",
        mode="lines", line=dict(color="orange", width=1.3), yaxis="y2"
    ))
    # Volume as bars (if available)
    if volume_col:
        fig.add_trace(go.Bar(
            x=df[date_col], y=df[volume_col], name="Volume",
            marker_color='rgba(135,206,250,0.18)', yaxis="y3",
            opacity=0.6
        ))

    # Layout: show dual y-axis for volatility, optional for volume
    fig.update_layout(
        title=dict(text=f"{label}", x=0.5),
        xaxis_title="Date",
        yaxis=dict(title="Price"),
        yaxis2=dict(title="Volatility (20d)", overlaying="y", side="right", showgrid=False),
        yaxis3=dict(
            title="Volume",
            anchor="free", overlaying="y", side="right",
            position=1.00, showgrid=False, showticklabels=False, layer="below traces"
        ) if volume_col else {},
        legend=dict(orientation="h", x=0, y=1.18),
        height=320,
        margin=dict(t=40, b=40)
    )
    st.markdown(f"**{label}**")
    st.caption(explanation)
    st.plotly_chart(fig, use_container_width=True)

# -- PAGE SETUP --
st.set_page_config(page_title="AI Global Technical Macro Analyst", page_icon="🌍")
st.title("🌍 AI Global Macro Technical Analyst Demo")
st.markdown("""
This demo fetches global market data, computes technical metrics, and asks the LLM to summarize the global technical outlook in both a professional (analyst) and plain-English (executive) format.
""")

# --- Get latest global technical summary
with st.spinner("Loading global technical summary..."):
    try:
        summary = ta_global()
        st.success("Fetched and computed global technical metrics.")
    except Exception as e:
        st.error(f"Error in ta_global(): {e}")
        st.stop()

# --- LLM Summary section FIRST ---
st.subheader("LLM-Generated Summaries")
if st.button("Generate LLM Global Summaries", type="primary"):
    with st.spinner("Querying LLM..."):
        try:
            json_summary = json.dumps(summary, indent=2)
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

# --- CHARTS SECTION ---
st.subheader("Global Macro Charts")
for chart in CHARTS:
    df = summary.get(chart["key"])
    if isinstance(df, pd.DataFrame):
        plot_chart(df, chart["label"], chart["explanation"])
    else:
        st.info(f"{chart['label']}: No data available.")

# --- RAW DATA EXPANDER ---
st.subheader("Raw Global Technical Data")
with st.expander("Show raw summary dict", expanded=False):
    st.json(summary)

st.caption("If you do not see the summaries or charts, check the console logs for errors or ensure your OpenAI API key is correctly set.")






