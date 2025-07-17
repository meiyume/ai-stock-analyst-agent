# streamlit_ta_market.py

import streamlit as st
import os
import json
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
import numpy as np

from agents.ta_market import ta_market
from data_utils import fetch_clean_yfinance
from llm_utils import call_llm

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

    hist_df = summary.get("composite_score_history")
    if hist_df is not None and not hist_df.empty:
        hist_df = hist_df.sort_values("date")
    else:
        st.info("No historical composite score history found yet.")

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

    st.markdown(
        f"#### <span style='font-size:1.3em;'>Composite Market Score: <b>{composite_score if composite_score is not None else 'N/A'}</b> ({composite_label if composite_label else 'N/A'})</span>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<span style='font-weight:600;'>Risk Regime:</span> {risk_regime}  |  <span style='font-weight:600;'>As of:</span> {as_of}",
        unsafe_allow_html=True
    )
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

    # --- Market Baskets Overview Table
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

    # --- Advanced Charts for STI, AAXJ, EWS, HSI ---
    st.subheader("Key Market Index Charts (with Advanced Features)")

    # Toggles for overlays
    show_sma = st.toggle("Show Moving Averages (SMA20/50/200)", value=True)
    show_regime = st.toggle("Show Regime Bands", value=True)
    show_signals = st.toggle("Show MACD/RSI/Highs/Lows", value=True)
    show_alerts = st.toggle("Show Smart Alerts", value=True)
    show_vol = st.toggle("Show Rolling Volatility Mini-Plot", value=False)

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

    def compute_macd(series, span1=12, span2=26, signal=9):
        ema1 = series.ewm(span=span1, adjust=False).mean()
        ema2 = series.ewm(span=span2, adjust=False).mean()
        macd = ema1 - ema2
        macd_signal = macd.ewm(span=signal, adjust=False).mean()
        return macd, macd_signal

    def compute_rsi(series, window=14):
        delta = series.diff()
        up = delta.clip(lower=0)
        down = -delta.clip(upper=0)
        ma_up = up.rolling(window, min_periods=1).mean()
        ma_down = down.rolling(window, min_periods=1).mean()
        rs = ma_up / ma_down.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi

    for chart in chart_list:
        st.markdown(f"### {chart['label']}")
        st.caption(chart["explanation"])
        df, err = fetch_clean_yfinance(chart["ticker"], start="2022-01-01", interval="1d", auto_adjust=True)
        if err or df is None or len(df) < 30:
            st.info(f"{chart['label']} data unavailable: {err}")
            continue

        # Defensive flatten/squeeze for close column
        close = df["close"]
        if isinstance(close, pd.DataFrame) or (hasattr(close, "shape") and len(close.shape) > 1 and close.shape[1] > 1):
            close = close.iloc[:, 0]
        close = close.astype(float).dropna()
        df = df.reset_index(drop=True)
        df["SMA20"] = close.rolling(20).mean()
        df["SMA50"] = close.rolling(50).mean()
        df["SMA200"] = close.rolling(200).mean()
        df["MACD"], df["MACD_Signal"] = compute_macd(close)
        df["RSI"] = compute_rsi(close)
        df["date"] = pd.to_datetime(df["date"])

        # Use market composite_score_history for regime bands
        local_hist_df = hist_df

        fig = go.Figure()

        # Price line
        fig.add_trace(go.Scatter(
            x=df["date"], y=close,
            mode="lines", name=chart["label"], line=dict(width=2)
        ))

        # Moving Averages
        if show_sma:
            fig.add_trace(go.Scatter(
                x=df["date"], y=df["SMA20"],
                mode="lines", name="SMA20", line=dict(dash="dot")
            ))
            fig.add_trace(go.Scatter(
                x=df["date"], y=df["SMA50"],
                mode="lines", name="SMA50", line=dict(dash="dash")
            ))
            fig.add_trace(go.Scatter(
                x=df["date"], y=df["SMA200"],
                mode="lines", name="SMA200", line=dict(dash="solid", color="black")
            ))

        # Regime Color Bands
        if show_regime and local_hist_df is not None and not local_hist_df.empty:
            regime_colors = {"Bullish": "#38B2AC", "Neutral": "#ECC94B", "Bearish": "#F56565"}
            last_date = df["date"].max()
            for i, row in local_hist_df.iterrows():
                if i == 0: continue
                prev_date = local_hist_df.iloc[i-1]["date"]
                curr_date = row["date"]
                label = row["composite_label"]
                color = regime_colors.get(label, "#888")
                fig.add_shape(
                    type="rect",
                    x0=prev_date, x1=curr_date,
                    y0=0, y1=close.max()*1.2,
                    fillcolor=color, opacity=0.10, line_width=0, layer="below"
                )
            if len(local_hist_df) > 1:
                fig.add_shape(
                    type="rect",
                    x0=local_hist_df.iloc[-1]["date"], x1=last_date,
                    y0=0, y1=close.max()*1.2,
                    fillcolor=regime_colors.get(local_hist_df.iloc[-1]["composite_label"], "#888"),
                    opacity=0.10, line_width=0, layer="below"
                )

        # Regime Change Vertical Lines
        if show_regime and local_hist_df is not None and not local_hist_df.empty:
            prev_label = None
            for i, row in local_hist_df.iterrows():
                label = row["composite_label"]
                if prev_label and label != prev_label:
                    fig.add_shape(
                        type="line",
                        x0=row["date"], x1=row["date"],
                        y0=0, y1=close.max()*1.2,
                        line=dict(color="black", dash="dot", width=1.5)
                    )
                    fig.add_annotation(
                        x=row["date"], y=close.max()*1.12,
                        text=label, showarrow=False, font=dict(size=12, color="black"),
                        bgcolor="white", opacity=0.7
                    )
                prev_label = label

        # Key Technical Signal Markers
        if show_signals:
            macd = df["MACD"]
            macd_sig = df["MACD_Signal"]
            for i in range(1, len(macd)):
                # Bullish crossover
                if macd.iloc[i-1] < macd_sig.iloc[i-1] and macd.iloc[i] > macd_sig.iloc[i]:
                    fig.add_trace(go.Scatter(
                        x=[df["date"].iloc[i]], y=[close.iloc[i]],
                        mode="markers+text",
                        marker=dict(color="green", size=14, symbol="arrow-up"),
                        text=["MACD↑"], textposition="bottom center",
                        name="MACD Bull", showlegend=False
                    ))
                # Bearish crossover
                if macd.iloc[i-1] > macd_sig.iloc[i-1] and macd.iloc[i] < macd_sig.iloc[i]:
                    fig.add_trace(go.Scatter(
                        x=[df["date"].iloc[i]], y=[close.iloc[i]],
                        mode="markers+text",
                        marker=dict(color="red", size=14, symbol="arrow-down"),
                        text=["MACD↓"], textposition="top center",
                        name="MACD Bear", showlegend=False
                    ))
            for i in range(len(df)):
                if df["RSI"].iloc[i] > 70:
                    fig.add_trace(go.Scatter(
                        x=[df["date"].iloc[i]], y=[close.iloc[i]],
                        mode="markers+text",
                        marker=dict(color="purple", size=12, symbol="circle"),
                        text=["RSI>70"], textposition="top right",
                        name="RSI Overbought", showlegend=False
                    ))
                elif df["RSI"].iloc[i] < 30:
                    fig.add_trace(go.Scatter(
                        x=[df["date"].iloc[i]], y=[close.iloc[i]],
                        mode="markers+text",
                        marker=dict(color="blue", size=12, symbol="circle"),
                        text=["RSI<30"], textposition="bottom right",
                        name="RSI Oversold", showlegend=False
                    ))
            for lookback, symbol, col in [(30, "⭐", "star"), (90, "🥇", "diamond"), (200, "🏅", "diamond")]:
                for i in range(lookback, len(df)):
                    window = close.iloc[i-lookback:i+1]
                    price = close.iloc[i]
                    if price == window.max():
                        fig.add_trace(go.Scatter(
                            x=[df["date"].iloc[i]], y=[price],
                            mode="markers+text",
                            marker=dict(color="gold", size=11, symbol=col),
                            text=[f"{symbol}High"], textposition="top left",
                            showlegend=False
                        ))
                    if price == window.min():
                        fig.add_trace(go.Scatter(
                            x=[df["date"].iloc[i]], y=[price],
                            mode="markers+text",
                            marker=dict(color="black", size=11, symbol=col),
                            text=[f"{symbol}Low"], textposition="bottom left",
                            showlegend=False
                        ))

        # Dynamic Smart Alert Annotations (from anomaly_alerts in summary)
        if show_alerts and anomaly_alerts:
            for msg in anomaly_alerts:
                fig.add_annotation(
                    x=df["date"].iloc[-1], y=close.iloc[-1],
                    text=msg, showarrow=True, arrowhead=1, ax=0, ay=-40,
                    bgcolor="yellow", opacity=0.85,
                    font=dict(size=12, color="black")
                )

        fig.update_layout(
            title=chart["label"],
            xaxis_title="Date",
            yaxis_title="Price",
            hovermode="x unified",
            height=500,
            legend=dict(orientation="h"),
            template="plotly_white",
            dragmode="zoom",
            margin=dict(l=30, r=30, t=60, b=30),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
        )

        st.plotly_chart(fig, use_container_width=True)

        # Rolling Volatility Mini-Plot
        if show_vol:
            st.markdown("**Rolling 30d Volatility (Mini-Plot):**")
            df["vol_30d"] = close.rolling(30).std()
            fig_vol = go.Figure(go.Scatter(
                x=df["date"], y=df["vol_30d"],
                mode="lines", name="Volatility (30d)", line=dict(color="orange", width=2)
            ))
            fig_vol.update_layout(height=180, margin=dict(l=10, r=10, t=10, b=10),
                                 template="plotly_white", yaxis_title="Volatility", xaxis_title="Date")
            st.plotly_chart(fig_vol, use_container_width=True)

        # Trend Table (same as global)
        table_windows = [20, 50, 200]
        table_rows = []
        for win in table_windows:
            window = close[-win:] if len(close) >= win else close
            if window.empty:
                pct, latest, trend = "N/A", "N/A", "N/A"
            else:
                start, endv = window.iloc[0], window.iloc[-1]
                if pd.isna(start) or pd.isna(endv) or start == 0:
                    pct, latest, trend = "N/A", "N/A", "N/A"
                else:
                    pct = 100 * (endv - start) / start
                    trend = "Uptrend" if endv > start else "Downtrend" if endv < start else "Flat"
                    latest = f"{endv:,.2f}"
                    pct = f"{pct:+.2f}%"
            table_rows.append({
                "Window": f"{win}d",
                "% Change": pct,
                "Latest": latest,
                "Trend": trend
            })
        table_df = pd.DataFrame(table_rows)
        st.markdown("**Trend Table**")
        st.dataframe(table_df, hide_index=True)

    # --- LLM Summaries Section ---
    st.subheader("LLM-Generated Market Summaries")
    summary_for_llm = {k: v for k, v in summary.items() if k != "out"}  # Do not send "out"
    json_summary = json.dumps(summary_for_llm, indent=2)
    if st.button("Generate LLM Market Summaries", type="primary"):
        with st.spinner("Querying LLM..."):
            try:
                llm_output = call_llm("market", json_summary, prompt_vars={
                    "composite_label": composite_label or "",
                    "risk_regime": risk_regime or "",
                })
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







