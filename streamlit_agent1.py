# streamlit_agent1.py

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from agents.agent1_stock import run_full_technical_analysis, enforce_date_column, get_llm_summary

# === Page Config ===
st.set_page_config(page_title="Agent 1: AI Technical Analyst", layout="wide")

st.title("📊 Agent 1: AI Technical Analyst")
st.markdown("""
Welcome to **Agent 1**, your AI-powered technical analyst.<br>
This agent performs a layered technical analysis using:<br>
- 📈 Stock indicators (SMA, MACD, RSI, Bollinger Bands, Stochastic, CMF, OBV, ADX, ATR)<br>
- 🏭 Peer sector comparison<br>
- 📊 Market index trends<br>
- 🛢️ Commodity signals (gold, oil)<br>
- 🌍 Global indices (Dow, Nikkei, HSI)
""", unsafe_allow_html=True)

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

results = {}
df = None

# === Run Analysis ===
if st.button("🔍 Run Technical Analysis"):
    with st.spinner("Analyzing..."):
        results, df = run_full_technical_analysis(ticker, selected_horizon)
        df = enforce_date_column(df)  # Always enforce after analysis!

# Prevent code from breaking if not run
if df is None or results == {}:
    st.info("Please run the technical analysis to view results.")
    st.stop()

stock_summary = results.get("stock", {}) if "stock" in results else results

# === Gather Anomalies for Each Indicator ===
anomaly_events = stock_summary.get("anomaly_events", [])
anomaly_by_indicator = {}
for event in anomaly_events:
    ind = event["indicator"]
    if ind not in anomaly_by_indicator:
        anomaly_by_indicator[ind] = []
    anomaly_by_indicator[ind].append((event["date"], event["event"]))

