import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from agents.agent1_stock import run_full_technical_analysis, enforce_date_column, get_llm_summary

st.set_page_config(page_title="Agent 1: AI Technical Analyst", layout="wide")

# -- Premium, inclusive intro (Wall Street version) --
st.title("📊 Agent 1: AI Technical Analyst")
st.markdown("""
🤖 **Agent 1** is your AI-powered market sidekick—giving everyone the expert edge, whether you’re trading millions or just starting out.

🔎 With advanced tools like **SMA Trend**, **OBV**, **CMF**, and **Stochastic**, Agent 1 uncovers hidden trends and smart-money moves you won’t find on ordinary charts.

📊 It fuses classic signals (MACD, RSI, Bollinger Bands, ADX, ATR) with sector, commodities, and global insights for a complete, instant risk check.

💡 But here’s the real magic:  
Every scan comes with a clear risk score, an AI-written summary, _and_ plain-English explanations for every indicator and dashboard—so you always know exactly what you’re seeing, and why.

---

*Wall Street tools, finally in everyone’s hands—ready to level the playing field.*
""", unsafe_allow_html=True)

# --- User Input ---
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

# --- Session State for seamless UX ---
if "results" not in st.session_state:
    st.session_state["results"] = None
if "df" not in st.session_state:
    st.session_state["df"] = None

if st.button("🔍 Run Technical Analysis"):
    with st.spinner("Analyzing..."):
        results, df = run_full_technical_analysis(ticker, selected_horizon)
        df = enforce_date_column(df)
        st.session_state["results"] = results
        st.session_state["df"] = df

results = st.session_state["results"]
df = st.session_state["df"]

if df is None or results is None:
    st.info("Please run the technical analysis to view results.")
    st.stop()

stock_summary = results.get("stock", {}) if "stock" in results else results

# --- Anomaly event aggregation ---
anomaly_events = stock_summary.get("anomaly_events", [])
anomaly_by_indicator = {}
for event in anomaly_events:
    ind = event["indicator"]
    if ind not in anomaly_by_indicator:
        anomaly_by_indicator[ind] = []
    anomaly_by_indicator[ind].append((event["date"], event["event"]))

# === Candlestick + SMA + Bollinger Bands ===
st.subheader("🕯️ Candlestick Chart with SMA & Bollinger Bands")
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

# === RSI Chart ===
if "RSI" in df.columns:
    st.subheader("📉 RSI (Relative Strength Index)")
    rsi_fig = go.Figure()
    rsi_fig.add_trace(go.Scatter(
        x=df["Date"], y=df["RSI"],
        name="RSI", line=dict(width=3, color="purple")
    ))
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

# === MACD Chart ===
if "MACD" in df.columns and "Signal" in df.columns:
    st.subheader("📈 MACD (Moving Average Convergence Divergence)")
    macd_fig = go.Figure()
    macd_fig.add_trace(go.Scatter(x=df["Date"], y=df["MACD"], name="MACD", line=dict(width=3)))
    macd_fig.add_trace(go.Scatter(x=df["Date"], y=df["Signal"], name="Signal", line=dict(width=2, dash="dash")))
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

# === Volume Chart ===
if "Volume" in df.columns:
    st.subheader("📊 Volume")
    vol_fig = go.Figure()
    vol_fig.add_trace(go.Bar(x=df["Date"], y=df["Volume"], name="Volume", marker_color="#3d5a80"))
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

# === ATR Chart ===
if "ATR" in df.columns:
    st.subheader("📉 ATR (Average True Range)")
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

# === Stochastic Chart ===
if "Stochastic_%K" in df.columns:
    st.subheader("⚡ Stochastic Oscillator")
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

# === CMF, OBV, ADX Charts ===
if "CMF" in df.columns:
    st.subheader("💰 CMF (Chaikin Money Flow)")
    cmf_fig = go.Figure()
    cmf_fig.add_trace(go.Scatter(x=df["Date"], y=df["CMF"], name="CMF", line=dict(width=3, color="#7b5800")))
    cmf_fig.update_layout(height=180, margin=dict(t=16, b=8))
    st.plotly_chart(cmf_fig, use_container_width=True)

