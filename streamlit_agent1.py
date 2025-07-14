import streamlit as st
import pandas as pd
from agents.agent1_core import run_full_technical_analysis

# Page setup
st.set_page_config(page_title="AI-Powered Stock Analyst", page_icon="📊", layout="wide")

st.markdown("# 🤖 AI-Powered Multi-Agent Stock Analyst")
st.markdown(
    """
    Welcome to your smart investor dashboard.  
    - Get a Chief Analyst summary plus deep dives from five AI agents (Stock, Sector, Market, Commodities, Globals).
    - Each tab gives you charts, technical signals, plain-English AI explanations, and all the raw data you want!
    ---
    """
)

# --- User input sidebar ---
with st.sidebar:
    st.header("Stock Selection")
    ticker = st.text_input("Enter Stock Ticker (e.g., AAPL, MSFT, TSLA):", value="AAPL")
    horizon = st.selectbox("Prediction Horizon:", ["1 Day", "3 Days", "7 Days", "30 Days"], index=2)
    openai_api_key = st.text_input("OpenAI API Key", type="password")
    run_button = st.button("Run Analysis")

if run_button or ticker:
    # --- Run orchestrator (calls all agents) ---
    with st.spinner("Running full technical and AI analysis..."):
        results = run_full_technical_analysis(
            ticker,
            company_name=None,
            horizon=horizon,
            lookback_days=None,
            api_key=openai_api_key if openai_api_key else None
        )

    # --- Display Chief Analyst summary at top ---
    st.markdown(f"## 🏆 Chief Analyst Grand Outlook for **{results['company_name']}** ({results['ticker']}) — {results['horizon']}")
    st.markdown(f"**AI Summary:** {results['llm_summary']}")
    st.markdown(f"**Composite Risk Score:** {results['composite_risk_score']}")
    st.markdown(f"**Risk Level:** {results['risk_level']}")

    st.divider()

    # --- Agent Tabs ---
    agent_configs = [
        ("Stock", "stock"),
        ("Sector", "sector"),
        ("Market", "market"),
        ("Commodities", "commodities"),
        ("Globals", "globals"),
    ]
    tab_names = [label for label, _ in agent_configs]
    tabs = st.tabs(tab_names)

    agent_reports = {}
    for i, (agent_label, agent_key) in enumerate(agent_configs):
        agent_data = results.get(agent_key, {})
        agent_reports[agent_label] = {
            "summary": agent_data.get("llm_summary", "No summary available."),
            "risk": agent_data.get("risk_level", "N/A"),
            "plot": agent_data.get("chart", None),
            "raw": agent_data,  # full dict for debug/expand
            "df": agent_data.get("df"),
        }

    for i, agent in enumerate(tab_names):
        with tabs[i]:
            st.markdown(f"### {agent} Analyst Report")

            # Chart (with unique key)
            chart_obj = agent_reports[agent]["plot"]
            if chart_obj is not None:
                st.plotly_chart(chart_obj, use_container_width=True, key=f"{agent}_plot")
            else:
                st.info("No chart available for this agent.")

            # Summaries
            st.markdown(f"**AI Summary:** {agent_reports[agent]['summary']}")
            st.markdown(f"**Risk Level:** {agent_reports[agent]['risk']}")

            # Expand for technical/raw
            with st.expander("Show technical details / raw data"):
                st.write(agent_reports[agent]["raw"])
                if isinstance(agent_reports[agent]["df"], pd.DataFrame):
                    st.dataframe(agent_reports[agent]["df"])
            
            # Download button (summary as markdown)
            st.download_button(
                label="Download Agent Report",
                data=agent_reports[agent]["summary"],
                file_name=f"{ticker}_{agent}_report.md"
            )

else:
    st.info("Enter a ticker and click **Run Analysis** to start.")







