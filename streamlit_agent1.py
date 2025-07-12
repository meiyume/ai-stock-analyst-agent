# streamlit_agent1.py

import streamlit as st
import plotly.graph_objects as go
from agents.agent1_core import run_full_technical_analysis

st.set_page_config(page_title="Agent 1: AI Technical Analyst", layout="wide")

st.title("📈 Agent 1: AI Technical Analyst")
st.markdown("""
Agent 1 analyzes a stock and its broader technical context (stock, sector, index, commodity, global).
This demo currently includes:
- ✅ Core stock-level technical analysis (Agent 1.0)
- ⏳ Sector, index, and commodity layers coming soon
""")

# === User Input ===
ticker = st.text_input("Enter SGX Stock Ticker (e.g. U11.SI)", value="U11.SI")

horizon = st.selectbox(
    "Select Outlook Horizon",
    options=[
        "Next Day (1D)",
        "3 Days",
        "7 Days",
        "30 Days (1M)"
    ],
    index=2
)

# Horizon normalization
horizon_map = {
    "Next Day (1D)": "1 Day",
    "3 Days": "3 Days",
    "7 Days": "7 Days",
    "30 Days (1M)": "30 Days"
}
selected_horizon = horizon_map[horizon]

if st.button("🔍 Run Technical Analysis"):
    results, df = run_full_technical_analysis(ticker, selected_horizon)
    
    st.subheader("📊 Candlestick Chart with SMA & Bollinger Bands")

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df["Date"],
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        name="Price"
    ))
    fig.add_trace(go.Scatter(x=df["Date"], y=df["SMA_5"], mode="lines", name="SMA 5"))
    fig.add_trace(go.Scatter(x=df["Date"], y=df["SMA_10"], mode="lines", name="SMA 10"))
    fig.add_trace(go.Scatter(x=df["Date"], y=df["BB_Upper"], mode="lines", name="Upper BB", line=dict(dash='dot')))
    fig.add_trace(go.Scatter(x=df["Date"], y=df["BB_Lower"], mode="lines", name="Lower BB", line=dict(dash='dot')))
    fig.update_layout(height=500, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📉 RSI")
    rsi_fig = go.Figure()
    rsi_fig.add_trace(go.Scatter(x=df["Date"], y=df["RSI"], name="RSI"))
    rsi_fig.update_layout(yaxis_range=[0, 100], height=250)
    st.plotly_chart(rsi_fig, use_container_width=True)

    st.subheader("📈 MACD")
    macd_fig = go.Figure()
    macd_fig.add_trace(go.Scatter(x=df["Date"], y=df["MACD"], name="MACD"))
    macd_fig.add_trace(go.Scatter(x=df["Date"], y=df["MACD_Signal"], name="Signal"))
    st.plotly_chart(macd_fig, use_container_width=True)

    st.subheader("📊 Volume")
    vol_fig = go.Figure()
    vol_fig.add_trace(go.Bar(x=df["Date"], y=df["Volume"], name="Volume"))
    st.plotly_chart(vol_fig, use_container_width=True)

    # === Layered Technical Summaries ===
    st.subheader("🧠 Technical Summary Layers")
    st.markdown("**Stock-Level Analysis (Agent 1.0):**")
    st.json(results["stock"])

    st.markdown("**Sector Analysis (Agent 1.1):**")
    st.info(results["sector"]["summary"])

    st.markdown("**Market Index (Agent 1.2):**")
    st.info(results["market"]["summary"])

    st.markdown("**Commodities (Agent 1.3):**")
    st.info(results["commodities"]["summary"])

    st.markdown("**Global Indices (Agent 1.4):**")
    st.info(results["globals"]["summary"])

    # === Final Outlook ===
    st.markdown("### 📌 Final Technical Outlook Summary")
    st.success(results["final_summary"])
