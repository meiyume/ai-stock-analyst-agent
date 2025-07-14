import streamlit as st
import pandas as pd
from agents.agent1_core import run_full_technical_analysis

# --- UI Setup ---
st.set_page_config(page_title="SGX AI Stock Analyst", page_icon=":chart_with_upwards_trend:", layout="wide")
st.title("🇸🇬 SGX AI-Powered Multi-Agent Stock Analyst")
st.caption("Grand outlook and deep-dives from 5 AI agents — now with LLM summaries, risk dashboards, and all the technicals.")

# --- Input Section ---
with st.sidebar:
    st.header("Stock Selection")
    ticker = st.text_input("SGX Stock Ticker (e.g. DBS.SI)", value="D05.SI")
    horizon = st.selectbox("Outlook Horizon", ["1 Day", "3 Days", "7 Days", "30 Days"], index=2)
    run_btn = st.button("Run AI Analysis")

if run_btn:
    with st.spinner("Running all AI agents..."):
        results = run_full_technical_analysis(
            ticker=ticker,
            company_name=None,
            horizon=horizon,
            lookback_days=None,
            api_key=st.secrets.get("OPENAI_API_KEY", None)
        )

    # --- Chief Analyst/Composite Summary ---
    st.markdown(f"## 🏆 Chief Analyst Grand Outlook — {results['company_name']} ({results['ticker']}) — {results['horizon']}")
    st.markdown(f"**AI Summary:** {results['llm_summary']}")
    st.markdown(f"**Composite Risk Score:** {results['composite_risk_score']}")
    st.markdown(f"**Risk Level:** {results['risk_level']}")
    st.divider()

    # --- Tabs for All Agents ---
    AGENT_KEYS = [("Stock", "stock"), ("Sector", "sector"), ("Market", "market"), ("Commodities", "commodities"), ("Globals", "globals")]
    tab_labels = [x[0] for x in AGENT_KEYS]
    tabs = st.tabs(tab_labels)

    agent_reports = {}
    for label, key in AGENT_KEYS:
        agent_data = results.get(key, {})
        agent_reports[label] = {
            "summary": agent_data.get("llm_summary", "No summary."),
            "risk": agent_data.get("risk_level", "N/A"),
            "plot": agent_data.get("chart", None),
            "raw": agent_data,
            "df": agent_data.get("df"),
        }

    for i, label in enumerate(tab_labels):
        with tabs[i]:
            st.markdown(f"### {label} Analyst Report")

            # Chart (with unique key per tab)
            if agent_reports[label]["plot"] is not None:
                st.plotly_chart(agent_reports[label]["plot"], use_container_width=True, key=f"{label}_plot")
            else:
                st.info("No chart available for this agent.")

            # AI and risk summaries
            st.markdown(f"**AI Summary:** {agent_reports[label]['summary']}")
            st.markdown(f"**Risk Level:** {agent_reports[label]['risk']}")

            # Expand technical details/raw
            with st.expander("Show technical details / raw data"):
                st.write(agent_reports[label]["raw"])
                if isinstance(agent_reports[label]["df"], pd.DataFrame):
                    st.dataframe(agent_reports[label]["df"])

            # Download summary as markdown
            st.download_button(
                label="Download Agent Report",
                data=agent_reports[label]["summary"],
                file_name=f"{ticker}_{label}_report.md"
            )

else:
    st.info("Enter a SGX ticker (e.g., D05.SI, U11.SI, A17U.SI) and click **Run AI Analysis**.")





