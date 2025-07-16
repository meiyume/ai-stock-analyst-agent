import streamlit as st
import json
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from agents.ta_global import ta_global
from llm_utils import call_llm

st.set_page_config(page_title="AI Global Technical Macro Analyst", page_icon="🌍")
st.title("🌍 AI Global Macro Technical Analyst Demo")

st.markdown(
    """
    This demo fetches global market data, computes technical metrics, and asks the LLM to summarize the global technical outlook
    in both a professional (analyst) and plain-English (executive) format.
    """
)

# --- Get latest global technical summary
with st.spinner("Loading global technical summary..."):
    try:
        summary = ta_global()
        st.success("Fetched and computed global technical metrics.")
    except Exception as e:
        st.error(f"Error in ta_global(): {e}")
        st.stop()

# ======= COMPOSITE SCORE AND OVERVIEW TABLE AT TOP =======

# --- Headline Composite Score ---
composite_score = summary.get("composite_score", None)
composite_label = summary.get("composite_label", None)
risk_regime = summary.get("risk_regime", "N/A")
as_of = summary.get("as_of", "N/A")

st.markdown(f"#### <span style='font-size:1.3em;'>Composite Market Score: <b>{composite_score if composite_score is not None else 'N/A'}</b> ({composite_label if composite_label else 'N/A'})</span>", unsafe_allow_html=True)
st.caption(f"**Risk Regime:** {risk_regime} &nbsp; | &nbsp; <b>As of:</b> {as_of}")

# --- Overview Table (Major Indices, VIX, Breadth) ---
out = summary.get("out", {})
breadth = summary.get("breadth", {})
lookbacks = summary.get("lookbacks", [30, 90, 200])

def color_trend(trend):
    if trend == "Uptrend":
        return "background-color:#c6f5d4;"  # green
    elif trend == "Downtrend":
        return "background-color:#f7c6c6;"  # red
    elif trend == "Sideways":
        return "background-color:#f5f2c6;"  # yellow
    else:
        return ""

def color_ma(flag):
    if flag == "✅":
        return "background-color:#c6f5d4;"  # green
    elif flag == "❌":
        return "background-color:#f7c6c6;"  # red
    else:
        return ""

def get_ma_flag(last, ma):
    if pd.isna(last) or pd.isna(ma):
        return "N/A"
    return "✅" if last > ma else "❌"

def safe_fmt(val, pct=False):
    if val is None or pd.isna(val):
        return "N/A"
    if pct:
        return f"{val:+.2f}%" if isinstance(val, float) else str(val)
    return f"{val:,.2f}" if isinstance(val, float) else str(val)

# Prepare overview rows
overview_rows = []
major_indices = ["S&P500", "Nasdaq", "EuroStoxx50", "Nikkei", "HangSeng", "FTSE100"]
for idx in major_indices:
    data = out.get(idx, {})
    # For MAs, refetch here to get up-to-date values for display
    try:
        ticker = {
            "S&P500": "^GSPC", "Nasdaq": "^IXIC", "EuroStoxx50": "^STOXX50E", 
            "Nikkei": "^N225", "HangSeng": "^HSI", "FTSE100": "^FTSE"
        }[idx]
        end = datetime.today()
        start = end - timedelta(days=400)
        df = yf.download(ticker, start=start, end=end, interval="1d", auto_adjust=True, progress=False)
        close = df["Close"].dropna()
        last = close.iloc[-1] if len(close) > 0 else np.nan
        ma50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else np.nan
        ma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else np.nan
        above_50d = get_ma_flag(last, ma50)
        above_200d = get_ma_flag(last, ma200)
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

# Add VIX row
vix = out.get("VIX", {})
overview_rows.append({
    "Index": "VIX",
    "Last": safe_fmt(vix.get("last", None)),
    "30D Change": safe_fmt(vix.get("change_30d_pct", None), pct=True),
    "Trend (30D)": vix.get("trend_30d", "N/A"),
    "Above 50D MA": "N/A",
    "Above 200D MA": "N/A",
})

