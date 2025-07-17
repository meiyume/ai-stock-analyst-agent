# streamlit_ta_market.py

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from agents.ta_market import ta_market
import yfinance as yf
from datetime import datetime, timedelta

def plot_index_chart(ticker, label, window=180, min_points=20):
    """Robustly plot a line chart with SMA overlays, defensive to all data/column issues."""
    try:
        end = datetime.today()
        start = end - timedelta(days=window + 60)
        df = yf.download(ticker, start=start, end=end, interval="1d", auto_adjust=True, progress=False)
        if df is None or not isinstance(df, pd.DataFrame) or df.empty:
            st.info(f"Not enough data to plot {label} (empty dataframe).")
            return
        # Flatten MultiIndex columns (if any)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [
                "_".join([str(i) for i in col if i and i != "None"]) for col in df.columns.values
            ]
        # Find 'close' column(s) (case-insensitive, works for 'Adj Close', 'Close*', etc.)
        close_cols = [c for c in df.columns if isinstance(c, str) and "close" in c.lower()]
        if not close_cols:
            st.warning(f"Chart error ({label}): No close price column found. Columns: {list(df.columns)}")
            return
        close_col = close_cols[0]
        # Drop NaN, check minimum history
        df = df.dropna(subset=[close_col])
        if len(df) < min_points:
            st.info(f"Not enough {label} data (only {len(df)} valid points).")
            return
        df = df.tail(window).copy()
        # Calculate SMAs only if enough data
        for sma_win in [20, 50, 200]:
            if len(df) >= sma_win:
                df[f"SMA{sma_win}"] = df[close_col].rolling(window=sma_win).mean()
            else:
                df[f"SMA{sma_win}"] = float('nan')
        # Check again for valid points after SMAs
        if df[close_col].isnull().all():
            st.info(f"All values in close column for {label} are NaN.")
            return
        # Build chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df.index, y=df[close_col], mode="lines", name=label,
            line=dict(width=2, color="#3182ce")
        ))
        for sma_win, dash, color in zip([20, 50, 200], ['dot', 'dash', 'solid'], ["#8fd3fe", "#38B2AC", "#222"]):
            sma_col = f"SMA{sma_win}"
            if not df[sma_col].isnull().all():
                fig.add_trace(go.Scatter(
                    x=df.index, y=df[sma_col], mode="lines", name=f"SMA {sma_win}",
                    line=dict(width=1, dash=dash, color=color)
                ))
        fig.update_layout(
            title=label,
            height=230,
            margin=dict(l=10, r=10, t=40, b=10),
            legend=dict(orientation="h", yanchor="top", y=0.95, xanchor="right", x=1),
            template="plotly_white",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"Chart error ({label}): {e}")

