import streamlit as st
import os
import json
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go

from agents.ta_global import ta_global
from agents.ta_market import ta_market
from llm_utils import call_llm

st.set_page_config(page_title="AI Macro & Market Technical Analyst", page_icon="🌍")
st.title("🌍 AI Macro & Market Technical Analyst Demo")
st.caption(f"Streamlit version: {st.__version__}")

st.markdown("""
This dashboard fetches global and sector/market data, computes technical metrics, applies cross-asset regime logic, and can summarize outlooks in both pro and plain-English style.
""")

# ---- TABS ----
tabs = st.tabs(["Market", "Global"])

# --- Tab 1: Market ---
with tabs[0]:
    st.header("Market / Sector Technical Dashboard")

    # --- Fetch market/sector/factor summary
    with st.spinner("Loading market/sector/factor technicals..."):
        try:
            mkt_summary = ta_market()
            st.success("Fetched and computed market/sector technical metrics.")
        except Exception as e:
            st.error(f"Error in ta_market(): {e}")
            st.stop()

    mkt_out = mkt_summary["out"]
    mkt_as_of = mkt_summary["as_of"]
    mkt_breadth = mkt_summary["breadth_30d_pct"]
    mkt_rel_perf = mkt_summary["rel_perf_30d"]

    st.markdown(f"**As of:** {mkt_as_of} &nbsp;|&nbsp; **% Baskets in Uptrend (30d):** {mkt_breadth}%")

    # --- Trend Table ---
    cols = [
        "Name", "Last", "30D Change", "90D Change", "200D Change",
        "Trend (30D)", "Trend (90D)", "Trend (200D)", "Vol (30D)", "Vol (90D)", "Vol (200D)", "Rel. Perf vs S&P500 (30D)"
    ]
    rows = []
    for name, data in mkt_out.items():
        if "error" in data:
            row = [name, data.get("error", "")] + [""] * (len(cols)-2)
        else:
            rel_perf = f"{mkt_rel_perf.get(name, 0):+.2f}%" if name in mkt_rel_perf else "N/A"
            row = [
                name,
                f"{data.get('last', 'N/A'):,}" if data.get("last", None) else "N/A",
                f"{data.get('change_30d_pct', 0):+.2f}%" if data.get("change_30d_pct", None) is not None else "N/A",
                f"{data.get('change_90d_pct', 0):+.2f}%" if data.get("change_90d_pct", None) is not None else "N/A",
                f"{data.get('change_200d_pct', 0):+.2f}%" if data.get("change_200d_pct", None) is not None else "N/A",
                data.get("trend_30d", "N/A"),
                data.get("trend_90d", "N/A"),
                data.get("trend_200d", "N/A"),
                f"{data.get('vol_30d', 0):,.2f}" if data.get("vol_30d", None) is not None else "N/A",
                f"{data.get('vol_90d', 0):,.2f}" if data.get("vol_90d", None) is not None else "N/A",
                f"{data.get('vol_200d', 0):,.2f}" if data.get("vol_200d", None) is not None else "N/A",
                rel_perf,
            ]
        rows.append(row)
    mkt_df = pd.DataFrame(rows, columns=cols)
    st.dataframe(mkt_df, hide_index=True)

    # --- Relative Rotation (bar chart) ---
    if mkt_rel_perf:
        st.markdown("**Relative Outperformance vs S&P 500 (Last 30D)**")
        rel_perf_df = pd.DataFrame(list(mkt_rel_perf.items()), columns=["Name", "Relative Perf (30D, %)"])
        rel_perf_df = rel_perf_df.sort_values("Relative Perf (30D, %)", ascending=False)
        fig_rel = go.Figure(go.Bar(
            x=rel_perf_df["Name"],
            y=rel_perf_df["Relative Perf (30D, %)"],
            marker_color=["#38B2AC" if v >= 0 else "#F56565" for v in rel_perf_df["Relative Perf (30D, %)"]]
        ))
        fig_rel.update_layout(
            yaxis_title="Outperformance vs S&P500 (%)",
            margin=dict(l=30, r=30, t=30, b=40),
            height=320,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            template="plotly_white",
        )
        st.plotly_chart(fig_rel, use_container_width=True)

    st.caption("Baskets include global indices, US sectors, value/growth/smallcap, bonds, gold, oil. Relative performance is versus S&P500.")

# --- Tab 2: Global ---
with tabs[1]:
    st.header("Global Macro Technical Dashboard")

    # --- Existing GLOBAL tab logic, unchanged from your latest code ---

    # --- Get latest global technical summary
    with st.spinner("Loading global technical summary..."):
        try:
            summary = ta_global()
            st.success("Fetched and computed global technical metrics.")
        except Exception as e:
            st.error(f"Error in ta_global(): {e}")
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
        f"#### <span style='font-size:1.3em;'>Composite Market Score: <b>{composite_score if composite_score is not None else 'N/A'}</b> ({composite_label if composite_label else 'N/A'})</span>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<span style='font-weight:600;'>Risk Regime:</span> {risk_regime}  |  <span style='font-weight:600;'>As of:</span> {as_of}",
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
        "Neutral": "A 'Neutral' risk regime means there aren’t big warning signs of danger, but there also isn’t a strong signal that it’s a super-safe time. The market isn’t panicky, but it’s not totally carefree either—it’s in a steady, watchful mode.",
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
    # ... (keep your existing group-by-class and asset table logic unchanged) ...

    # --- The rest of your GLOBAL logic follows here, as in your last version ---

# ---- End ----


# ---- End ----







