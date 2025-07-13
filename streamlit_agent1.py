
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
- Stock indicators (SMA, MACD, RSI, Bollinger Bands)
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

        # === Candlestick + SMA + BB ===
        st.subheader("📊 Candlestick Chart with SMA & Bollinger Bands")
        st.markdown("""
This chart combines three powerful tools to visualize market trends.
- **Candlesticks**: Each candle represents a day of trading. A **green candle** means the stock closed higher than it opened (bullish), while a **red candle** means it closed lower (bearish). Candlesticks help traders spot patterns and reversals.
- **SMA (Simple Moving Averages)**: The **SMA5** shows the average closing price over the last 5 days; **SMA10** covers 10 days. When SMA5 is above SMA10, it suggests bullish momentum; when below, bearish momentum.
- **Bollinger Bands**: These show volatility. The upper and lower bands are placed two standard deviations away from a moving average. If prices touch or exceed the **upper band**, the stock may be **overbought**. If it dips below the **lower band**, it may be **oversold**. Traders use this to spot price extremes and reversals.
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
        fig.add_trace(go.Scatter(x=df["Date"], y=df["SMA_5"], mode="lines", name="SMA5"))
        fig.add_trace(go.Scatter(x=df["Date"], y=df["SMA_10"], mode="lines", name="SMA10"))
        fig.add_trace(go.Scatter(x=df["Date"], y=df["BB_Upper"], mode="lines", name="Upper BB", line=dict(dash='dot')))
        fig.add_trace(go.Scatter(x=df["Date"], y=df["BB_Lower"], mode="lines", name="Lower BB", line=dict(dash='dot')))
        fig.update_layout(height=500, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # === RSI ===
        if "RSI" in df.columns:
            st.subheader("📊 RSI (Relative Strength Index)")
            st.markdown("""
The RSI measures how fast and how far a stock's price has moved recently.
- It ranges from **0 to 100**.
- An RSI **above 70** indicates the stock might be **overbought** and could face a pullback.
- An RSI **below 30** suggests the stock is **oversold** and might rebound.
RSI helps investors decide whether the current trend is too strong to last.
""")
            rsi_fig = go.Figure()
            rsi_fig.add_trace(go.Scatter(x=df["Date"], y=df["RSI"], name="RSI"))
            rsi_fig.update_layout(yaxis_range=[0, 100], height=250)
            st.plotly_chart(rsi_fig, use_container_width=True)

        # === MACD ===
        if "MACD" in df.columns and "MACD_Signal" in df.columns:
            st.subheader("📊 MACD (Moving Average Convergence Divergence)")
            st.markdown("""
MACD tracks the difference between short- and long-term moving averages to show momentum.
- When the **MACD Line** crosses **above the Signal Line**, it's a **bullish signal**.
- When it crosses **below**, it's a **bearish signal**.
- The histogram bars grow as the difference between the two lines increases, indicating momentum.
MACD is useful for spotting early trend reversals.
""")
            macd_fig = go.Figure()
            macd_fig.add_trace(go.Scatter(x=df["Date"], y=df["MACD"], name="MACD"))
            macd_fig.add_trace(go.Scatter(x=df["Date"], y=df["MACD_Signal"], name="Signal"))
            st.plotly_chart(macd_fig, use_container_width=True)

        # === Volume ===
        if "Volume" in df.columns:
            st.subheader("📊 Volume")
            st.markdown("""
Volume shows how many shares were traded.
- **High volume** on a price move confirms strength behind the move.
- **Low volume** may mean the move is weak and not trustworthy.
Volume helps investors gauge conviction—strong moves with volume are more reliable.
""")
            vol_fig = go.Figure()
            vol_fig.add_trace(go.Bar(x=df["Date"], y=df["Volume"], name="Volume"))
            st.plotly_chart(vol_fig, use_container_width=True)

        # === Stochastic ===
        if "Stochastic_%K" in df.columns:
            st.subheader("📊 Stochastic Oscillator")
            st.markdown("""
The stochastic measures a stock’s closing price relative to its recent trading range.
- Above **80** means the stock may be **overbought**.
- Below **20** means it might be **oversold**.
- A **bullish signal** is when %K crosses **above** %D; **bearish** when it crosses below.
It helps detect potential reversals.
""")
            st.plotly_chart(go.Figure([
                go.Scatter(x=df["Date"], y=df["Stochastic_%K"], name="%K"),
                go.Scatter(x=df["Date"], y=df["Stochastic_%D"], name="%D")
            ]), use_container_width=True)

        # === OBV ===
        if "OBV" in df.columns:
            st.subheader("📊 OBV (On-Balance Volume)")
            st.markdown("""
OBV accumulates volume based on price movement:
- **Up day** = add volume to OBV.
- **Down day** = subtract volume.
If **OBV rises with price**, the trend is strong.
If **OBV falls while price rises**, it signals **bearish divergence**—a warning sign.
""")
            st.plotly_chart(go.Figure([
                go.Scatter(x=df["Date"], y=df["OBV"], name="OBV")
            ]), use_container_width=True)

        # === CMF ===
        if "CMF" in df.columns:
            st.subheader("📊 CMF (Chaikin Money Flow)")
            st.markdown("""
CMF measures the buying and selling pressure over time by combining price and volume.
- **Positive CMF (> 0)** = more buying pressure (bullish).
- **Negative CMF (< 0)** = more selling pressure (bearish).
The closer to +1 or -1, the stronger the pressure. CMF helps confirm breakouts and trends.
""")
            st.plotly_chart(go.Figure([
                go.Scatter(x=df["Date"], y=df["CMF"], name="CMF")
            ]), use_container_width=True)

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
