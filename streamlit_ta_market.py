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

