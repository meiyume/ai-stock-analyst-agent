
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
- 📈 Stock indicators (SMA, MACD, RSI, Bollinger Bands, Stochastic, CMF, OBV)
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
This chart combines three key tools for technical traders:

- **Candlestick Chart**: Visualizes daily price action. A green candle means the stock closed higher than it opened (bullish), while a red candle means it closed lower (bearish). Candlesticks help traders identify reversal patterns, momentum shifts, and support/resistance zones.
- **SMA (Simple Moving Average)**: SMA5 and SMA10 show short-term trends. When SMA5 crosses **above** SMA10, it may suggest bullish momentum. A cross **below** may signal weakening momentum.
- **Bollinger Bands**: These expand and contract with price volatility. If the price rises above the upper band, it might signal overbought conditions. If it dips below the lower band, it may be oversold. Bands tightening often precede major price movements.
""")

        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df["Date"], open=df["Open"], high=df["High"],
                                     low=df["Low"], close=df["Close"], name="Candles"))
        fig.add_trace(go.Scatter(x=df["Date"], y=df["SMA5"], mode="lines", name="SMA5"))
        fig.add_trace(go.Scatter(x=df["Date"], y=df["SMA10"], mode="lines", name="SMA10"))
        fig.add_trace(go.Scatter(x=df["Date"], y=df["Upper"], mode="lines", name="Upper BB", line=dict(dash='dot')))
        fig.add_trace(go.Scatter(x=df["Date"], y=df["Lower"], mode="lines", name="Lower BB", line=dict(dash='dot')))
        fig.update_layout(height=500, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        if "RSI" in df.columns:
            st.subheader("📉 RSI (Relative Strength Index)")
            st.markdown("""
RSI tracks momentum by comparing recent gains to losses.

- RSI > 70: Stock may be overbought — potential cooling or pullback.
- RSI < 30: Stock may be oversold — potential bounce or reversal.
""")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["Date"], y=df["RSI"], name="RSI"))
            fig.update_layout(yaxis_range=[0, 100], height=250)
            st.plotly_chart(fig, use_container_width=True)

        if "MACD" in df.columns and "Signal" in df.columns:
            st.subheader("📈 MACD (Moving Average Convergence Divergence)")
            st.markdown("""
MACD shows trend strength and direction by comparing short- and long-term EMAs.

- A **bullish crossover** (MACD crosses above Signal) suggests upward momentum.
- A **bearish crossover** (MACD below Signal) suggests downward momentum.
- Widely used to catch trend reversals early.
""")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["Date"], y=df["MACD"], name="MACD"))
            fig.add_trace(go.Scatter(x=df["Date"], y=df["Signal"], name="Signal"))
            st.plotly_chart(fig, use_container_width=True)

        if "Stochastic_%K" in df.columns:
            st.subheader("⚡ Stochastic Oscillator")
            st.markdown("""
Compares a stock’s close to its recent trading range.

- %K above 80: Overbought territory.
- %K below 20: Oversold territory.
- Bullish signal when %K crosses above %D in oversold zone. Bearish when it crosses below %D in overbought zone.
""")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["Date"], y=df["Stochastic_%K"], name="%K"))
            fig.add_trace(go.Scatter(x=df["Date"], y=df["Stochastic_%D"], name="%D"))
            st.plotly_chart(fig, use_container_width=True)

        if "CMF" in df.columns:
            st.subheader("💰 Chaikin Money Flow (CMF)")
            st.markdown("""
CMF tracks buying/selling pressure using both price and volume.

- Positive CMF: Buying (accumulation) pressure.
- Negative CMF: Selling (distribution) pressure.
- Helps detect hidden accumulation/distribution before price reacts.
""")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["Date"], y=df["CMF"], name="CMF"))
            st.plotly_chart(fig, use_container_width=True)

        if "OBV" in df.columns:
            st.subheader("🔄 On-Balance Volume (OBV)")
            st.markdown("""
OBV adds/subtracts daily volume based on price direction.

- Rising OBV + Rising Price: Confirmed uptrend.
- Falling OBV while price rises: Bearish divergence (rally losing strength).
- OBV can precede price movement — helpful for early signals.
""")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["Date"], y=df["OBV"], name="OBV"))
            st.plotly_chart(fig, use_container_width=True)

        if "Volume" in df.columns:
            st.subheader("📊 Volume")
            st.markdown("""
Volume shows trading activity. Spikes often indicate strong interest (news, breakouts).

- Unusual volume can confirm breakout moves or suggest reversal setups.
""")
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df["Date"], y=df["Volume"], name="Volume"))
            st.plotly_chart(fig, use_container_width=True)

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

        stock = results.get("stock", {}).get("summary", "")
        sector = results.get("sector", {}).get("summary", "")
        market = results.get("market", {}).get("summary", "")
        commodities = results.get("commodities", {}).get("summary", "")
        globals_ = results.get("globals", {}).get("summary", "")

        final_text = (
            f"📌 **Stock:** {stock}  \n"
            f"📊 **Sector:** {sector}  \n"
            f"📈 **Market Index:** {market}  \n"
            f"🛢️ **Commodities:** {commodities}  \n"
            f"🌍 **Global Indices:** {globals_}"
        )

        st.success(final_text)