# === Candlestick + SMA + Bollinger Bands ===
st.subheader("🕯️ Candlestick Chart with SMA & Bollinger Bands")
st.markdown("""
Shows price movement (candles), trends (SMA), and volatility (Bollinger Bands).
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
patterns = stock_summary.get("patterns", [])
st.subheader("📌 Detected Candlestick Patterns")
if patterns:
    st.markdown(
        ", ".join([f"✅ **{p}**" for p in patterns]) + "\n\n"
        + "These patterns were detected in the last 3 candles."
    )
else:
    st.info("No recognizable candlestick patterns detected in the last 3 candles.")

# === RSI Chart with Anomaly Markers ===
if "RSI" in df.columns:
    st.subheader("📉 RSI (Relative Strength Index)")
    st.markdown("""
    RSI (0–100). Overbought (&gt;70): Pullback risk. Oversold (&lt;30): Rebound potential.
    """, unsafe_allow_html=True)
    rsi_fig = go.Figure()
    rsi_fig.add_trace(go.Scatter(
        x=df["Date"], y=df["RSI"],
        name="RSI", line=dict(width=3, color="purple")
    ))
    # Add anomaly markers for RSI
    for date, event in anomaly_by_indicator.get("RSI", []):
        y_val = df.loc[df["Date"] == date, "RSI"].values
        if len(y_val) > 0:
            rsi_fig.add_trace(go.Scatter(
                x=[date], y=[y_val[0]],
                mode="markers+text",
                marker=dict(size=12, color="red", symbol="star"),
                text=[event], textposition="top center",
                name=f"Anomaly: {event}"
            ))
    rsi_fig.update_yaxes(range=[0, 100])
    rsi_fig.update_layout(height=220, margin=dict(t=16, b=8))
    st.plotly_chart(rsi_fig, use_container_width=True)

# === MACD Chart with Anomaly Markers ===
if "MACD" in df.columns and "Signal" in df.columns:
    st.subheader("📈 MACD (Moving Average Convergence Divergence)")
    st.markdown("""
    MACD helps identify trend strength/direction.<br>
    MACD &gt; Signal: Bullish. MACD &lt; Signal: Bearish.
    """, unsafe_allow_html=True)
    macd_fig = go.Figure()
    macd_fig.add_trace(go.Scatter(x=df["Date"], y=df["MACD"], name="MACD", line=dict(width=3)))
    macd_fig.add_trace(go.Scatter(x=df["Date"], y=df["Signal"], name="Signal", line=dict(width=2, dash="dash")))
    # Add anomaly markers for MACD
    for date, event in anomaly_by_indicator.get("MACD", []):
        y_val = df.loc[df["Date"] == date, "MACD"].values
        if len(y_val) > 0:
            macd_fig.add_trace(go.Scatter(
                x=[date], y=[y_val[0]],
                mode="markers+text",
                marker=dict(size=12, color="red", symbol="diamond"),
                text=[event], textposition="bottom center",
                name=f"Anomaly: {event}"
            ))
    macd_fig.update_layout(height=220, margin=dict(t=16, b=8))
    st.plotly_chart(macd_fig, use_container_width=True)

# === Volume Chart with Anomaly Markers ===
if "Volume" in df.columns:
    st.subheader("📊 Volume")
    st.markdown("Volume shows trading activity. Spikes may mean institutional moves/news.")
    vol_fig = go.Figure()
    vol_fig.add_trace(go.Bar(x=df["Date"], y=df["Volume"], name="Volume", marker_color="#3d5a80"))
    # Add anomaly markers for Volume
    for date, event in anomaly_by_indicator.get("Volume", []):
        y_val = df.loc[df["Date"] == date, "Volume"].values
        if len(y_val) > 0:
            vol_fig.add_trace(go.Scatter(
                x=[date], y=[y_val[0]],
                mode="markers+text",
                marker=dict(size=14, color="red", symbol="triangle-up"),
                text=[event], textposition="top center",
                name=f"Anomaly: {event}"
            ))
    vol_fig.update_layout(height=180, margin=dict(t=16, b=8))
    st.plotly_chart(vol_fig, use_container_width=True)

# === ATR Chart with Anomaly Markers ===
if "ATR" in df.columns:
    st.subheader("📉 ATR (Average True Range)")
    st.markdown("""
    ATR measures volatility. High ATR: Big moves. Low ATR: Stable.
    """, unsafe_allow_html=True)
    atr_fig = go.Figure()
    atr_fig.add_trace(go.Scatter(x=df["Date"], y=df["ATR"], name="ATR", line=dict(width=3, color="#a31621")))
    for date, event in anomaly_by_indicator.get("ATR", []):
        y_val = df.loc[df["Date"] == date, "ATR"].values
        if len(y_val) > 0:
            atr_fig.add_trace(go.Scatter(
                x=[date], y=[y_val[0]],
                mode="markers+text",
                marker=dict(size=12, color="red", symbol="circle"),
                text=[event], textposition="top center",
                name=f"Anomaly: {event}"
            ))
    atr_fig.update_layout(height=180, margin=dict(t=16, b=8))
    st.plotly_chart(atr_fig, use_container_width=True)

# === Stochastic Oscillator with Anomaly Markers ===
if "Stochastic_%K" in df.columns:
    st.subheader("⚡ Stochastic Oscillator")
    st.markdown("""
    Stochastic compares close to recent range. %K &gt; 80: Overbought. %K &lt; 20: Oversold.
    """, unsafe_allow_html=True)
    stoch_fig = go.Figure()
    stoch_fig.add_trace(go.Scatter(x=df["Date"], y=df["Stochastic_%K"], name="Stoch %K", line=dict(width=3, color="blue")))
    stoch_fig.add_trace(go.Scatter(x=df["Date"], y=df["Stochastic_%D"], name="Stoch %D", line=dict(width=2, color="green", dash="dash")))
    for date, event in anomaly_by_indicator.get("Stochastic", []):
        y_val = df.loc[df["Date"] == date, "Stochastic_%K"].values
        if len(y_val) > 0:
            stoch_fig.add_trace(go.Scatter(
                x=[date], y=[y_val[0]],
                mode="markers+text",
                marker=dict(size=12, color="red", symbol="x"),
                text=[event], textposition="top center",
                name=f"Anomaly: {event}"
            ))
    stoch_fig.update_yaxes(range=[0, 100])
    stoch_fig.update_layout(height=220, margin=dict(t=16, b=8))
    st.plotly_chart(stoch_fig, use_container_width=True)

# === CMF, OBV, ADX Charts (no anomalies for these unless you add) ===
if "CMF" in df.columns:
    st.subheader("💰 CMF (Chaikin Money Flow)")
    st.markdown("""
    Money flow over time. Positive: Buying pressure. Negative: Selling pressure.
    """, unsafe_allow_html=True)
    cmf_fig = go.Figure()
    cmf_fig.add_trace(go.Scatter(x=df["Date"], y=df["CMF"], name="CMF", line=dict(width=3, color="#7b5800")))
    cmf_fig.update_layout(height=180, margin=dict(t=16, b=8))
    st.plotly_chart(cmf_fig, use_container_width=True)

if "OBV" in df.columns:
    st.subheader("🔄 On-Balance Volume (OBV)")
    st.markdown("""
    OBV tracks accumulation/distribution. Rising OBV + rising price: Bullish.
    """, unsafe_allow_html=True)
    obv_fig = go.Figure()
    obv_fig.add_trace(go.Scatter(x=df["Date"], y=df["OBV"], name="OBV", line=dict(width=3, color="#3c6e71")))
    obv_fig.update_layout(height=180, margin=dict(t=16, b=8))
    st.plotly_chart(obv_fig, use_container_width=True)

if "ADX" in df.columns:
    st.subheader("📊 ADX (Average Directional Index)")
    st.markdown("""
    ADX measures trend strength (not direction). ADX &gt; 25: Strong trend.
    """, unsafe_allow_html=True)
    adx_fig = go.Figure()
    adx_fig.add_trace(go.Scatter(x=df["Date"], y=df["ADX"], name="ADX", line=dict(width=3, color='orange')))
    adx_fig.update_yaxes(range=[0, 100])
    adx_fig.update_layout(height=220, margin=dict(t=16, b=8))
    st.plotly_chart(adx_fig, use_container_width=True)

# === Historical Anomaly Events Table ===
with st.expander("🕰️ Historical Anomaly Events", expanded=False):
    if anomaly_events:
        df_anom = pd.DataFrame(anomaly_events)
        if not df_anom.empty:
            df_anom = df_anom[["date", "indicator", "event"]].sort_values("date")
            st.dataframe(df_anom.rename(columns={
                "date": "Date",
                "indicator": "Indicator",
                "event": "Anomaly Event"
            }), use_container_width=True, hide_index=True)
        else:
            st.info("No anomalies detected.")
    else:
        st.info("No anomalies detected.")

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
if risk_score is not None:
    st.markdown(f"**Composite Risk Score**: `{risk_score}`")
if risk_level is not None:
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

# === Technical Summary ===
st.subheader("🧠 Technical Summary (Agent 1)")
st.markdown("**📌 Stock-Level Analysis (Agent 1.0):**")
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

# === LLM Commentary ===
api_key = st.secrets["OPENAI_API_KEY"]
if st.button("🧠 Generate LLM Analysis"):
    with st.spinner("Agent 1 is thinking..."):
        llm_summary = get_llm_summary(stock_summary, api_key)
    st.subheader("🧠 LLM-Powered Analyst Commentary")
    st.write(llm_summary)

# (You may continue with Sector/Market/Commodities/Global summaries as in your full version)