# Add breadth row
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
    # Colorize trend and MA columns for heatmap effect
    styled = df.style
    if "Trend (30D)" in df.columns:
        styled = styled.applymap(color_trend, subset=["Trend (30D)"])
    if "Above 50D MA" in df.columns:
        styled = styled.applymap(color_ma, subset=["Above 50D MA"])
    if "Above 200D MA" in df.columns:
        styled = styled.applymap(color_ma, subset=["Above 200D MA"])
    return styled

st.subheader("Global Market Overview Table")
st.write(style_overview(overview_df), unsafe_allow_html=True)
st.caption("Green = bullish, Red = bearish, Yellow = neutral/sideways. Breadth: % of indices above moving average.")

# ========== LLM Summaries ==========
st.subheader("LLM-Generated Summaries")
json_summary = json.dumps(summary, indent=2)

if st.button("Generate LLM Global Summaries", type="primary"):
    with st.spinner("Querying LLM..."):
        try:
            llm_output = call_llm("global", json_summary)
            if "Technical Summary" in llm_output and "Plain-English Summary" in llm_output:
                tech = llm_output.split("Plain-English Summary")[0].replace("Technical Summary", "").strip()
                plain = llm_output.split("Plain-English Summary")[1].strip()
                st.markdown("**Technical Summary**")
                st.info(tech)
                st.markdown("**Plain-English Summary**")
                st.success(plain)
            else:
                st.warning("LLM output did not match expected template. Full output below:")
                st.code(llm_output)
        except Exception as e:
            st.error(f"LLM error: {e}")

st.caption("If you do not see the summaries, check the console logs for LLM errors or ensure your OpenAI API key is correctly set.")

# ========== RAW DATA SECTION ==========
st.subheader("Raw Global Technical Data")
with st.expander("Show raw summary dict", expanded=False):
    st.json(summary)

# ========== CHARTS ==========
def find_col(possibles, columns):
    for p in possibles:
        for c in columns:
            if p in str(c).lower():
                return c
    return None

def calc_trend_info(df, date_col, close_col, window=50):
    """Returns percentage change, latest price, and trend direction for given window."""
    if close_col not in df.columns or len(df) < window + 1:
        return "N/A", "N/A", "N/A"
    window_df = df.tail(window)
    if window_df[close_col].isnull().all():
        return "N/A", "N/A", "N/A"
    start = window_df[close_col].iloc[0]
    end = window_df[close_col].iloc[-1]
    if pd.isna(start) or pd.isna(end):
        return "N/A", "N/A", "N/A"
    pct = 100 * (end - start) / start if start != 0 else 0
    trend = "Uptrend" if end > start else "Downtrend" if end < start else "Flat"
    latest = f"{end:,.2f}"
    return f"{pct:+.2f}%", latest, trend

