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

        # === RSI ===
        if "RSI" in df.columns:
            st.subheader("📉 RSI (Relative Strength Index)")
            st.markdown("""
RSI measures the speed and magnitude of recent price changes on a 0–100 scale.

- If RSI > 70: The stock may be **overbought**, potentially due for a pullback.
- If RSI < 30: The stock may be **oversold**, potentially due for a rebound.
            """)
            rsi_fig = go.Figure()
            rsi_fig.add_trace(go.Scatter(x=df["Date"], y=df["RSI"], name="RSI"))
            rsi_fig.update_layout(yaxis_range=[0, 100], height=250)
            st.plotly_chart(rsi_fig, use_container_width=True)

        # === MACD ===
        if "MACD" in df.columns and "Signal" in df.columns:
            st.subheader("📈 MACD (Moving Average Convergence Divergence)")
            st.markdown("""
MACD helps identify trend strength and direction.

- **MACD Line vs Signal Line**: When the MACD crosses **above** the Signal line, it’s a **bullish signal**. When it crosses **below**, it’s **bearish**.
            """)
            macd_fig = go.Figure()
            macd_fig.add_trace(go.Scatter(x=df["Date"], y=df["MACD"], name="MACD"))
            macd_fig.add_trace(go.Scatter(x=df["Date"], y=df["Signal"], name="Signal"))
            st.plotly_chart(macd_fig, use_container_width=True)

        # === Stochastic Oscillator ===
        if "Stochastic_%K" in df.columns:
            st.subheader("⚡ Stochastic Oscillator")
            st.markdown("""
The Stochastic Oscillator compares a stock’s closing price to its price range over a certain period.

- **%K Line and %D Line**: When %K crosses above %D and both are below 20, it may signal a **bullish reversal**. If they’re above 80 and %K drops below %D, it could indicate **bearish** pressure.
            """)
            stoch_fig = go.Figure()
            stoch_fig.add_trace(go.Scatter(x=df["Date"], y=df["Stochastic_%K"], name="Stoch %K"))
            stoch_fig.add_trace(go.Scatter(x=df["Date"], y=df["Stochastic_%D"], name="Stoch %D"))
            st.plotly_chart(stoch_fig, use_container_width=True)

        # === CMF ===
        if "CMF" in df.columns:
            st.subheader("💰 Chaikin Money Flow (CMF)")
            st.markdown("""
CMF measures money flow volume over time to assess buying/selling pressure.

- A **positive CMF** suggests accumulation (buying).
- A **negative CMF** indicates distribution (selling).
            """)
            cmf_fig = go.Figure()
            cmf_fig.add_trace(go.Scatter(x=df["Date"], y=df["CMF"], name="CMF"))
            st.plotly_chart(cmf_fig, use_container_width=True)

        # === OBV ===
        if "OBV" in df.columns:
            st.subheader("🔄 On-Balance Volume (OBV)")
            st.markdown("""
OBV adds or subtracts volume based on whether the price closes higher or lower.

- **Rising OBV with rising price** confirms a **bullish trend**.
- **Falling OBV while price rises** may indicate **bearish divergence** (weak rally).
            """)
            obv_fig = go.Figure()
            obv_fig.add_trace(go.Scatter(x=df["Date"], y=df["OBV"], name="OBV"))
            st.plotly_chart(obv_fig, use_container_width=True)

        # === Volume ===
        if "Volume" in df.columns:
            st.subheader("📊 Volume")
            st.markdown("""
Volume shows how actively a stock is being traded. Sudden spikes may indicate institutional activity or major news.
            """)
            vol_fig = go.Figure()
            vol_fig.add_trace(go.Bar(x=df["Date"], y=df["Volume"], name="Volume"))
            st.plotly_chart(vol_fig, use_container_width=True)

        # === Summary Layers ===
        st.subheader("🧠 Technical Summary (Agent 1)")

        st.markdown("**📌 Stock-Level Analysis (Agent 1.0):**")
        stock_summary = results.get("stock", {})
        stock_text = (
            f"• **SMA Trend**: {stock_summary.get('sma_trend')}  \n"
            f"• **MACD Signal**: {stock_summary.get('macd_signal')}  \n"
            f"• **RSI Signal**: {stock_summary.get('rsi_signal')}  \n"
            f"• **Bollinger Signal**: {stock_summary.get('bollinger_signal')}  \n"
            f"• **Stochastic**: {stock_summary.get('stochastic_signal', 'N/A')}  \n"
            f"• **CMF Signal**: {stock_summary.get('cmf_signal', 'N/A')}  \n"
            f"• **OBV Signal**: {stock_summary.get('obv_signal', 'N/A')}  \n"
            f"• **Volume Spike**: {stock_summary.get('vol_spike')}"
        )
        st.markdown(stock_text)

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


