import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import yfinance as yf
from agents.ta_global import ta_global

st.set_page_config(page_title="AI Global Technical Analyst", page_icon="🌍")
st.title("🌍 AI Global Macro Technical Analyst")

# === Get global TA summary ===
with st.spinner("Loading global technical summary..."):
    summary = ta_global()

as_of = summary.get("as_of", "N/A")
composite_score = summary.get("composite_score", None)
composite_label = summary.get("composite_label", None)
risk_regime = summary.get("risk_regime", "N/A")
out = summary.get("out", {})
breadth = summary.get("breadth", {})

# ===== HEADLINE =====
st.markdown(
    f"#### <span style='font-size:1.3em;'>Composite Market Score: <b>{composite_score if composite_score is not None else 'N/A'}</b> ({composite_label if composite_label else 'N/A'})</span>",
    unsafe_allow_html=True,
)
st.caption(f"**Risk Regime:** {risk_regime}  |  <b>As of:</b> {as_of}")

# ===== TABLE WITH BOTH PER-INDEX & BREADTH =====

# Define indices and ticker mapping
major_indices = ["S&P500", "Nasdaq", "EuroStoxx50", "Nikkei", "HangSeng", "FTSE100"]
ticker_map = {
    "S&P500": "^GSPC", "Nasdaq": "^IXIC", "EuroStoxx50": "^STOXX50E", 
    "Nikkei": "^N225", "HangSeng": "^HSI", "FTSE100": "^FTSE"
}

def color_trend(trend):
    if trend == "Uptrend":
        return "background-color: #156f2c; color: #fff;"  # strong green
    elif trend == "Downtrend":
        return "background-color: #8b2323; color: #fff;"  # strong red
    elif trend == "Sideways":
        return "background-color: #786300; color: #fff;"  # gold
    else:
        return ""

def color_ma(flag):
    return ""  # No highlight for tick/cross

def safe_fmt(val, pct=False):
    if val is None or pd.isna(val):
        return "N/A"
    if pct:
        return f"{val:+.2f}%" if isinstance(val, float) else str(val)
    return f"{val:,.2f}" if isinstance(val, float) else str(val)

# Efficiently batch-fetch index price data for MA checks
st.markdown("##### Global Market Overview Table")

# Cache the download for fast reruns
@st.cache_data(show_spinner=False, max_entries=12, ttl=600)
def fetch_index_data(ticker):
    end = datetime.today()
    start = end - timedelta(days=400)
    df = yf.download(ticker, start=start, end=end, interval="1d", auto_adjust=True, progress=False)
    close = df["Close"].dropna()
    if isinstance(close, pd.DataFrame):
        close = close.squeeze()
    return close

overview_rows = []
for idx in major_indices:
    data = out.get(idx, {})
    try:
        ticker = ticker_map[idx]
        close = fetch_index_data(ticker)
        last = close.iloc[-1] if len(close) > 0 else np.nan
        ma50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else np.nan
        ma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else np.nan
        above_50d = "✅" if not pd.isna(last) and not pd.isna(ma50) and last > ma50 else "❌"
        above_200d = "✅" if not pd.isna(last) and not pd.isna(ma200) and last > ma200 else "❌"
    except Exception:
        last, above_50d, above_200d = np.nan, "N/A", "N/A"
    overview_rows.append({
        "Index": idx,
        "Last": safe_fmt(last),
        "30D Change": safe_fmt(data.get("change_30d_pct", None), pct=True),
        "Trend (30D)": data.get("trend_30d", "N/A"),
        "Above 50D MA": above_50d,
        "Above 200D MA": above_200d,
    })

# VIX row
vix = out.get("VIX", {})
try:
    vix_close = fetch_index_data("^VIX")
    vix_last = vix_close.iloc[-1] if len(vix_close) > 0 else np.nan
except Exception:
    vix_last = np.nan

overview_rows.append({
    "Index": "VIX",
    "Last": safe_fmt(vix_last),
    "30D Change": safe_fmt(vix.get("change_30d_pct", None), pct=True),
    "Trend (30D)": vix.get("trend_30d", "N/A"),
    "Above 50D MA": "N/A",
    "Above 200D MA": "N/A",
})

# Breadth row (%)
overview_rows.append({
    "Index": "Breadth",
    "Last": "",
    "30D Change": "",
    "Trend (30D)": "",
    "Above 50D MA": f"{breadth.get('breadth_above_50dma_pct','N/A')}%",
    "Above 200D MA": f"{breadth.get('breadth_above_200dma_pct','N/A')}%",
})

overview_df = pd.DataFrame(overview_rows)

def style_overview(df):
    styled = df.style
    if "Trend (30D)" in df.columns:
        styled = styled.applymap(color_trend, subset=["Trend (30D)"])
    if "Above 50D MA" in df.columns:
        styled = styled.applymap(color_ma, subset=["Above 50D MA"])
    if "Above 200D MA" in df.columns:
        styled = styled.applymap(color_ma, subset=["Above 200D MA"])
    return styled

st.write(style_overview(overview_df), unsafe_allow_html=True)
st.caption("Green = bullish, Red = bearish, Yellow = neutral/sideways. Breadth: % of indices above moving average.")

# Optional: Show raw data for debugging
with st.expander("Show raw summary dict", expanded=False):
    st.json(summary)

# ---- End ----







