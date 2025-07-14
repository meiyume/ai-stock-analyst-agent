import streamlit as st
import pandas as pd

from agents.agent1_core import (
    analyze_stock,
    analyze_sector,
    analyze_market,
    analyze_commodities,
    analyze_globals,
)

st.set_page_config(page_title="AI Technical Analyst", page_icon=":bar_chart:")

st.title("🦾 AI-Powered Technical Analyst: Multi-Agent Stock Intelligence")
st.write("Welcome! Get expert, explainable outlooks on any stock, sector, market, and more—by your modular team of digital analysts.")

# --- Sidebar user inputs ---
st.sidebar.header("Stock Analysis Input")
ticker = st.sidebar.text_input("Enter SGX ticker symbol (e.g., UOB.SI, OCBC.SI)", value="UOB.SI")
horizon = st.sidebar.selectbox("Select Outlook Horizon", ["1 Day", "3 Days", "7 Days", "30 Days", "90 Days"])

api_key = st.secrets["OPENAI_API_KEY"]

# --- Helper for clean LLM summary tabs ---
def display_llm_summaries(agent_name, summary):
    st.subheader(f"🧠 LLM-Powered {agent_name} Analyst Report")
    tab1, tab2 = st.tabs(["Technical Summary", "For Grandmas and Grandpas"])
    with tab1:
        st.markdown(
            "<span style='font-size:1.1em;font-weight:600;'>🧑‍💼 Technical Summary</span>",
            unsafe_allow_html=True
        )
        st.write(summary.get("llm_technical_summary", "No technical summary available."))
    with tab2:
        st.markdown(
            "<span style='font-size:1.1em;font-weight:600;'>👵 Plain-English Summary</span>",
            unsafe_allow_html=True
        )
        st.write(summary.get("llm_plain_summary", "No plain-English summary available."))

# --- Orchestrator: Run all agents ---
st.info("Running multi-agent team. This may take up to a minute for full AI analysis...")

with st.spinner("Agent 1 Stock analyzing..."):
    stock_summary, stock_df = analyze_stock(ticker, horizon, api_key=api_key)
with st.spinner("Agent 1 Sector analyzing..."):
    sector_summary, sector_df = analyze_sector(ticker, horizon, api_key=api_key)
with st.spinner("Agent 1 Market analyzing..."):
    market_summary, market_df = analyze_market(ticker, horizon, api_key=api_key)
with st.spinner("Agent 1 Commodities analyzing..."):
    commodities_summary, commodities_df = analyze_commodities(ticker, horizon, api_key=api_key)
with st.spinner("Agent 1 Global analyzing..."):
    globals_summary, globals_df = analyze_globals(ticker, horizon, api_key=api_key)

# --- Chief/Grand Outlook (example - can expand logic here) ---
st.header("🎩 Chief AI Analyst Grand Outlook (BETA)")
# You could call another synthesis LLM function here for the ultimate "orchestra" summary.

st.write("**Here’s what your Chief AI Analyst sees at a glance, after reviewing the team's reports:**")
# Placeholder: display the stock technical summary as the 'grand outlook' for now
st.success(stock_summary.get("llm_technical_summary", "No technical summary available."))

# --- Show each agent's dual LLM summary in tabs ---
st.divider()
display_llm_summaries("Stock", stock_summary)
st.divider()
display_llm_summaries("Sector", sector_summary)
st.divider()
display_llm_summaries("Market", market_summary)
st.divider()
display_llm_summaries("Commodities", commodities_summary)
st.divider()
display_llm_summaries("Global", globals_summary)

# --- Example: Plot chart for stock (can expand for sector/market etc.) ---
import plotly.graph_objects as go

st.header(f"📈 {ticker} Candlestick Chart with SMA & Bollinger Bands")
if not stock_df.empty:
    fig = go.Figure(
        data=[
            go.Candlestick(
                x=stock_df["Date"],
                open=stock_df["Open"],
                high=stock_df["High"],
                low=stock_df["Low"],
                close=stock_df["Close"],
                name="Candlestick",
            ),
            go.Scatter(
                x=stock_df["Date"], y=stock_df["SMA5"], mode="lines", name="SMA5"
            ),
            go.Scatter(
                x=stock_df["Date"], y=stock_df["SMA10"], mode="lines", name="SMA10"
            ),
            go.Scatter(
                x=stock_df["Date"], y=stock_df["Upper"], mode="lines", name="Bollinger Upper", line=dict(dash="dot")
            ),
            go.Scatter(
                x=stock_df["Date"], y=stock_df["Lower"], mode="lines", name="Bollinger Lower", line=dict(dash="dot")
            ),
        ]
    )
    fig.update_layout(height=500, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("No price data to plot for this ticker/horizon.")

# --- Display composite risk and risk dashboard ---
st.header("🚦 Composite Risk Dashboard")
st.write(f"**Composite Risk Score:** {stock_summary.get('composite_risk_score', 'N/A')}")
st.write(f"**Risk Level:** {stock_summary.get('risk_level', 'N/A')}")

# --- Show technical indicator mini-dashboard for Stock agent ---
with st.expander("Show All Stock Technical Indicators (Raw Output)"):
    st.dataframe(stock_df)

# You can further add dashboards for other agents as needed (sector_df, etc.)







