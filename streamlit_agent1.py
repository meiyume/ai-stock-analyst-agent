import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from agents.agent1_core import run_full_technical_analysis
from agents.agent1_stock import enforce_date_column, get_llm_summary

st.set_page_config(page_title="Agent 1: AI Technical Analyst", layout="wide")

st.title("📊 Agent 1: AI Technical Analyst")
st.markdown("""
🤖 **Agent 1** analyzes multiple stocks with explainable AI, giving you a risk dashboard and plain-English insights.
""", unsafe_allow_html=True)

# --- Multi-ticker input ---
st.subheader("Step 1: Enter up to 3 Stock Tickers")

if "tickers" not in st.session_state:
    st.session_state.tickers = ["UOB"]  # Start with one

def add_ticker():
    if len(st.session_state.tickers) < 3:
        st.session_state.tickers.append("")

def remove_ticker(idx):
    if len(st.session_state.tickers) > 1:
        st.session_state.tickers.pop(idx)

for i, ticker in enumerate(st.session_state.tickers):
    cols = st.columns([7, 1])
    key = f"ticker_{i}"
    st.session_state.tickers[i] = cols[0].text_input(
        f"Ticker {i+1}", value=ticker, key=key
    )
    if len(st.session_state.tickers) > 1:
        if cols[1].button("❌", key=f"remove_{i}"):
            remove_ticker(i)
            st.rerun()

if len(st.session_state.tickers) < 3:
    if st.button("➕ Add another ticker"):
        add_ticker()
        st.rerun()

def auto_format_ticker(t):
    t = t.strip().upper()
    if '.' not in t:
        return t + ".SI"
    return t

tickers = [auto_format_ticker(t) for t in st.session_state.tickers if t.strip()]
st.write("**Selected Tickers:**", ", ".join(tickers) if tickers else "None")

# --- Hybrid horizon selection ---
st.subheader("Step 2: Select Outlook Horizon")
horizon_options = [
    "1 Day", "3 Days", "5 Days", "7 Days", "14 Days",
    "30 Days", "60 Days", "90 Days", "180 Days", "360 Days", "Custom..."
]
horizon_choice = st.selectbox("Prediction Horizon", horizon_options, index=3)
if horizon_choice == "Custom...":
    custom_days = st.number_input("Custom Horizon (days)", min_value=1, max_value=360, value=7)
    selected_horizon = f"{custom_days} Days"
else:
    selected_horizon = horizon_choice

# --- Step 3: Analyze All Tickers ---
st.subheader("Step 3: Analyze All Tickers")

if st.button("🔍 Run Technical Analysis"):
    all_results = {}
    with st.spinner("Analyzing all tickers with Agent 1..."):
        for ticker in tickers:
            try:
                results = run_full_technical_analysis(
                    ticker,
                    None,  # company_name auto-fetched!
                    selected_horizon,
                    api_key=st.secrets["OPENAI_API_KEY"]
                )
                all_results[ticker] = results
            except Exception as e:
                all_results[ticker] = {"error": str(e)}
    st.session_state["all_results"] = all_results

all_results = st.session_state.get("all_results", {})
if not all_results:
    st.info("Please run the technical analysis to view results.")
    st.stop()

# --- Chief AI Analyst Grand Outlook ---
def get_chief_llm_summary(all_results, horizon, api_key):
    context_lines = []
    for ticker, reports in all_results.items():
        context_lines.append(f"\nFor {ticker}:")
        context_lines.append(f"- Stock Analyst: {reports.get('stock', {}).get('llm_summary', 'N/A')}")
        context_lines.append(f"- Sector Analyst: {reports.get('sector', {}).get('llm_summary', 'N/A')}")
        context_lines.append(f"- Market Analyst: {reports.get('market', {}).get('llm_summary', 'N/A')}")
        context_lines.append(f"- Commodities Analyst: {reports.get('commodities', {}).get('llm_summary', 'N/A')}")
        context_lines.append(f"- Global Macro Analyst: {reports.get('globals', {}).get('llm_summary', 'N/A')}")
    prompt = f"""
You are the Chief AI Analyst. Your analyst team has submitted their LLM reports for multiple stocks and outlook horizon ({horizon}):

{chr(10).join(context_lines)}

Carefully read all agent reports above and write a single, comprehensive 'Grand Outlook' for the user:

- Summarize the technical and macro outlook for each stock.
- Directly compare the tickers: Which is more favorable for the horizon, and why? Highlight key risks and opportunities for each.
- Reference sector, market, commodities, or global factors that impact both/all.
- If the agents disagree or there are conflicting signals, clearly state so.
- End with a bold, 1-2 sentence “Grand Outlook Verdict” that is actionable and understandable by both professional and everyday investors.

Start with a bold headline: “Chief AI Analyst’s Grand Outlook”.
"""
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800,
        temperature=0.4,
    )
    return response.choices[0].message.content.strip()

st.header("👑 Chief AI Analyst's Grand Outlook")
api_key = st.secrets["OPENAI_API_KEY"]

