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

def render_global_tab():
    st.header("Global Macro Technical Dashboard")

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

    def highlight_trend(val):
        base = (
            "display:inline-block;"
            "padding: 2px 10px;"
            "border-radius: 12px;"
            "margin: 2px auto;"
            "min-width: 80px;"
            "text-align:center;"
        )
        if val == "Uptrend":
            return base + "background-color: #38B2AC; color: #fff; font-weight: 600;"
        elif val == "Downtrend":
            return base + "background-color: #F56565; color: #fff; font-weight: 600;"
        elif val == "Sideways":
            return base + "background-color: #ECC94B; color: #333; font-weight: 600;"
        return ""

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
    st.subheader("LLM-Generated Summaries")
    json_summary = json.dumps(summary, indent=2)

    if st.button("Generate LLM Global Summaries", type="primary"):
        with st.spinner("Querying LLM..."):
            try:
                llm_output = call_llm("global", json_summary, prompt_vars={
                    "composite_label": composite_label or "",
                    "risk_regime": risk_regime or "",
                })
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
                    st.markdown("<span style='font-size:1.07em;font-weight:600;'>LLM Explanation (Why <b>{}</b> / Regime: <b>{}</b>?):</span>".format(
                        composite_label, risk_regime
                    ), unsafe_allow_html=True)
                    st.warning(sections["Explanation"].strip())
            except Exception as e:
                st.error(f"LLM error: {e}")

    st.caption("If you do not see the summaries, check the console logs for LLM errors or ensure your OpenAI API key is correctly set.")

    # --- Raw Data Section
    st.subheader("Raw Global Technical Data")
    with st.expander("Show raw summary dict", expanded=False):
        st.json(summary)
