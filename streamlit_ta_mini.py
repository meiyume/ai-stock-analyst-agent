# streamlit_ta_market.py

import streamlit as st
import os
import json
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
from agents.ta_market import ta_market
from llm_utils import call_llm
from datetime import datetime, timedelta

def render_market_tab():
    st.markdown("""
    <h1 style='margin-bottom: 0.3em;'>Technical Analyst AI Agent 🤖<br>
    - Regional Markets</h1>
    """, unsafe_allow_html=True)

    st.markdown(
        """
        Analyzes key Singapore and Asia equity, FX and commodity indices, computes market breath, regime, 
        anormalies, cross-asset risk and summarizes outlook in both pro and plain-English style.
        """
    )

    # --- Fetch market technical summary
    with st.spinner("Loading data and performing computation..."):
        try:
            summary = ta_market()
            st.success("Fetched and computed market technical metrics.")
        except Exception as e:
            st.error(f"Error in ta_market(): {e}")
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

    # === HEADLINE METRICS ===
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
    rel_perf_30d = summary.get("rel_perf_30d", {})
    alerts = summary.get("alerts", [])

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
    
    # Rule-based explanations
    composite_score_expl = {
        "Bullish": "‘Bullish’ = Most Singapore/Asia market signals are strong, risk appetite is high, and uptrends dominate.",
        "Neutral": "‘Neutral’ = Markets are mixed or sideways, no clear winner. Wait-and-see mode.",
        "Bearish": "‘Bearish’ = Signals are weak or negative, defensive strategies favored, watch for downside risk."
    }
    if composite_label in composite_score_expl:
        st.markdown(
            f"<span style='color:gray; font-size:0.90em;'>{composite_score_expl[composite_label]}</span>",
            unsafe_allow_html=True
        )
    if risk_regime_rationale:
        st.markdown(
            f"<span style='color:gray; font-size:0.88em;'>Risk Regime Rationale: {risk_regime_rationale}</span>",
            unsafe_allow_html=True
        )

    # --- Smart Anomaly Alerts ---
    if anomaly_alerts:
        st.warning("**Smart Anomaly Alerts:**\n\n" + "\n".join(anomaly_alerts))
    elif alerts:
        st.warning("**Additional Alerts:**\n\n" + "\n".join(alerts))
    else:
        st.info("🕊️ No unusual market stress detected.\nMarkets appear calm and no smart anomalies were found.")

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
            template="plotly_white",
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
            template="plotly_white",
        )
        st.plotly_chart(fig_corr, use_container_width=True)

    # ===== Basket Overview Table =====
    st.markdown("#### Market Baskets Overview")
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
    # Market basket = by default show all tickers as a table (or grouped if you wish)
    rows = []
    cols = [
        "Name", "Last", "30D Change", "90D Change", "200D Change",
        "Trend (30D)", "Trend (90D)", "Trend (200D)",
        "Vol (30D)", "Vol (90D)", "Vol (200D)", "Alerts"
    ]
    for name, data in out.items():
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
                data.get("alerts", "")
            ]
        rows.append(row)
    df = pd.DataFrame(rows, columns=cols)
    st.dataframe(df, hide_index=True)

    # --- Relative Outperformance vs S&P 500 (30D) ---
    if rel_perf_30d:
        rel_df = pd.DataFrame(list(rel_perf_30d.items()), columns=["Name", "Relative Outperf (%)"])
        rel_df = rel_df.sort_values("Relative Outperf (%)", ascending=False)
    
        # Pastel green to pastel red (custom)
        pastel_scale = [
            [0.0, "#F7B6B6"],   # pastel red
            [0.5, "#F7F6E7"],   # very light neutral
            [1.0, "#B6E2D3"],   # pastel green
        ]
    
        fig = px.bar(
            rel_df,
            x="Name",
            y="Relative Outperf (%)",
            color="Relative Outperf (%)",
            color_continuous_scale=pastel_scale,
            height=400,
            labels={"Relative Outperf (%)": "Relative Outperformance (%)"},
            title=None,
        )
        fig.update_layout(
            yaxis_title="Relative Outperformance (%) vs S&P 500",
            xaxis_title=None,
            coloraxis_showscale=False,
            margin=dict(l=0, r=0, t=30, b=0),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Not enough data to compute relative outperformance.")

    # --- LLM Summaries Section ---
    st.subheader("AI-Agent Summaries")
    summary_for_llm = {k: v for k, v in summary.items() if k != "out"}  # Do not send "out"
    
    for k, v in summary_for_llm.items():
        try:
            json.dumps({k: v})
        except Exception as e:
            st.write(f"Key {k} failed to serialize: {e} (type={type(v)})")

    
    json_summary = json.dumps(summary_for_llm, indent=2)
    if st.button("Generate Report", type="primary"):
        with st.spinner("Querying LLM..."):
            try:
                llm_output = call_llm("market", json_summary, prompt_vars={
                    "composite_label": composite_label or "",
                    "risk_regime": risk_regime or "",
                })
                st.session_state["llm_market_summary"] = llm_output
                # Split into sections (robust, use headings if present)
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
                    st.markdown("<span style='font-size:1.07em;font-weight:600;'>Why Composite Score is <b>{}</b> and Regime: <b>{}</b>?</span>".format(
                        composite_label, risk_regime
                    ), unsafe_allow_html=True)
                    st.warning(sections["Explanation"].strip())
            except Exception as e:
                st.error(f"LLM error: {e}")

    st.caption("Note: AI generated content can be incorrect or misleading.")

    # --- Raw Data Section
    st.subheader("Raw Market Technical Data")
    with st.expander("Show raw summary dict", expanded=False):
        st.json(summary)

# If using as main app file
if __name__ == "__main__":
    st.set_page_config(page_title="Market Dashboard", page_icon="🏢", layout="wide")
    render_market_tab()
