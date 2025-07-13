
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
- Stock indicators (SMA, MACD, RSI, Bollinger Bands, Stochastic, CMF, OBV)
- Peer sector comparison
- Market index trends
- Commodity signals (e.g. gold, oil)
- Global indices (Dow, Nikkei, HSI)

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

        # Fix missing 'Date' column if index is datetime
        if "Date" not in df.columns:
            df = df.reset_index()

        # === Candlestick + SMA + Bollinger Bands ===
        st.subheader("🕯️ Candlestick Chart with SMA & Bollinger Bands")
        st.markdown("""
This chart combines price action (candlesticks), trend analysis (SMA), and volatility bands (Bollinger Bands).
- A green candle means the stock closed higher than it opened (bullish), red means it closed lower (bearish).
- SMA5 and SMA10 show short-term and medium-term trends respectively.
- Bollinger Bands expand and contract with volatility. If the price touches or exceeds the upper band, it may suggest overbought conditions. If it dips below the lower band, it may suggest oversold conditions.
""")
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df["Date"],
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="Price"
        ))
        fig.add_trace(go.Scatter(x=df["Date"], y=df["SMA5"], mode="lines", name="SMA5"))
        fig.add_trace(go.Scatter(x=df["Date"], y=df["SMA10"], mode="lines", name="SMA10"))
        fig.add_trace(go.Scatter(x=df["Date"], y=df["Upper"], mode="lines", name="Upper BB", line=dict(dash='dot')))
        fig.add_trace(go.Scatter(x=df["Date"], y=df["Lower"], mode="lines", name="Lower BB", line=dict(dash='dot')))
        fig.update_layout(height=500, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # === RSI ===
        st.subheader("📉 RSI (Relative Strength Index)")
        st.markdown("""
RSI measures momentum — how strongly a stock is moving. It ranges from 0 to 100.
- If RSI > 70, the stock might be overbought.
- If RSI < 30, it might be oversold.
This helps identify potential reversals or trend continuations.
""")
        rsi_fig = go.Figure()
        rsi_fig.add_trace(go.Scatter(x=df["Date"], y=df["RSI"], name="RSI"))
        rsi_fig.update_layout(yaxis_range=[0, 100], height=250)
        st.plotly_chart(rsi_fig, use_container_width=True)

        # === MACD ===
        st.subheader("📈 MACD (Moving Average Convergence Divergence)")
        st.markdown("""
MACD helps spot trend changes and momentum.
- The MACD line crossing **above** the Signal line is a bullish sign (buy signal).
- Crossing **below** is a bearish sign (sell signal).
It works well to confirm or anticipate trend shifts.
""")
        macd_fig = go.Figure()
        macd_fig.add_trace(go.Scatter(x=df["Date"], y=df["MACD"], name="MACD"))
        macd_fig.add_trace(go.Scatter(x=df["Date"], y=df["Signal"], name="Signal"))
        st.plotly_chart(macd_fig, use_container_width=True)

        # === Stochastic Oscillator ===
        st.subheader("📊 Stochastic Oscillator")
        st.markdown("""
Stochastic measures where the price is relative to recent highs and lows.
- If it goes above 80, the stock may be overbought.
- If it falls below 20, it may be oversold.
It’s useful for spotting reversal points.
""")
        stoch_fig = go.Figure()
        stoch_fig.add_trace(go.Scatter(x=df["Date"], y=df["Stoch_K"], name="Stoch %K"))
        stoch_fig.add_trace(go.Scatter(x=df["Date"], y=df["Stoch_D"], name="Stoch %D"))
        st.plotly_chart(stoch_fig, use_container_width=True)

        # === CMF ===
        st.subheader("💸 Chaikin Money Flow (CMF)")
        st.markdown("""
CMF tells whether money is flowing in or out of a stock using price and volume.
- A CMF above 0 means buying pressure (bullish).
- Below 0 means selling pressure (bearish).
It validates strength behind moves.
""")
        cmf_fig = go.Figure()
        cmf_fig.add_trace(go.Scatter(x=df["Date"], y=df["CMF"], name="CMF"))
        cmf_fig.update_layout(yaxis_range=[-1, 1])
        st.plotly_chart(cmf_fig, use_container_width=True)

        # === OBV ===
        st.subheader("📦 On-Balance Volume (OBV)")
        st.markdown("""
OBV adds volume on up days and subtracts on down days.
- If OBV rises with price, it confirms the uptrend (bullish).
- If OBV falls while price rises, it suggests weak momentum (bearish divergence).
""")
        obv_fig = go.Figure()
        obv_fig.add_trace(go.Scatter(x=df["Date"], y=df["OBV"], name="OBV"))
        st.plotly_chart(obv_fig, use_container_width=True)

        # === Volume ===
        st.subheader("📊 Volume")
        vol_fig = go.Figure()
        vol_fig.add_trace(go.Bar(x=df["Date"], y=df["Volume"], name="Volume"))
        st.plotly_chart(vol_fig, use_container_width=True)

        # === Summary Layers ===
        st.subheader("🧠 Technical Summary (Agent 1)")

        st.markdown("**📌 Stock-Level Analysis (Agent 1.0):**")
        st.json(results.get("stock", {}))

        st.markdown("**🏭 Sector Analysis (Agent 1.1):**")
        st.info(results.get("sector", {}).get("summary", "No data."))

        st.markdown("**📊 Market Index (Agent 1.2):**")
        st.info(results.get("market", {}).get("summary", "No data."))

        st.markdown("**🛢️ Commodities (Agent 1.3):**")
        st.info(results.get("commodities", {}).get("summary", "No data."))

        st.markdown("**🌍 Global Indices (Agent 1.4):**")
        st.info(results.get("globals", {}).get("summary", "No data."))

        # === Final Outlook ===
        st.markdown("### ✅ Final Technical Outlook")
        st.success(results.get("final_summary", "No summary available."))
