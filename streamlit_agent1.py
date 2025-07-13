
# streamlit_agent1.py

import streamlit as st
import plotly.graph_objects as go
from agents.agent1_core import run_full_technical_analysis

# === Page Config ===
st.set_page_config(page_title="Agent 1: AI Technical Analyst", layout="wide")

st.title("📊 Agent 1: AI Technical Analyst")
st.markdown("""
Welcome to **Agent 1**, your AI-powered technical analyst.

This agent performs a layered technical analysis using:
- 📈 Stock indicators (SMA, MACD, RSI, Bollinger Bands, Stochastic, CMF, OBV, ADX, ATR)
- 🏭 Peer sector comparison
- 📊 Market index trends
- 🛢️ Commodity signals (gold, oil)
- 🌍 Global indices (Dow, Nikkei, HSI)

--- 
""")

# === User Input ===
ticker = st.text_input("🎯 Enter SGX Stock Ticker (e.g. U11.SI)", value="U11.SI")

horizon = st.selectbox("📅 Select Outlook Horizon", [
    "Next Day (1D)", "3 Days", "7 Days", "30 Days (1M)"
], index=2)

horizon_map = {
    "Next Day (1D)": "1 Day",
    "3 Days": "3 Days",
    "7 Days": "7 Days",
    "30 Days (1M)": "30 Days"
}
selected_horizon = horizon_map[horizon]

# === Run Analysis ===
if st.button("🔍 Run Technical Analysis"):
    with st.spinner("Analyzing..."):
        results, df = run_full_technical_analysis(ticker, selected_horizon)

        if "Date" not in df.columns:
            df = df.reset_index()

        # === Candlestick + SMA + Bollinger Bands ===
        st.subheader("🕯️ Candlestick Chart with SMA & Bollinger Bands")
        st.markdown("""
Shows price movement (candles), trends (SMA), and volatility (Bollinger Bands).

- **Candlestick chart**: Each candle represents a day of trading. A green candle means the stock closed higher than it opened (bullish), while a red candle means it closed lower (bearish). 
- **SMA (Simple Moving Average)**: SMA5 and SMA10 show short-term trend directions. Traders watch for crossovers (e.g., when SMA5 rises above SMA10) as trend signals.
- **Bollinger Bands**: These lines represent 2 standard deviations from the SMA10. If price hits or exceeds the upper band, it may suggest the stock is overbought. If it touches or dips below the lower band, it might be oversold.
        """)

        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df["Date"], open=df["Open"], high=df["High"],
            low=df["Low"], close=df["Close"], name="Candles"
        ))
        fig.add_trace(go.Scatter(x=df["Date"], y=df["SMA5"], mode="lines", name="SMA5"))
        fig.add_trace(go.Scatter(x=df["Date"], y=df["SMA10"], mode="lines", name="SMA10"))
        fig.add_trace(go.Scatter(x=df["Date"], y=df["Upper"], mode="lines", name="Upper BB", line=dict(dash='dot')))
        fig.add_trace(go.Scatter(x=df["Date"], y=df["Lower"], mode="lines", name="Lower BB", line=dict(dash='dot')))
        fig.update_layout(height=500, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # === Pattern Detection ===
        patterns = results.get("stock", {}).get("patterns", [])
        st.subheader("📌 Detected Candlestick Patterns")
        if patterns:
            st.markdown(
                ", ".join([f"✅ **{p}**" for p in patterns]) + "\n\n"
                + "These patterns were detected in the last 3 candles."
            )
        else:
            st.info("No recognizable candlestick patterns detected in the last 3 candles.")

        # === Anomaly Alerts ===
        st.subheader("🚨 Anomaly Alerts (Experimental)")
        anomalies = []
        stock_summary = results.get("stock", {})
        if stock_summary.get("rsi_spike"):
            anomalies.append("⚠️ **RSI Spike** detected — large momentum shift.")
        if stock_summary.get("price_gap"):
            anomalies.append("⚠️ **Price Gap** between yesterday's close and today's open.")
        if stock_summary.get("macd_spike"):
            anomalies.append("⚠️ **MACD Crossover Spike** — potential trend reversal.")
        if anomalies:
            for alert in anomalies:
                st.warning(alert)
        else:
            st.info("No anomalies detected today. 📈")