def plot_chart(ticker, label, explanation):
    with st.container():
        st.markdown(f"#### {label}")
        st.caption(explanation)
        try:
            end = datetime.today()
            start = end - timedelta(days=400)
            df = yf.download(ticker, start=start, end=end, interval="1d", auto_adjust=True, progress=False)
            if df is None or len(df) < 10:
                st.info(f"Not enough {label} data to plot.")
                return

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = ['_'.join([str(i) for i in col if i]) for col in df.columns.values]
            df = df.reset_index()

            date_col = find_col(['date', 'datetime', 'index'], df.columns) or df.columns[0]
            close_col = find_col(['close'], df.columns)
            volume_col = find_col(['volume'], df.columns)

            if not date_col or not close_col:
                st.info(f"{label} chart failed to load: columns found: {list(df.columns)}")
                return

            df = df.dropna(subset=[date_col, close_col])
            if len(df) < 10:
                st.info(f"Not enough {label} data to plot.")
                return

            df["SMA20"] = df[close_col].rolling(window=20).mean()
            df["SMA50"] = df[close_col].rolling(window=50).mean()
            df["SMA200"] = df[close_col].rolling(window=200).mean()

            if len(df) > 180:
                df = df.iloc[-180:].copy()

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df[date_col], y=df[close_col],
                mode='lines', name=label
            ))
            fig.add_trace(go.Scatter(
                x=df[date_col], y=df["SMA20"],
                mode='lines', name='SMA 20', line=dict(dash='dot')
            ))
            fig.add_trace(go.Scatter(
                x=df[date_col], y=df["SMA50"],
                mode='lines', name='SMA 50', line=dict(dash='dash')
            ))
            fig.add_trace(go.Scatter(
                x=df[date_col], y=df["SMA200"],
                mode='lines', name='SMA 200', line=dict(dash='solid', color='black')
            ))
            if volume_col and volume_col in df.columns:
                fig.add_trace(go.Bar(
                    x=df[date_col], y=df[volume_col],
                    name="Volume", yaxis="y2",
                    marker_color="rgba(0,160,255,0.16)",
                    opacity=0.5
                ))

            fig.update_layout(
                title=label,
                xaxis_title="Date",
                yaxis_title="Price",
                yaxis=dict(title="Price", showgrid=True),
                yaxis2=dict(
                    title="Volume", overlaying='y', side='right', showgrid=False, rangemode='tozero'
                ),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                template="plotly_white",
                height=350,
                bargap=0
            )

            st.plotly_chart(fig, use_container_width=True)

            # --- Trend Table (20d, 50d, 200d) ---
            table_windows = [20, 50, 200]
            table_rows = []
            for win in table_windows:
                pct, latest, trend = calc_trend_info(df, date_col, close_col, window=win)
                table_rows.append({
                    "Window": f"{win}d",
                    "% Change": pct,
                    "Latest": latest,
                    "Trend": trend
                })
            table_df = pd.DataFrame(table_rows)
            st.markdown("**Trend Table**")
            st.table(table_df)

        except Exception as e:
            st.info(f"{label} chart failed to load: {e}")

# --- Chart definitions and explanations ---
chart_list = [
    {"ticker": "^GSPC", "label": "S&P 500 (Last 6 Months)", "explanation": "..."},
    {"ticker": "^VIX", "label": "VIX (Volatility Index)", "explanation": "..."},
    {"ticker": "^IXIC", "label": "Nasdaq Composite", "explanation": "..."},
    {"ticker": "^STOXX50E", "label": "EuroStoxx 50", "explanation": "..."},
    {"ticker": "^N225", "label": "Nikkei 225", "explanation": "..."},
    {"ticker": "^HSI", "label": "Hang Seng Index", "explanation": "..."},
    {"ticker": "^FTSE", "label": "FTSE 100", "explanation": "..."},
    {"ticker": "^TNX", "label": "US 10-Year Treasury Yield", "explanation": "..."},
    {"ticker": "^IRX", "label": "US 2-Year Treasury Yield", "explanation": "..."},
    {"ticker": "DX-Y.NYB", "label": "US Dollar Index (DXY)", "explanation": "..."},
    {"ticker": "USDSGD=X", "label": "USD/SGD FX Rate", "explanation": "..."},
    {"ticker": "JPY=X", "label": "USD/JPY FX Rate", "explanation": "..."},
    {"ticker": "EURUSD=X", "label": "EUR/USD FX Rate", "explanation": "..."},
    {"ticker": "USDCNH=X", "label": "USD/CNH FX Rate", "explanation": "..."},
    {"ticker": "GC=F", "label": "Gold Futures", "explanation": "..."},
    {"ticker": "BZ=F", "label": "Brent Crude Oil", "explanation": "..."},
    {"ticker": "CL=F", "label": "WTI Crude Oil", "explanation": "..."},
    {"ticker": "HG=F", "label": "Copper Futures", "explanation": "..."},
]

st.subheader("Global Market Charts")
for chart in chart_list:
    plot_chart(chart["ticker"], chart["label"], chart["explanation"])

# ---- End ----