def render_market_tab():
    st.header("📈 AI Market / Sector Technical Dashboard")

    st.markdown(
        """
        The Market tab analyzes Asia/SGX, global, and thematic baskets with pro-grade technicals, outperformance, and cross-asset correlation—all built for investor and portfolio context.
        """
    )

    # --- Fetch market summary ---
    with st.spinner("Loading market/sector/factor technicals..."):
        try:
            mkt_summary = ta_market()
            st.success("Fetched and computed market/sector technical metrics.")
        except Exception as e:
            st.error(f"Error in ta_market(): {e}")
            st.stop()

    # --- Historical Composite Score Chart ---
    hist_df = mkt_summary.get("composite_score_history")
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
    else:
        st.info("No historical market composite score data available yet.")

    # --- HEADLINE & LOGIC ---
    as_of = mkt_summary.get("as_of", "N/A")
    composite_score = mkt_summary.get("composite_score")
    composite_label = mkt_summary.get("composite_label")
    risk_regime = mkt_summary.get("risk_regime")
    risk_regime_rationale = mkt_summary.get("risk_regime_rationale")
    anomaly_alerts = mkt_summary.get("anomaly_alerts", [])
    alerts = mkt_summary.get("alerts", [])
    breadth = mkt_summary.get("breadth", {})
    rel_perf = mkt_summary.get("rel_perf_30d", {})
    corr_matrix = mkt_summary.get("correlation_matrix")
    mkt_out = mkt_summary.get("out", {})

    # === HEADLINE ===
    st.markdown(
        f"#### <span style='font-size:1.3em;'>Composite Market Score: <b>{composite_score if composite_score is not None else 'N/A'}</b> ({composite_label if composite_label else 'N/A'})</span>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<span style='font-weight:600;'>Risk Regime:</span> {risk_regime}  |  <span style='font-weight:600;'>As of:</span> {as_of}",
        unsafe_allow_html=True
    )
    # Brief explanation (optional—adjust for your logic)
    composite_score_expl = {
        "Bullish": "A 'Bullish' composite score means most regional indices are in strong uptrends and above key moving averages.",
        "Neutral": "A 'Neutral' composite score signals mixed technicals—some indices strong, others flat or weak.",
        "Bearish": "A 'Bearish' composite score means most baskets are trending down or below key averages—caution is warranted."
    }
    risk_regime_expl = {
        "Bullish": "A 'Bullish' risk regime means volatility is falling and major indices are rising. Investors are confident and risk-taking is encouraged.",
        "Neutral": "A 'Neutral' risk regime means the market is not panicky, but not fully risk-on either.",
        "Bearish": "A 'Bearish' risk regime means volatility is rising and most indices are falling. Caution is warranted."
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

    # --- Show 2 key index charts (STI, AAXJ) ---
    st.markdown("#### Key Index Charts")
    col1, col2 = st.columns(2)
    with col1:
        plot_index_chart("^STI", "Straits Times Index (STI)")
    with col2:
        plot_index_chart("AAXJ", "Asia ex Japan ETF (AAXJ)")

    # --- Alerts & Anomalies ---
    if anomaly_alerts or alerts:
        st.warning("**Smart Anomaly Alerts:**\n\n" + "\n".join([*anomaly_alerts, *alerts]))
    else:
        st.info("🕊️ No significant market anomalies detected. Market appears calm.")

    # --- Breadth Dashboard ---
    st.markdown("**Breadth Summary:**")
    st.write(pd.DataFrame([breadth]))

    # --- Trend Table ---
    cols = [
        "Name", "Last", "30D Change", "90D Change", "200D Change",
        "Trend (30D)", "Trend (90D)", "Trend (200D)",
        "Vol (30D)", "Vol (90D)", "Vol (200D)",
        "SMA50", "SMA200", "RSI", "MACD", "MACD Sig", "Vol Z", "RelPerf (30D)", "Alerts"
    ]
    rows = []
    for name, data in mkt_out.items():
        if "error" in data:
            row = [name, data.get("error", "")] + [""] * (len(cols)-2)
        else:
            rel_perf_val = rel_perf.get(name, None)
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
                data.get("sma50_status", "N/A"),
                data.get("sma200_status", "N/A"),
                f"{data.get('rsi', 'N/A'):.1f}" if data.get("rsi", None) is not None else "N/A",
                f"{data.get('macd', 'N/A'):.2f}" if data.get("macd", None) is not None else "N/A",
                f"{data.get('macd_signal', 'N/A'):.2f}" if data.get("macd_signal", None) is not None else "N/A",
                f"{data.get('vol_zscore', 'N/A'):.2f}" if data.get('vol_zscore', None) is not None else "N/A",
                f"{rel_perf_val:+.2f}%" if rel_perf_val is not None else "N/A",
                data.get("alerts", ""),
            ]
        rows.append(row)
    mkt_df = pd.DataFrame(rows, columns=cols)
    st.dataframe(mkt_df, hide_index=True)

    # --- Relative Outperformance vs S&P500 (Bar Chart) ---
    if rel_perf:
        st.markdown("**Relative Outperformance vs S&P 500 (Last 30D)**")
        rel_perf_df = pd.DataFrame(list(rel_perf.items()), columns=["Name", "Relative Perf (30D, %)"])
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

    # --- Cross-Asset Correlation Heatmap (with different color scheme) ---
    if corr_matrix:
        st.markdown("**Cross-Asset Correlation (Last 60 Days)**")
        corr_df = pd.DataFrame(corr_matrix)
        fig_corr = go.Figure(
            data=go.Heatmap(
                z=corr_df.values,
                x=corr_df.columns,
                y=corr_df.index,
                colorscale="Viridis",    # Different from global tab
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
            template="plotly_white"
        )
        st.plotly_chart(fig_corr, use_container_width=True)

    st.caption("Baskets include SGX/Asia indices, regional ETFs, and global context. Composite score, risk regime, and alerts use only available data.")

# --- LLM Summaries and Explanation ---
st.subheader("LLM-Generated Market Summaries")
import json

# Prepare JSON summary for LLM input
market_summary = dict(mkt_summary)  # Make a shallow copy for editing if needed
json_summary = json.dumps(market_summary, indent=2, default=str)

if st.button("Generate LLM Market Summaries", type="primary"):
    from llm_utils import call_llm
    with st.spinner("Querying LLM for market outlook..."):
        try:
            llm_output = call_llm("market", json_summary, prompt_vars={
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
st.subheader("Raw Market Technical Data")
with st.expander("Show raw summary dict", expanded=False):
    st.json(mkt_summary)

# ---- End ----



