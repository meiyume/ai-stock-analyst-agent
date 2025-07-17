# streamlit_ta_market.py

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from agents.ta_market import ta_market

def render_market_tab():
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
    breadth = mkt_summary["breadth"]
    rel_perf = mkt_summary["rel_perf_30d"]
    composite_score = mkt_summary.get("composite_score")
    composite_label = mkt_summary.get("composite_label")
    risk_regime = mkt_summary.get("risk_regime")
    risk_regime_rationale = mkt_summary.get("risk_regime_rationale")
    anomaly_alerts = mkt_summary.get("anomaly_alerts", [])
    alerts = mkt_summary.get("alerts", [])
    corr_matrix = mkt_summary.get("correlation_matrix")

    # --- Headline & composite/risk regime
    st.markdown(
        f"**As of:** {mkt_as_of} &nbsp;|&nbsp; "
        f"**Composite Score:** {composite_score:.2f} ({composite_label}) &nbsp;|&nbsp; "
        f"**Risk Regime:** {risk_regime}"
    )
    if risk_regime_rationale:
        st.caption(f"_{risk_regime_rationale}_")

    # --- Alerts and anomalies
    if anomaly_alerts or alerts:
        st.warning("  \n".join([*anomaly_alerts, *alerts]), icon="🚨")
    else:
        st.info("🕊️ No significant anomalies detected. Market appears calm.")

    # --- Breadth dashboard
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
                f"{data.get('vol_zscore', 'N/A'):.2f}" if data.get("vol_zscore", None) is not None else "N/A",
                f"{rel_perf_val:+.2f}%" if rel_perf_val is not None else "N/A",
                data.get("alerts", ""),
            ]
        rows.append(row)
    mkt_df = pd.DataFrame(rows, columns=cols)
    st.dataframe(mkt_df, hide_index=True)

    # --- Relative Rotation (bar chart) ---
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

    # --- Correlation heatmap ---
    if corr_matrix:
        st.markdown("**Cross-Asset Correlation (Last 60 Days)**")
        corr_df = pd.DataFrame(corr_matrix)
        st.dataframe(corr_df.style.background_gradient(axis=None, cmap='coolwarm'), height=350)

    st.caption("Baskets include SGX/Asia indices, regional ETFs, and global context. Relative performance is versus S&P500. Composite score, risk regime, and alerts use only available data.")


