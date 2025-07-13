import streamlit as st
import plotly.graph_objects as go
from agents.agent1_core import run_full_technical_analysis

# === Page Config ===
st.set_page_config(page_title="Agent 1: AI Technical Analyst", layout="wide")

st.title("📊 Agent 1: AI Technical Analyst")
st.markdown("""
<div style='font-size:1.15rem;'>
Welcome to <b>Agent 1</b>, your AI-powered technical analyst.<br>
This agent performs layered technical analysis using:
<ul>
  <li>📈 <b>Stock indicators</b> (SMA, MACD, RSI, Bollinger Bands, Stochastic, CMF, OBV, ADX, ATR)</li>
  <li>🏭 <b>Peer sector comparison</b></li>
  <li>📊 <b>Market index trends</b></li>
  <li>🛢️ <b>Commodities signals</b> (gold, oil)</li>
  <li>🌍 <b>Global indices</b> (Dow, Nikkei, HSI)</li>
</ul>
</div>
<hr>
""", unsafe_allow_html=True)

# === User Input ===
st.sidebar.header("⚙️ Analysis Settings")
ticker = st.sidebar.text_input("🎯 Enter SGX Stock Ticker", value="U11.SI")
horizon = st.sidebar.selectbox("📅 Select Outlook Horizon", [
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
run_button = st.sidebar.button("🔍 Run Technical Analysis", use_container_width=True)
if run_button:
    with st.spinner("Analyzing..."):
        results, df = run_full_technical_analysis(ticker, selected_horizon)
        df = df.reset_index()

# Prevent code from breaking if not run
if df is None or results == {}:
    st.info("Please use the sidebar and run the analysis to view results.")
    st.stop()

stock_summary = results.get("stock", {})

# === Candlestick + SMA + Bollinger Bands ===
st.markdown("### 🕯️ Candlestick Chart with SMA & Bollinger Bands")
st.markdown("""
Shows price movement, trend, and volatility. <br>
<ul>
<li><b>Candlestick chart:</b> Each candle shows a trading day. Green = bullish, red = bearish.</li>
<li><b>SMA (Simple Moving Average):</b> SMA5 & SMA10 track short-term trends. Watch crossovers.</li>
<li><b>Bollinger Bands:</b> 2 standard deviations from SMA10. Price above upper band may suggest overbought; below lower = oversold.</li>
</ul>
""", unsafe_allow_html=True)
fig = go.Figure()
fig.add_trace(go.Candlestick(
    x=df["Date"], open=df["Open"], high=df["High"],
    low=df["Low"], close=df["Close"], name="Candles"
))
fig.add_trace(go.Scatter(x=df["Date"], y=df["SMA5"], mode="lines", name="SMA5"))
fig.add_trace(go.Scatter(x=df["Date"], y=df["SMA10"], mode="lines", name="SMA10"))
fig.add_trace(go.Scatter(x=df["Date"], y=df["Upper"], mode="lines", name="Upper BB", line=dict(dash='dot')))
fig.add_trace(go.Scatter(x=df["Date"], y=df["Lower"], mode="lines", name="Lower BB", line=dict(dash='dot')))
fig.update_layout(height=480, xaxis_rangeslider_visible=False, margin=dict(t=16, b=0))
st.plotly_chart(fig, use_container_width=True)

# === Pattern Detection ===
with st.expander("📌 Detected Candlestick Patterns", expanded=True):
    patterns = stock_summary.get("patterns", [])
    if patterns:
        st.success("Detected pattern(s): " + ", ".join([f"**{p}**" for p in patterns]))
    else:
        st.info("Detected pattern(s): _None_")

# === Anomaly Alerts ===
with st.expander("🚨 Anomaly Alerts", expanded=True):
    anomalies = stock_summary.get("anomalies", [])
    if anomalies:
        for alert in anomalies:
            st.warning(f"⚠️ {alert}")
    else:
        st.info("No anomalies detected today. 📈")

# === Indicator Visualizations (with compact expander sections) ===
with st.expander("📉 RSI / Relative Strength Index", expanded=False):
    if "RSI" in df.columns:
        st.markdown("""
        RSI measures the speed and magnitude of recent price changes (0–100 scale).<br>
        > Overbought (&gt;70): Potential pullback. <br>
        > Oversold (&lt;30): Potential rebound.
        """, unsafe_allow_html=True)
        rsi_fig = go.Figure()
        rsi_fig.add_trace(go.Scatter(x=df["Date"], y=df["RSI"], name="RSI"))
        rsi_fig.update_layout(yaxis_range=[0, 100], height=180)
        st.plotly_chart(rsi_fig, use_container_width=True)

with st.expander("📈 MACD (Moving Average Convergence Divergence)", expanded=False):
    if "MACD" in df.columns and "Signal" in df.columns:
        st.markdown("""
        MACD helps identify trend strength/direction.<br>
        - <b>MACD > Signal</b>: Bullish signal<br>
        - <b>MACD &lt; Signal</b>: Bearish signal
        """, unsafe_allow_html=True)
        macd_fig = go.Figure()
        macd_fig.add_trace(go.Scatter(x=df["Date"], y=df["MACD"], name="MACD"))
        macd_fig.add_trace(go.Scatter(x=df["Date"], y=df["Signal"], name="Signal"))
        st.plotly_chart(macd_fig, use_container_width=True)

with st.expander("⚡ Stochastic Oscillator", expanded=False):
    if "Stochastic_%K" in df.columns:
        st.markdown("""
        Compares close price to recent range.<br>
        - <b>%K > 80</b>: Overbought<br>
        - <b>%K &lt; 20</b>: Oversold
        """, unsafe_allow_html=True)
        stoch_fig = go.Figure()
        stoch_fig.add_trace(go.Scatter(x=df["Date"], y=df["Stochastic_%K"], name="Stoch %K"))
        stoch_fig.add_trace(go.Scatter(x=df["Date"], y=df["Stochastic_%D"], name="Stoch %D"))
        st.plotly_chart(stoch_fig, use_container_width=True)

with st.expander("💰 CMF (Chaikin Money Flow)", expanded=False):
    if "CMF" in df.columns:
        st.markdown("""
        Money flow over time.<br>
        - <b>Positive:</b> Buying pressure<br>
        - <b>Negative:</b> Selling pressure
        """, unsafe_allow_html=True)
        cmf_fig = go.Figure()
        cmf_fig.add_trace(go.Scatter(x=df["Date"], y=df["CMF"], name="CMF"))
        st.plotly_chart(cmf_fig, use_container_width=True)

with st.expander("🔄 OBV (On-Balance Volume)", expanded=False):
    if "OBV" in df.columns:
        st.markdown("""
        OBV tracks accumulation/distribution.<br>
        - <b>Rising OBV + rising price:</b> Bullish<br>
        - <b>Falling OBV while price rises:</b> Bearish divergence
        """, unsafe_allow_html=True)
        obv_fig = go.Figure()
        obv_fig.add_trace(go.Scatter(x=df["Date"], y=df["OBV"], name="OBV"))
        st.plotly_chart(obv_fig, use_container_width=True)

with st.expander("📊 ADX (Average Directional Index)", expanded=False):
    if "ADX" in df.columns:
        st.markdown("""
        ADX measures trend <b>strength</b> (not direction).<br>
        - <b>ADX &gt; 25</b>: Strong trend<br>
        - <b>ADX &lt; 20</b>: Weak/no trend
        """, unsafe_allow_html=True)
        adx_fig = go.Figure()
        adx_fig.add_trace(go.Scatter(x=df["Date"], y=df["ADX"], name="ADX"))
        adx_fig.update_layout(yaxis_range=[0, 100], height=180)
        st.plotly_chart(adx_fig, use_container_width=True)

with st.expander("📉 ATR (Average True Range)", expanded=False):
    if "ATR" in df.columns:
        st.markdown("""
        ATR measures <b>volatility</b>.<br>
        - <b>High ATR:</b> Large moves, risk/opportunity<br>
        - <b>Low ATR:</b> Stable price
        """, unsafe_allow_html=True)
        atr_fig = go.Figure()
        atr_fig.add_trace(go.Scatter(x=df["Date"], y=df["ATR"], name="ATR"))
        st.plotly_chart(atr_fig, use_container_width=True)

with st.expander("📊 Volume", expanded=False):
    if "Volume" in df.columns:
        st.markdown("Volume shows activity. Spikes may mean institutional moves or news.")
        vol_fig = go.Figure()
        vol_fig.add_trace(go.Bar(x=df["Date"], y=df["Volume"], name="Volume"))
        st.plotly_chart(vol_fig, use_container_width=True)

# === Risk Dashboard ===
st.markdown("""
## 🛡️ <span style='color:#1877c9'>Risk Dashboard</span>
""", unsafe_allow_html=True)
st.markdown("""
<div style='background-color:#f3f5fa; padding: 22px; border-radius: 12px; border: 1px solid #e1e4eb;'>
<b>Interpreting Risk Signals:</b><br>
- 🟢 <b>Bullish / Healthy</b>: Indicator shows strength or stability<br>
- 🟠 <b>Volatile / Watch</b>: Caution advised – indicator signals instability<br>
- 🔴 <b>Bearish / Risky</b>: Indicator shows weakness or negative pressure<br>
- ⚪ <b>Neutral / No Signal</b>: No actionable signal detected
</div>
""", unsafe_allow_html=True)

heatmap = stock_summary.get("heatmap_signals", {})
risk_score = stock_summary.get("composite_risk_score", None)
risk_level = stock_summary.get("risk_level", None)
if heatmap:
    st.markdown("#### 🔍 <u>Current Signal Status</u>", unsafe_allow_html=True)
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
            f"<div style='background-color:#fff;padding:10px 0 10px 0;border-radius:10px;text-align:center;font-size:1.08rem;'>"
            f"<b>{indicator}</b><br>{color} <span style='font-size:1.06rem'>{status}</span></div>",
            unsafe_allow_html=True
        )
if risk_score is not None:
    st.markdown(f"**Composite Risk Score**: `{risk_score}`")
if risk_level is not None:
    st.markdown(f"**Overall Risk Level**: 🎯 **{risk_level}**")

st.markdown("""
### How to Interpret the Composite Risk Score
The <b>Composite Risk Score</b> is a weighted calculation of technical indicators, normalized between <b>0.00 (low risk)</b> and <b>1.00 (high risk)</b>.<br>
| Score Range | What It Means         |
|-------------|------------------------|
| <b>0.00 – 0.33</b> | ✅ <b>Low Risk</b>: Signals are stable or bullish |
| <b>0.34 – 0.66</b> | ⚠️ <b>Caution</b>: Mixed signals; watch carefully |
| <b>0.67 – 1.00</b> | 🔥 <b>High Risk</b>: Multiple red flags detected |
<b>Overall Risk Level</b> is a simplified risk tag for fast decisions and investor signal intensity at a glance.
""", unsafe_allow_html=True)

st.markdown("*SMA Trend, OBV, CMF, and Stochastic signals are now integrated into the dashboard for a fuller view of risk.*")

# === Summary Layers ===
st.markdown("## 🧠 Technical Summary (Agent 1)")
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
final_text = (
    f"📌 **Stock:** {results.get('stock', {}).get('summary', '')}  \n"
    f"📊 **Sector:** {results.get('sector', {}).get('summary', '')}  \n"
    f"📈 **Market Index:** {results.get('market', {}).get('summary', '')}  \n"
    f"🛢️ **Commodities:** {results.get('commodities', {}).get('summary', '')}  \n"
    f"🌍 **Global Indices:** {results.get('globals', {}).get('summary', '')}"
)
st.success(final_text)