if "OBV" in df.columns:
    st.subheader("🔄 On-Balance Volume (OBV)")
    obv_fig = go.Figure()
    obv_fig.add_trace(go.Scatter(x=df["Date"], y=df["OBV"], name="OBV", line=dict(width=3, color="#3c6e71")))
    obv_fig.update_layout(height=180, margin=dict(t=16, b=8))
    st.plotly_chart(obv_fig, use_container_width=True)

if "ADX" in df.columns:
    st.subheader("📊 ADX (Average Directional Index)")
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
### 🧮 How to Read the Composite Risk Score
This score blends all technical signals into a single, intuitive risk rating:
- **Low Risk (0.00 – 0.33)**: ✅ Most signals healthy or bullish.
- **Caution (0.34 – 0.66)**: ⚠️ Mixed or volatile signals—watch closely.
- **High Risk (0.67 – 1.00)**: 🔥 Multiple bearish or red-flag indicators.

The overall risk level is a **quick summary**—helping you spot danger or opportunity at a glance.

> Example: Bearish MACD, Overbought RSI, and a Volume Spike could produce a **High Risk** score.

*Composite scoring makes risk transparent, explainable, and actionable—so you don’t just see the chart, you understand it.*
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

# === Technical Summary (Markdown + Table + Multi-Layer) ===
st.subheader("🧠 Technical Summary (Agent 1)")

# -- Stock-Level Markdown Block --
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

# -- Stock-Level Table (optional wow factor) --
st.subheader("🧠 Technical Summary (Multi-Layer)")
st.markdown("**📌 Stock-Level Technicals:**")
stock_metrics = {
    "SMA Trend": stock_summary.get('sma_trend'),
    "MACD": stock_summary.get('macd_signal'),
    "RSI": stock_summary.get('rsi_signal'),
    "Bollinger": stock_summary.get('bollinger_signal'),
    "Stochastic": stock_summary.get('stochastic_signal', 'N/A'),
    "CMF": stock_summary.get('cmf_signal', 'N/A'),
    "OBV": stock_summary.get('obv_signal', 'N/A'),
    "ADX": stock_summary.get('adx_signal', 'N/A'),
    "ATR": stock_summary.get('atr_signal', 'N/A'),
    "Volume Spike": stock_summary.get('vol_spike')
}
st.table(pd.DataFrame(stock_metrics, index=["Signal"]))

# -- Multi-Layer Context: Sector, Market, Commodities, Global --
st.markdown("**📌 Sector Analysis:**")
sector_summary = results.get("sector", None)
if sector_summary:
    st.markdown(sector_summary.get("summary", "No sector insights available."))

st.markdown("**📌 Market Index Analysis:**")
market_summary = results.get("market", None)
if market_summary:
    st.markdown(market_summary.get("summary", "No market index insights available."))

st.markdown("**📌 Commodities & Global Macro:**")
commodities_summary = results.get("commodities", None)
globals_summary = results.get("globals", None)
if commodities_summary:
    st.markdown(commodities_summary.get("summary", "No commodities insights available."))
if globals_summary:
    st.markdown(globals_summary.get("summary", "No global macro insights available."))

# === LLM Commentary (auto-generated, always visible) ===
api_key = st.secrets["OPENAI_API_KEY"]
with st.spinner("Agent 1 is generating LLM commentary..."):
    llm_summary = get_llm_summary(stock_summary, api_key)

# Split the LLM response:
if "For Technical Readers" in llm_summary and "For Grandmas and Grandpas" in llm_summary:
    technical, grandma = llm_summary.split("For Grandmas and Grandpas", 1)
    st.subheader("🧠 LLM-Powered Analyst Commentary")
    st.markdown(
        "<span style='font-size:1.3em;font-weight:600;'>🧑‍💼 For Technical Readers</span>",
        unsafe_allow_html=True
    )
    st.write(technical.replace("For Technical Readers", "").replace("Summary:", "").strip())
    st.markdown(
        "<span style='font-size:1.3em;font-weight:600;'>👵 For Grandmas and Grandpas</span>",
        unsafe_allow_html=True
    )
    st.write(grandma.replace("Summary:", "").strip())
else:
    st.subheader("🧠 LLM-Powered Analyst Commentary")
    st.write(llm_summary)





