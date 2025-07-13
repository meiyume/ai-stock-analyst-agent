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

        # === ADX ===
        if "ADX" in df.columns:
            st.subheader("📊 ADX (Average Directional Index)")
            st.markdown("""
ADX measures the **strength** of a trend, regardless of direction. 

- **ADX > 25**: A strong trend is present (bull or bear).
- **ADX < 20**: Market is ranging or lacks direction.
            """)
            adx_fig = go.Figure()
            adx_fig.add_trace(go.Scatter(x=df["Date"], y=df["ADX"], name="ADX"))
            adx_fig.update_layout(yaxis_range=[0, 100], height=250)
            st.plotly_chart(adx_fig, use_container_width=True)

        # === ATR ===
        if "ATR" in df.columns:
            st.subheader("📉 ATR (Average True Range)")
            st.markdown("""
ATR measures **volatility** — how much a stock moves day to day.

- High ATR: Stock is making big moves (can be risky or offer opportunity).
- Low ATR: Price is stable, small daily swings.
            """)
            atr_fig = go.Figure()
            atr_fig.add_trace(go.Scatter(x=df["Date"], y=df["ATR"], name="ATR"))
            st.plotly_chart(atr_fig, use_container_width=True)

        # === Volume ===
        if "Volume" in df.columns:
            st.subheader("📊 Volume")
            st.markdown("""
Volume shows how actively a stock is being traded. Sudden spikes may indicate institutional activity or major news.
            """)
            vol_fig = go.Figure()
            vol_fig.add_trace(go.Bar(x=df["Date"], y=df["Volume"], name="Volume"))
            st.plotly_chart(vol_fig, use_container_width=True)

        


        # === Risk Dashboard ===
        st.markdown("## 🛡️ Risk Dashboard")
        st.markdown("""
        <div style='background-color:#f8f9fa; padding: 20px; border-radius: 10px;'>
        <h5 style='margin-bottom: 10px;'>🧠 Interpreting Risk Signals</h5>
        <p>This dashboard summarizes multiple technical signals using intuitive color-coded cues.</p>
        <ul>
          <li><b>🟢 Bullish / Healthy</b>: Indicator shows strength or stability</li>
          <li><b>🟠 Volatile / Watch</b>: Caution advised – indicator signals instability</li>
          <li><b>🔴 Bearish / Risky</b>: Indicator shows weakness or negative pressure</li>
          <li><b>⚪ Neutral / No Signal</b>: No actionable signal detected</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)

        heatmap = stock_summary.get("heatmap_signals", {})
        risk_score = stock_summary.get("composite_risk_score", None)
        risk_level = stock_summary.get("risk_level", None)

        
if heatmap:
    st.markdown("#### 🔍 Current Signal Status")
    cols = st.columns(len(heatmap))
    for i, (indicator, status) in enumerate(heatmap.items()):
        if "Overbought" in status or "Bearish" in status or "Selling" in status or "Divergence" in status:
            color = "🔴"
        elif "Spike" in status or "High" in status or "Oversold" in status:
            color = "🟠"
        elif "Bullish" in status or "Buying" in status or "Strong" in status:
            color = "🟢"
        elif "Neutral" in status or "None" in status:
            color = "⚪"
        else:
            color = "🟡"

        cols[i].markdown(
            f"<div style='background-color:#ffffff;padding:10px;border-radius:10px;text-align:center;'>"
            f"<b>{indicator}</b><br>{color} {status}</div>",
            unsafe_allow_html=True
        )

    
st.markdown(f"**Composite Risk Score**: `{risk_score}`")
st.markdown(f"**Overall Risk Level**: 🎯 **{risk_level}**")
        st.markdown("""
        ### 🧮 How to Interpret the Composite Risk Score

        The **Composite Risk Score** is a weighted calculation of technical indicators, normalized to a range between **0.00 (low risk)** and **1.00 (high risk)**.

        It reflects how many red flags are being raised and how serious those signals are based on:

        - **Strength and direction of trends** (e.g., MACD, ADX)
        - **Volatility and anomalies** (e.g., RSI spikes, ATR)
        - **Volume behavior and market sentiment** (e.g., volume spikes, patterns)

        | Score Range | What It Means         |
        |-------------|------------------------|
        | **0.00 – 0.33** | ✅ **Low Risk**: Signals are stable or bullish |
        | **0.34 – 0.66** | ⚠️ **Caution**: Mixed signals; watch carefully |
        | **0.67 – 1.00** | 🔥 **High Risk**: Multiple red flags detected |

        ### 🎯 What Does the Overall Risk Level Mean?

        This is a **simplified risk tag** derived from the composite score, designed to:

        - Help retail users **make fast decisions**
        - Allow investors to assess **signal intensity at a glance**
        - Enable Agent 2 to prioritize predictive efforts on high-alert stocks

        > For example, a stock with `MACD Bearish`, `Overbought RSI`, and a `Volume Spike` might result in a score of `0.72` — tagged as **High Risk**.

        ### ✅ Why It Matters

        This system provides a **quantitative, explainable**, and **repeatable** way to evaluate stock risk. We're not just showing charts — we're **translating technical complexity into clear, actionable insight.**

        ### 🚀 Expandability Built In

        We’ve designed this dashboard to evolve — soon we’ll include:
        - 📈 SMA trend momentum
        - 🔄 OBV divergences
        - 🧠 LLM-enhanced pattern confidence
        """, unsafe_allow_html=True)


        st.markdown("✅ *SMA Trend, OBV, CMF, and Stochastic signals are now integrated into the dashboard for a fuller view of risk.*")
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
            f"• **ADX Signal**: {stock_summary.get('adx_signal', 'N/A')}  \n"
            f"• **ATR Signal**: {stock_summary.get('atr_signal', 'N/A')}  \n"
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