with st.spinner("Chief AI Analyst is reviewing all agent reports and composing a grand synthesis..."):
    try:
        chief_llm = get_chief_llm_summary(all_results, selected_horizon, api_key)
        st.success(chief_llm)
    except Exception as e:
        st.error(f"Chief AI Analyst synthesis failed: {e}")

# --- Results per ticker with tabs ---
for ticker, results in all_results.items():
    with st.expander(f"📊 Results for {ticker}", expanded=True):
        if "error" in results:
            st.error(f"Analysis failed for {ticker}: {results['error']}")
            continue

        tab_dashboard, tab_agents, tab_technicals = st.tabs(
            ["🛡️ Dashboard", "🤖 AI Agent Reports", "📈 Technicals"]
        )

        # --- Dashboard tab ---
        with tab_dashboard:
            stock_summary = results.get("stock", {}) if "stock" in results else results
            stock_summary["horizon"] = selected_horizon

            df = results.get("stock_df", None)
            if df is not None:
                df = enforce_date_column(df)

            st.markdown(f"### Risk Dashboard for {ticker}")
            heatmap = stock_summary.get("heatmap_signals", {})
            risk_score = stock_summary.get("composite_risk_score", None)
            risk_level = stock_summary.get("risk_level", None)
            if heatmap:
                cols = st.columns(len(heatmap))
                for i, (indicator, status) in enumerate(heatmap.items()):
                    if "Overbought" in status or "Bearish" in status or "Selling" in status or "Divergence" in status:
                        color = "🔴"
                    elif "Spike" in status or "High" in status or "Oversold" in status:
                        color = "🟠"
                    elif "Bullish" in status or "Buying" in status or "Strong" in status:
                        color = "🟢"
                    elif "Neutral" in status or "None" in status:
                        color = "⚪"
                    else:
                        color = "🟡"
                    cols[i].markdown(
                        f"<div style='background-color:#ffffff;padding:10px;border-radius:10px;text-align:center;'>"
                        f"<b>{indicator}</b><br>{color} {status}</div>",
                        unsafe_allow_html=True
                    )
            if risk_score is not None:
                st.markdown(f"**Composite Risk Score**: `{risk_score}`")
            if risk_level is not None:
                st.markdown(f"**Overall Risk Level**: 🎯 **{risk_level}**")

            if df is not None:
                st.markdown("#### 🕯️ Candlestick Chart with SMA & Bollinger Bands")
                fig = go.Figure()
                fig.add_trace(go.Candlestick(
                    x=df["Date"], open=df["Open"], high=df["High"],
                    low=df["Low"], close=df["Close"], name="Candles"
                ))
                fig.add_trace(go.Scatter(x=df["Date"], y=df["SMA5"], mode="lines", name="SMA5"))
                fig.add_trace(go.Scatter(x=df["Date"], y=df["SMA10"], mode="lines", name="SMA10"))
                fig.add_trace(go.Scatter(x=df["Date"], y=df["Upper"], mode="lines", name="Upper BB", line=dict(dash='dot')))
                fig.add_trace(go.Scatter(x=df["Date"], y=df["Lower"], mode="lines", name="Lower BB", line=dict(dash='dot')))
                fig.update_layout(height=400, xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)

            # Add more visuals (patterns, anomalies) here if needed.

        # --- AI Agent Reports tab ---
        with tab_agents:
            st.markdown("### 🤖 AI Agent Reports")
            agent_configs = [
                ("Stock Analyst", "stock", "📈"),
                ("Sector Analyst", "sector", "🏭"),
                ("Market Analyst", "market", "📊"),
                ("Commodities Analyst", "commodities", "🛢️"),
                ("Global Macro Analyst", "globals", "🌍"),
            ]
            for label, key, icon in agent_configs:
                with st.expander(f"{icon} {label}"):
                    st.write(results.get(key, {}).get("llm_summary", "No report."))

        # --- Technicals tab ---
        with tab_technicals:
            st.markdown("### 📈 Technical Indicators & Patterns")
            # Here you can insert RSI, MACD, Stochastic, Volume, ADX, ATR, CMF, OBV, anomalies, and pattern detection
            # Example for RSI (add others similarly):

            df = results.get("stock_df", None)
            if df is not None and "RSI" in df.columns:
                st.markdown("#### 📉 RSI (Relative Strength Index)")
                rsi_fig = go.Figure()
                rsi_fig.add_trace(go.Scatter(
                    x=df["Date"], y=df["RSI"],
                    name="RSI", line=dict(width=3, color="purple")
                ))
                rsi_fig.update_yaxes(range=[0, 100])
                rsi_fig.update_layout(height=220, margin=dict(t=16, b=8))
                st.plotly_chart(rsi_fig, use_container_width=True)
            # Repeat for MACD, volume, etc. as you like

# Footer
st.markdown("---")
st.caption("Agent 1: For informational and educational use only. Not financial advice.")





