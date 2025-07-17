# streamlit_ta_global.py

import streamlit as st
import os
import json
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from agents.ta_global import ta_global
from llm_utils import call_llm

st.set_page_config(page_title="Technical Analyst AI Agent", page_icon="🌍")
st.markdown("""
<h1 style='margin-bottom: 0.3em;'>Technical Analyst AI Agent 🤖<br>
- Global Macro</h1>
""", unsafe_allow_html=True)

st.markdown(
    """
    Fetches global market data, computes technical metrics, applies cross-asset regime logic, and summarizes global outlook in both pro and plain-English style.
    """
)

# --- Get latest global technical summary
with st.spinner("Loading data and performing computation..."):
    try:
        summary = ta_global()
        st.success("Fetched and computed global technical metrics.")
    except Exception as e:
        st.error(f"Error in fetching from ta_global(): {e}")
        st.stop()

# --- Load composite score history ---
history_file = "composite_score_history.csv"
hist_df = None
if os.path.exists(history_file):
    try:
        hist_df = pd.read_csv(history_file, parse_dates=["date"])
    except Exception as e:
        st.warning(f"Could not load composite score history: {e}")
else:
    st.info("No composite score history found yet.")

# === HEADLINE METRICS & LOGIC ===
as_of = summary.get("as_of", "N/A")
composite_score = summary.get("composite_score", None)
composite_label = summary.get("composite_label", None)
risk_regime = summary.get("risk_regime", "N/A")
risk_regime_rationale = summary.get("risk_regime_rationale", "")
risk_regime_score = summary.get("risk_regime_score", None)
anomaly_alerts = summary.get("anomaly_alerts", [])
correlation_matrix = summary.get("correlation_matrix", None)
out = summary.get("out", {})
breadth = summary.get("breadth", {})

# ===== HEADLINE =====
st.markdown(
    f"#### <span style='font-size:1.3em;'>Composite Market Score: <b>{composite_score if composite_score is not None else 'N/A'}</b> ({composite_label if composite_label else 'N/A'})</span><br>"
    f"<span style='font-size:1.0em;'>Risk Regime: <b>{risk_regime}</b></span>",
    unsafe_allow_html=True,
)
st.markdown(
    f"<span>As of</span> {as_of}",
    unsafe_allow_html=True
)

# === Rule-based human explanations ===
composite_score_expl = {
    "Bullish": "A 'Bullish' composite market score means that, overall, the world’s major markets are showing strong, positive signals—most trends look healthy and investors are generally optimistic.",
    "Neutral": "A 'Neutral' composite market score means markets are mixed, with no clear trend dominating. Investors are taking a wait-and-see approach, and there’s no strong push up or down.",
    "Bearish": "A 'Bearish' composite market score means the world’s major markets are showing weak or negative signals—trends are generally unhealthy and investors may be cautious or pessimistic."
}
risk_regime_expl = {
    "Bullish": "A 'Bullish' risk regime means volatility is falling and major markets are rising. Investors are confident and risk-taking is encouraged.",
    "Neutral": "A 'Neutral' risk regime means there aren’t big warning signs of danger, but there also isn’t a strong signal that it’s a super-safe time. The market isn’t panicky, but it’s not totally carefree either. it’s in a steady, watchful mode.",
    "Bearish": "A 'Bearish' risk regime means volatility is rising and major markets are falling. Investors may be nervous, and caution is warranted."
}
explanation = ""
if composite_label in composite_score_expl:
    explanation += composite_score_expl[composite_label]
if risk_regime in risk_regime_expl:
    if explanation:
        explanation += " "
    explanation += risk_regime_expl[risk_regime]
if explanation:
    st.markdown(
        f"<span style='color:gray; font-size:0.80em;'>{explanation}</span>",
        unsafe_allow_html=True
    )

if risk_regime_rationale:
    st.markdown(
        f"<span style='color:gray; font-size:0.86em;'>Risk Regime Rationale: {risk_regime_rationale}</span>",
        unsafe_allow_html=True
    )

