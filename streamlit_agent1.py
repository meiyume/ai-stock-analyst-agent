
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

        if "Date" not in df.columns:
            df = df.reset_index()

        st.subheader("🕯️ Candlestick Chart with SMA & Bollinger Bands")
        st.markdown("This chart shows the stock’s daily price movements. The candlesticks represent each day’s open, high, low, and close prices. Simple Moving Averages (SMA) help show the stock’s short-term and mid-term trend. Bollinger Bands measure how far prices move from their average — if the price touches the upper band, it may be overbought; if it touches the lower band, it may be oversold.")

        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df["Date"], open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="Price"))
        fig.add_trace(go.Scatter(x=df["Date"], y=df["SMA_5"], mode="lines", name="SMA5"))
        fig.add_trace(go.Scatter(x=df["Date"], y=df["SMA_10"], mode="lines", name="SMA10"))
        fig.add_trace(go.Scatter(x=df["Date"], y=df["BB_Upper"], mode="lines", name="Upper BB", line=dict(dash='dot')))
        fig.add_trace(go.Scatter(x=df["Date"], y=df["BB_Lower"], mode="lines", name="Lower BB", line=dict(dash='dot')))
        fig.update_layout(height=500, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        if "RSI" in df.columns:
            st.subheader("📉 RSI (Relative Strength Index)")
            st.markdown("RSI measures how strongly a stock has moved up or down recently. A value above 70 means the stock may be overbought and could drop. Below 30 means it's oversold and might bounce back.")
            rsi_fig = go.Figure()
            rsi_fig.add_trace(go.Scatter(x=df["Date"], y=df["RSI"], name="RSI"))
            rsi_fig.update_layout(yaxis_range=[0, 100], height=250)
            st.plotly_chart(rsi_fig, use_container_width=True)

        if "MACD" in df.columns and "MACD_Signal" in df.columns:
            st.subheader("📈 MACD (Moving Average Convergence Divergence)")
            st.markdown("MACD helps spot trend changes. When the MACD line crosses above the signal line, it’s a bullish sign. When it crosses below, it’s bearish — indicating the momentum is weakening.")
            macd_fig = go.Figure()
            macd_fig.add_trace(go.Scatter(x=df["Date"], y=df["MACD"], name="MACD"))
            macd_fig.add_trace(go.Scatter(x=df["Date"], y=df["MACD_Signal"], name="Signal"))
            st.plotly_chart(macd_fig, use_container_width=True)

        if "Stoch_K" in df.columns and "Stoch_D" in df.columns:
            st.subheader("📉 Stochastic Oscillator")
            st.markdown("The stochastic oscillator shows how current price compares to recent highs/lows. When %K crosses above %D from below 20, it could signal a rebound. When it crosses below from above 80, it could signal a pullback.")
            stoch_fig = go.Figure()
            stoch_fig.add_trace(go.Scatter(x=df["Date"], y=df["Stoch_K"], name="%K"))
            stoch_fig.add_trace(go.Scatter(x=df["Date"], y=df["Stoch_D"], name="%D"))
            stoch_fig.update_layout(yaxis_range=[0, 100], height=250)
            st.plotly_chart(stoch_fig, use_container_width=True)

        if "CMF" in df.columns:
            st.subheader("💵 Chaikin Money Flow (CMF)")
            st.markdown("CMF indicates whether money is flowing into or out of the stock. A positive CMF shows buying pressure (bullish), while a negative CMF shows selling pressure (bearish).")
            cmf_fig = go.Figure()
            cmf_fig.add_trace(go.Scatter(x=df["Date"], y=df["CMF"], name="CMF"))
            st.plotly_chart(cmf_fig, use_container_width=True)

        if "OBV" in df.columns:
            st.subheader("📊 On-Balance Volume (OBV)")
            st.markdown("OBV adds up volume based on price direction. It is useful to validate the strength behind a price move. If OBV rises with price, it confirms a bullish trend. If OBV drops while price goes up, it shows weak momentum (bearish divergence).")
            obv_fig = go.Figure()
            obv_fig.add_trace(go.Scatter(x=df["Date"], y=df["OBV"], name="OBV"))
            st.plotly_chart(obv_fig, use_container_width=True)

        if "Volume" in df.columns:
            st.subheader("📦 Volume")
            vol_fig = go.Figure()
            vol_fig.add_trace(go.Bar(x=df["Date"], y=df["Volume"], name="Volume"))
            st.plotly_chart(vol_fig, use_container_width=True)

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
