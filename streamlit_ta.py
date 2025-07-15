import streamlit as st
import pandas as pd
from agents.ta_chief import run_full_technical_analysis

st.set_page_config(page_title="SGX AI Stock Analyst", page_icon=":chart_with_upwards_trend:", layout="wide")
st.title("🇸🇬 SGX AI-Powered Multi-Agent Stock Analyst")
st.caption("Grand outlook and deep-dives from 5 AI agents — with LLM summaries, risk dashboards, and technicals.")

# --- Sidebar Input ---
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

    st.markdown(f"## 🏆 Chief Analyst Grand Outlook — {results['company_name']} ({results['ticker']}) — {results['horizon']}")
    grand_tabs = st.tabs(["Technical Summary", "Plain-English Summary"])
    with grand_tabs[0]:
        st.markdown(results.get("llm_technical_summary", "No technical summary available."))
    with grand_tabs[1]:
        st.markdown(results.get("llm_plain_summary", "No plain-English summary available."))

    st.markdown(f"**Composite Risk Score:** {results['composite_risk_score']}")
    st.markdown(f"**Risk Level:** {results['risk_level']}")

    st.divider()

    # --- Agent Tabs (Stock, Sector, Market, Commodity, Global) ---
    AGENT_KEYS = [
        ("Stock", "stock"),
        ("Sector", "sector"),
        ("Market", "market"),
        ("Commodity", "commodity"),
        ("Global", "global"),
    ]
    tab_labels = [x[0] for x in AGENT_KEYS]
    agent_tabs = st.tabs(tab_labels)

    for i, (label, key) in enumerate(AGENT_KEYS):
        agent_data = results.get(key, {})

        with agent_tabs[i]:
            st.markdown(f"## {label} Agent")

            # --- Chart Section ---
            chart = agent_data.get("chart")
            if chart is not None:
                st.plotly_chart(chart, use_container_width=True, key=f"{label}_chart")
            elif key == "stock" and results['stock'].get("chart"):
                st.plotly_chart(results['stock']["chart"], use_container_width=True, key=f"{label}_chart")
            else:
                st.info("No chart available for this agent.")

            # --- Summary Section (Tabbed: Technical / Plain-English) ---
            st.markdown("### AI Summary")
            summary_tabs = st.tabs(["Technical", "Plain-English"])
            with summary_tabs[0]:
                tech = agent_data.get("llm_technical_summary", "")
                if not tech or "llm error" in tech.lower():
                    st.warning("Technical summary could not be generated due to an LLM error.")
                else:
                    st.markdown(tech)
            with summary_tabs[1]:
                plain = agent_data.get("llm_plain_summary", "")
                if not plain or "llm error" in plain.lower():
                    st.warning("Plain-English summary could not be generated due to an LLM error.")
                else:
                    st.markdown(plain)

            # --- Risk Level ---
            st.markdown(f"**Risk Level:** {agent_data.get('risk_level', 'N/A')}")

            # --- Expandable: Show technical details/raw data ---
            with st.expander("Show technical details / raw data"):
                st.write(agent_data)
                df = agent_data.get("df")
                if isinstance(df, pd.DataFrame):
                    st.dataframe(df)

            # --- Download Agent Report ---
            download_text = f"""# {label} Agent AI Report

## Technical Summary
{agent_data.get('llm_technical_summary', '')}

## Plain-English Summary
{agent_data.get('llm_plain_summary', '')}
"""
            st.download_button(
                label="Download Agent Report",
                data=download_text,
                file_name=f"{ticker}_{label}_report.md"
            )

else:
    st.info("Enter a SGX ticker (e.g., D05.SI, U11.SI, A17U.SI) and click **Run AI Analysis** to start.")




