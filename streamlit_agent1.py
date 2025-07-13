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
- Stock indicators (SMA, MACD, RSI, Bollinger Bands, OBV, Stochastic, CMF)
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

        # === Candlestick + SMA + Bollinger Bands ===
        st.subheader("🕯️ Candlestick Chart with SMA & Bollinger Bands")
        st.caption("Candlesticks are colored bars that show price movement for each day. A green candle means the stock closed higher than it opened (price went up). 
        A red candle means it closed lower than it opened (price went down). Each candle also shows the day's high and low, giving a full picture of price action. 
        The SMA (Simple Moving Averages) are smooth lines overlaid on the chart: SMA5 is the average closing price of the last 5 days. SMA10 is the average over the last 10 days.
        These help identify short-term trends—when SMA5 is above SMA10, it's often a bullish sign. 
        The Bollinger Bands are two dotted lines that expand and contract around the price: They measure volatility, or how wildly the price is moving. The middle line is usually 
        the 20-day average; the upper and lower bands are 2 standard deviations away. If prices move close to or above the upper band, it might signal the stock is overbought (too expensive).
        If they touch or drop below the lower band, it may mean the stock is oversold (possibly undervalued).
        Together, this chart helps you see trend direction, market sentiment, volatility and extremes to make smarter decisions on when to buy or sell.                   
                   ")
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
        if "RSI" in df.columns:
            st.subheader("📉 RSI (Relative Strength Index)")
            st.caption("RSI measures momentum. Values above 70 suggest the stock may be overbought; below 30 may mean it's oversold.")
            rsi_fig = go.Figure()
            rsi_fig.add_trace(go.Scatter(x=df["Date"], y=df["RSI"], name="RSI"))
            rsi_fig.update_layout(yaxis_range=[0, 100], height=250)
            st.plotly_chart(rsi_fig, use_container_width=True)

        # === MACD ===
        if "MACD" in df.columns and "Signal" in df.columns:
            st.subheader("📈 MACD (Moving Average Convergence Divergence)")
            st.caption("MACD shows momentum. When MACD crosses above the Signal line, it's a bullish sign. "
                       "When it crosses below, it may signal a downtrend.")
            macd_fig = go.Figure()
            macd_fig.add_trace(go.Scatter(x=df["Date"], y=df["MACD"], name="MACD"))
            macd_fig.add_trace(go.Scatter(x=df["Date"], y=df["Signal"], name="Signal"))
            st.plotly_chart(macd_fig, use_container_width=True)

        # === OBV ===
        if "OBV" in df.columns:
            st.subheader("🔄 On-Balance Volume (OBV)")
            st.caption("OBV adds up volume based on price movement. Rising OBV with price confirms strength (bullish). "
                       "Falling OBV while price rises shows weak momentum (bearish divergence).")
            obv_fig = go.Figure()
            obv_fig.add_trace(go.Scatter(x=df["Date"], y=df["OBV"], name="OBV"))
            st.plotly_chart(obv_fig, use_container_width=True)

        # === CMF ===
        if "CMF" in df.columns:
            st.subheader("💰 Chaikin Money Flow (CMF)")
            st.caption("CMF combines price and volume to detect buying or selling pressure. "
                       "Positive CMF suggests accumulation (bullish), negative CMF indicates distribution (bearish).")
            cmf_fig = go.Figure()
            cmf_fig.add_trace(go.Scatter(x=df["Date"], y=df["CMF"], name="CMF"))
            st.plotly_chart(cmf_fig, use_container_width=True)

        # === Stochastic Oscillator ===
        if "Stochastic_K" in df.columns and "Stochastic_D" in df.columns:
            st.subheader("📊 Stochastic Oscillator")
            st.caption("Stochastic compares current price to recent highs/lows. If it’s above 80, stock may be overbought; "
                       "below 20 may be oversold. Crossovers between %K and %D can indicate entry/exit signals.")
            sto_fig = go.Figure()
            sto_fig.add_trace(go.Scatter(x=df["Date"], y=df["Stochastic_K"], name="%K"))
            sto_fig.add_trace(go.Scatter(x=df["Date"], y=df["Stochastic_D"], name="%D"))
            sto_fig.update_layout(yaxis_range=[0, 100])
            st.plotly_chart(sto_fig, use_container_width=True)

        # === Volume ===
        if "Volume" in df.columns:
            st.subheader("📦 Volume")
            st.caption("Volume shows how much of the stock was traded. Volume spikes often precede major price moves.")
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