# --- Anomaly Alerts ---
if anomaly_alerts:
    st.warning("**Smart Anomaly Alerts:**\n\n" + "\n".join(anomaly_alerts))
else:
    st.info("🕊️ No unusual market stress detected.\nMarkets appear calm and no smart anomalies were found in the latest signals.")


# --- Historical Composite Score Chart ---
if hist_df is not None and not hist_df.empty:
    st.subheader("Historical Composite Market Score")
    regime_colors = {"Bullish": "#38B2AC", "Neutral": "#ECC94B", "Bearish": "#F56565"}
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hist_df["date"], y=hist_df["composite_score"],
        mode="lines+markers",
        line=dict(color="#3182ce", width=2),
        marker=dict(size=7, color=[regime_colors.get(l, "#888") for l in hist_df["composite_label"]]),
        text=hist_df["composite_label"],
        name="Composite Score"
    ))
    fig.update_layout(
        height=280,
        margin=dict(l=0, r=0, t=30, b=0),
        yaxis=dict(title="Composite Score"),
        showlegend=False,
        template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly_white",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )
    st.plotly_chart(fig, use_container_width=True)

# --- Cross-Asset Correlation Heatmap ---
if correlation_matrix is not None:
    st.subheader("Cross-Asset Correlation Heatmap (Last 60 Days)")
    corr_df = pd.DataFrame(correlation_matrix)
    fig_corr = go.Figure(
        data=go.Heatmap(
            z=corr_df.values,
            x=corr_df.columns,
            y=corr_df.index,
            colorscale="RdBu",
            zmin=-1, zmax=1,
            colorbar=dict(title="Corr", tickvals=[-1, -0.5, 0, 0.5, 1])
        )
    )
    fig_corr.update_layout(
        height=340,
        margin=dict(l=30, r=30, t=40, b=30),
        xaxis_title="Asset",
        yaxis_title="Asset",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly_white",
    )
    st.plotly_chart(fig_corr, use_container_width=True)

# ===== ASSET CLASS GROUPED TABLES =====
def safe_fmt(val, pct=False):
    if val is None or pd.isna(val):
        return "N/A"
    if pct:
        return f"{val:+.2f}%" if isinstance(val, float) else str(val)
    return f"{val:,.2f}" if isinstance(val, float) else str(val)

def trend_icon(val):
    if val == "Uptrend":
        return "🟢 Up"
    elif val == "Downtrend":
        return "🔴 Down"
    elif val == "Sideways":
        return "🟡 Side"
    return val or "N/A"

# Group all assets by class for display
grouped = {}
for name, data in out.items():
    asset_class = data.get("class", "Other")
    grouped.setdefault(asset_class, []).append((name, data))

class_display_order = ["Index", "FX", "Bond", "Commodity", "Volatility", "Other"]

st.markdown("#### Market Overview by Asset Class")
for asset_class in class_display_order:
    assets = grouped.get(asset_class, [])
    if not assets:
        continue
    with st.expander(f"{asset_class}s ({len(assets)})", expanded=(asset_class == "Index")):
        rows = []
        cols = [
            "Name", "Last", "30D Change", "90D Change", "200D Change",
            "Trend (30D)", "Trend (90D)", "Trend (200D)", "Vol (30D)", "Vol (90D)", "Vol (200D)"
        ]
        for name, data in assets:
            if "error" in data:
                row = [name] + [data.get("error", "")] + [""] * (len(cols)-2)
            else:
                row = [
                    name,
                    safe_fmt(data.get("last", None)),
                    safe_fmt(data.get("change_30d_pct", None), pct=True),
                    safe_fmt(data.get("change_90d_pct", None), pct=True),
                    safe_fmt(data.get("change_200d_pct", None), pct=True),
                    trend_icon(data.get("trend_30d", "N/A")),
                    trend_icon(data.get("trend_90d", "N/A")),
                    trend_icon(data.get("trend_200d", "N/A")),
                    safe_fmt(data.get("vol_30d", None)),
                    safe_fmt(data.get("vol_90d", None)),
                    safe_fmt(data.get("vol_200d", None)),
                ]
            rows.append(row)
        df = pd.DataFrame(rows, columns=cols)
        # --- Ensure "Name" is a column, not the index, and is first
        if 'Name' not in df.columns:
            df = df.reset_index()
        df = df.reset_index(drop=True)
        curr_cols = df.columns.tolist()
        if curr_cols[0] != 'Name':
            curr_cols.remove('Name')
            df = df[['Name'] + curr_cols]
        st.dataframe(df, hide_index=True)

st.caption("Assets are grouped by class. Note: Some tickers may not have reliable data (e.g. certain bonds/volatility indices on Yahoo).")

# --- LLM Summaries and Explanation ---
st.subheader("AI-Agent Summaries")
json_summary = json.dumps(summary, indent=2)

if st.button("Generate Report", type="primary"):
    with st.spinner("Querying LLM..."):
        try:
            llm_output = call_llm("global", json_summary, prompt_vars={
                "composite_label": composite_label or "",
                "risk_regime": risk_regime or "",
            })
            st.session_state["llm_global_summary"] = llm_output
            # Split the LLM output into sections
            sections = {"Technical Summary": "", "Plain-English Summary": "", "Explanation": ""}
            current_section = None
            for line in llm_output.splitlines():
                line_strip = line.strip()
                if line_strip.startswith("Technical Summary"):
                    current_section = "Technical Summary"
                elif line_strip.startswith("Plain-English Summary"):
                    current_section = "Plain-English Summary"
                elif line_strip.startswith("Explanation"):
                    current_section = "Explanation"
                elif current_section and line_strip:
                    sections[current_section] += line + "\n"
            if sections["Technical Summary"]:
                st.markdown("**Technical Summary**")
                st.info(sections["Technical Summary"].strip())
            if sections["Plain-English Summary"]:
                st.markdown("**Plain-English Summary**")
                st.success(sections["Plain-English Summary"].strip())
            if sections["Explanation"]:
                st.markdown("<span style='font-size:1.07em;font-weight:600;'>Why Composite Score is <b>{}</b> and Regime is <b>{}</b>?</span>".format(
                    composite_label, risk_regime
                ), unsafe_allow_html=True)
                st.warning(sections["Explanation"].strip())
        except Exception as e:
            st.error(f"LLM error: {e}")

st.caption("Note: AI generated content can be incorrect or misleading.")

# --- Raw Data Section
st.subheader("Raw Global Technical Data")
with st.expander("Show raw summary dict", expanded=False):
    st.json(summary)

# --- Chart section helper ---
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
                mode='lines', name='SMA 200', line=dict(dash='longdash')
            ))
            if volume_col and volume_col in df.columns:
                fig.add_trace(go.Bar(
                    x=df[date_col], y=df[volume_col],
                    name="Volume", yaxis="y2",
                    marker_color="rgba(0,160,255,0.16)",
                    opacity=0.5
                ))
            fig.update_layout(
                # === title=label,
                xaxis_title="Date",
                yaxis_title="Price",
                yaxis=dict(title="Price", showgrid=True),
                yaxis2=dict(
                    title="Volume", overlaying='y', side='right', showgrid=False, rangemode='tozero'
                ),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                template="plotly_white",
                height=350,
                bargap=0,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
            )
            st.plotly_chart(fig, use_container_width=True)
            table_windows = [20, 50, 200]
            table_rows = []
            for win in table_windows:
                pct, latest, trend = calc_trend_info(df, date_col, close_col, window=win)
                table_rows.append({
                    "Window": f"{win}d",
                    "% Change": pct,
                    "Latest": latest,
                    "Trend": trend_icon(trend)
                })
            table_df = pd.DataFrame(table_rows)
            st.markdown("**Trend Table**")
            st.dataframe(table_df, hide_index=True)
        except Exception as e:
            st.info(f"{label} chart failed to load: {e}")

