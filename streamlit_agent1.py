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
- Stock indicators (SMA, MACD, RSI, Bollinger Bands, Volume, OBV, CMF, Stochastic)
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

        if "Date" not in df.columns:
            df = df.reset_index()

        # === Candlestick + SMA + BB ===
        st.subheader("🕯️ Candlestick Chart with SMA & Bollinger Bands")
        st.markdown("""
This chart shows daily price movement.
- **SMA** smooths out noise to show trends.
- **Bollinger Bands** reflect volatility — prices near the edges might be extreme.
""")
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df["Date"], open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="Price"
        ))
        fig.add_trace(go.Scatter(x=df["Date"], y=df["SMA5"], mode="lines", name="SMA5"))
        fig.add_trace(go.Scatter(x=df["Date"], y=df["SMA10"], mode="lines", name="SMA10"))
        fig.add_trace(go.Scatter(x=df["Date"], y=df["Upper"], mode="lines", name="Upper BB", line=dict(dash='dot')))
        fig.add_trace(go.Scatter(x=df["Date"], y=df["Lower"], mode="lines", name="Lower BB", line=dict(dash='dot')))
        fig.update_layout(height=500, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # === RSI ===
        if "RSI" in df.columns:
            st.subheader("📉 RSI (Relative Strength Index)")
            st.markdown("""
RSI shows if a stock is **overbought** or **oversold**.
- **>70**: Might be overbought (due for pullback)
- **<30**: Might be oversold (due for bounce)
""")
            rsi_fig = go.Figure()
            rsi_fig.add_trace(go.Scatter(x=df["Date"], y=df["RSI"], name="RSI"))
            rsi_fig.update_layout(yaxis_range=[0, 100], height=250)
            st.plotly_chart(rsi_fig, use_container_width=True)

        # === MACD ===
        if "MACD" in df.columns and "Signal" in df.columns:
            st.subheader("📈 MACD (Moving Average Convergence Divergence)")
            st.markdown("""
MACD helps detect **momentum** and **trend reversals**.
- MACD crossing **above** Signal → Bullish
- MACD crossing **below** Signal → Bearish
""")
            macd_fig = go.Figure()
            macd_fig.add_trace(go.Scatter(x=df["Date"], y=df["MACD"], name="MACD"))
            macd_fig.add_trace(go.Scatter(x=df["Date"], y=df["Signal"], name="Signal"))
            st.plotly_chart(macd_fig, use_container_width=True)

        # === Stochastic Oscillator ===
        if "Stoch_%K" in df.columns and "Stoch_%D" in df.columns:
            st.subheader("📊 Stochastic Oscillator")
            st.markdown("""
Stochastic shows how the price is doing relative to its recent highs/lows.
- **>80** = overbought
- **<20** = oversold
""")
            stoch_fig = go.Figure()
            stoch_fig.add_trace(go.Scatter(x=df["Date"], y=df["Stoch_%K"], name="%K"))
            stoch_fig.add_trace(go.Scatter(x=df["Date"], y=df["Stoch_%D"], name="%D"))
            stoch_fig.update_layout(yaxis_range=[0, 100], height=250)
            st.plotly_chart(stoch_fig, use_container_width=True)

        # === CMF ===
        if "CMF" in df.columns:
            st.subheader("💰 Chaikin Money Flow (CMF)")
            st.markdown("""
CMF helps track **buying vs selling pressure**.
- Positive = buying pressure
- Negative = selling pressure
""")
            cmf_fig = go.Figure()
            cmf_fig.add_trace(go.Scatter(x=df["Date"], y=df["CMF"], name="CMF"))
            st.plotly_chart(cmf_fig, use_container_width=True)

        # === OBV ===
        if "OBV" in df.columns:
            st.subheader("🔄 On-Balance Volume (OBV)")
            st.markdown("""
OBV tracks whether volume is flowing in (buying) or out (selling).
- Rising OBV → demand is increasing
""")
            obv_fig = go.Figure()
            obv_fig.add_trace(go.Scatter(x=df["Date"], y=df["OBV"], name="OBV"))
            st.plotly_chart(obv_fig, use_container_width=True)

        # === Volume ===
        if "Volume" in df.columns:
            st.subheader("📊 Volume")
            st.markdown("""
Volume shows total shares traded. Spikes often indicate large moves ahead.
""")
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

        st.markdown("### ✅ Final Technical Outlook")
        st.success(results.get("final_summary", "No summary available."))
