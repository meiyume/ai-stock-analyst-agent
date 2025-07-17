# streamlit_ta_market.py

import streamlit as st
import os
import json
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go

from agents.ta_market import ta_market
from data_utils import fetch_clean_yfinance
from llm_utils import call_llm

def safe_json(obj):
    import pandas as pd
    import numpy as np
    if isinstance(obj, dict):
        return {k: safe_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [safe_json(i) for i in obj]
    elif isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient="records")
    elif isinstance(obj, pd.Series):
        return obj.tolist()
    elif isinstance(obj, (pd.Timestamp, np.datetime64)):
        return str(obj)
    elif isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    else:
        return obj
        
def render_market_tab():
    st.header("🏢 AI Singapore/Asia Market Technical Dashboard")

    st.caption(f"Streamlit version: {st.__version__}")

    st.markdown(
        """
        This dashboard analyzes key Singapore & Asia equity, FX, and commodity indices, computes market breadth, regime, anomalies, cross-asset risk, and summarizes outlook via LLM.
        """
    )

    # --- Fetch market technical summary
    with st.spinner("Loading market technical summary..."):
        try:
            summary = ta_market()
            st.success("Fetched and computed market technical metrics.")
        except Exception as e:
            st.error(f"Error in ta_market(): {e}")
            st.stop()

    # --- Load historical composite score for market ---
    hist_df = summary.get("composite_score_history")
    if hist_df is not None and not hist_df.empty:
        hist_df = hist_df.sort_values("date")
    else:
        st.info("No historical composite score history found yet.")

    # === HEADLINE METRICS ===
    as_of = summary.get("as_of", "N/A")
    composite_score = summary.get("composite_score", None)
    composite_label = summary.get("composite_label", None)
    risk_regime = summary.get("risk_regime", "N/A")
    risk_regime_rationale = summary.get("risk_regime_rationale", "")
    anomaly_alerts = summary.get("anomaly_alerts", [])
    correlation_matrix = summary.get("correlation_matrix", None)
    out = summary.get("out", {})
    breadth = summary.get("breadth", {})
    rel_perf_30d = summary.get("rel_perf_30d", {})
    alerts = summary.get("alerts", [])

    # ===== HEADLINE =====
    st.markdown(
        f"#### <span style='font-size:1.3em;'>Composite Market Score: <b>{composite_score if composite_score is not None else 'N/A'}</b> ({composite_label if composite_label else 'N/A'})</span>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<span style='font-weight:600;'>Risk Regime:</span> {risk_regime}  |  <span style='font-weight:600;'>As of:</span> {as_of}",
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
        # Optional: regime bands
        fig.add_shape(type="rect", x0=hist_df["date"].min(), y0=0.7, x1=hist_df["date"].max(), y1=1.0,
                      fillcolor="#38B2AC", opacity=0.09, layer="below", line_width=0)
        fig.add_shape(type="rect", x0=hist_df["date"].min(), y0=0.3, x1=hist_df["date"].max(), y1=0.7,
                      fillcolor="#ECC94B", opacity=0.07, layer="below", line_width=0)
        fig.add_shape(type="rect", x0=hist_df["date"].min(), y0=0, x1=hist_df["date"].max(), y1=0.3,
                      fillcolor="#F56565", opacity=0.09, layer="below", line_width=0)
        fig.update_layout(
            height=280,
            margin=dict(l=0, r=0, t=30, b=0),
            yaxis=dict(range=[0, 1], title="Composite Score"),
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
    st.markdown("#### Relative Outperformance vs S&P 500 (30D)")
    if rel_perf_30d:
        rel_df = pd.DataFrame(list(rel_perf_30d.items()), columns=["Name", "Relative Outperf (%)"])
        rel_df = rel_df.sort_values("Relative Outperf (%)", ascending=False)
        st.dataframe(rel_df, hide_index=True)
    else:
        st.info("Not enough data to compute relative outperformance.")

    # --- Key Index Charts (mirror streamlit_ta_global.py) ---
    st.subheader("Key Market Index Charts")
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
                df, err = fetch_clean_yfinance(ticker, start=start, end=end, interval="1d", auto_adjust=True)
                if err or df is None or len(df) < 10:
                    st.info(f"Not enough {label} data to plot. {err if err else ''}")
                    return
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
                        "Trend": trend
                    })
                table_df = pd.DataFrame(table_rows)
                st.markdown("**Trend Table**")
                st.dataframe(table_df, hide_index=True)
            except Exception as e:
                st.info(f"{label} chart failed to load: {e}")

    chart_list = [
        {
            "ticker": "^STI",
            "label": "Straits Times Index (STI)",
            "explanation": "Singapore's main equity benchmark."
        },
        {
            "ticker": "AAXJ",
            "label": "MSCI Asia ex Japan ETF (AAXJ)",
            "explanation": "Broad Asia ex Japan equities."
        },
        {
            "ticker": "EWS",
            "label": "MSCI Singapore ETF (EWS)",
            "explanation": "NY-traded Singapore equity ETF."
        },
        {
            "ticker": "^HSI",
            "label": "Hang Seng Index (HSI)",
            "explanation": "Hong Kong equity benchmark."
        },
    ]

    for chart in chart_list:
        plot_chart(chart["ticker"], chart["label"], chart["explanation"])

    # --- LLM Summaries Section ---
    st.subheader("LLM-Generated Market Summaries")
    summary_for_llm = {k: v for k, v in summary.items() if k != "out"}  # Do not send "out"
    json_summary = json.dumps(safe_json(summary_for_llm), indent=2)
    if st.button("Generate LLM Market Summaries", type="primary"):
        with st.spinner("Querying LLM..."):
            try:
                llm_output = call_llm("market", json_summary, prompt_vars={
                    "composite_label": composite_label or "",
                    "risk_regime": risk_regime or "",
                })
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
                    st.markdown("<span style='font-size:1.07em;font-weight:600;'>LLM Explanation (Why <b>{}</b> / Regime: <b>{}</b>?):</span>".format(
                        composite_label, risk_regime
                    ), unsafe_allow_html=True)
                    st.warning(sections["Explanation"].strip())
            except Exception as e:
                st.error(f"LLM error: {e}")

    st.caption("Summaries are powered by your LLM agent. Check API key if errors occur.")

    # --- Raw Data Section
    st.subheader("Raw Market Technical Data")
    with st.expander("Show raw summary dict", expanded=False):
        st.json(summary)

# If using as main app file
if __name__ == "__main__":
    st.set_page_config(page_title="Market Dashboard", page_icon="🏢", layout="wide")
    render_market_tab()