chart_list = [
    {
        "ticker": "^GSPC",
        "label": "S&P 500 (Last 6 Months)",
        "explanation": "The S&P 500 is a broad-based index representing large-cap US equities across economic sectors. Analysts study it to assess overall US market health and risk sentiment."
    },
    {
        "ticker": "^VIX",
        "label": "VIX (Volatility Index)",
        "explanation": "The VIX reflects expected US stock market volatility (fear/greed). A rising VIX signals heightened investor anxiety."
    },
    {
        "ticker": "^IXIC",
        "label": "Nasdaq Composite",
        "explanation": "Tracks over 3,000 technology and growth-oriented companies. Used to monitor tech sector momentum and risk appetite."
    },
    {
        "ticker": "^STOXX50E",
        "label": "EuroStoxx 50",
        "explanation": "Major European blue-chip index, often a proxy for Eurozone market health and capital flows."
    },
    {
        "ticker": "^N225",
        "label": "Nikkei 225",
        "explanation": "The benchmark for Japanese equities and an indicator of Asia-Pacific risk trends."
    },
    {
        "ticker": "^HSI",
        "label": "Hang Seng Index",
        "explanation": "The Hang Seng represents the Hong Kong equity market and is closely watched for signs of China/Asia sentiment shifts."
    },
    {
        "ticker": "^FTSE",
        "label": "FTSE 100",
        "explanation": "The FTSE 100 is the primary UK equity index, tracking the largest London-listed companies and reflecting European market trends."
    },
    {
        "ticker": "^TNX",
        "label": "US 10-Year Treasury Yield",
        "explanation": "The 10-year yield is a global benchmark for interest rates, influencing borrowing costs and risk assets worldwide."
    },
    {
        "ticker": "^IRX",
        "label": "US 2-Year Treasury Yield",
        "explanation": "Short-term US government bond yield. Rising 2-year yields can signal shifting Fed policy expectations."
    },
    {
        "ticker": "DX-Y.NYB",
        "label": "US Dollar Index (DXY)",
        "explanation": "DXY measures the US dollar's strength against a basket of major currencies. It affects global trade and capital flows."
    },
    {
        "ticker": "USDSGD=X",
        "label": "USD/SGD FX Rate",
        "explanation": "The USD/SGD exchange rate is closely monitored as an indicator of Singapore’s economic health and regional capital flows."
    },
    {
        "ticker": "JPY=X",
        "label": "USD/JPY FX Rate",
        "explanation": "Tracks the US dollar against the Japanese yen. Used to gauge risk sentiment and monetary policy trends in Asia."
    },
    {
        "ticker": "EURUSD=X",
        "label": "EUR/USD FX Rate",
        "explanation": "The EUR/USD rate is the world's most traded FX pair, serving as a barometer of global macro and policy divergence."
    },
    {
        "ticker": "USDCNH=X",
        "label": "USD/CNH FX Rate",
        "explanation": "Reflects the offshore yuan versus the US dollar. A gauge of global investor sentiment towards China."
    },
    {
        "ticker": "GC=F",
        "label": "Gold Futures",
        "explanation": "Gold is a traditional safe-haven asset. Its price movement signals inflation and global risk sentiment."
    },
    {
        "ticker": "BZ=F",
        "label": "Brent Crude Oil",
        "explanation": "Brent is the world’s key oil price benchmark. It affects inflation, trade balances, and energy markets."
    },
    {
        "ticker": "CL=F",
        "label": "WTI Crude Oil",
        "explanation": "WTI is the US oil benchmark, important for tracking energy prices and economic activity."
    },
    {
        "ticker": "HG=F",
        "label": "Copper Futures",
        "explanation": "Copper is an industrial bellwether, used to assess the strength of global manufacturing and economic growth."
    },
]

# --- Plot all charts ---
st.subheader("Global Market Charts")
for chart in chart_list:
    plot_chart(chart["ticker"], chart["label"], chart["explanation"])

# ---- End ----

# ---- End ----

