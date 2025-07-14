import streamlit as st
import plotly.graph_objects as go

from agents.agent1_core import run_full_technical_analysis
import agents.agent1_stock as agent1_stock
import agents.agent1_sector as agent1_sector
import agents.agent1_market as agent1_market
import agents.agent1_commodities as agent1_commodities
import agents.agent1_globals as agent1_globals

st.set_page_config(page_title="AI Stock Analyst", page_icon="📊", layout="wide")

# --- Sidebar Inputs ---
st.sidebar.title("Stock Selection")
ticker = st.sidebar.text_input("Ticker", value="A17U.SI")
horizon = st.sidebar.selectbox("Forecast Horizon", ["1 Day", "3 Days", "7 Days", "30 Days"])
lookback_days = st.sidebar.number_input("Lookback Days (optional override)", min_value=7, max_value=365, value=60)
openai_api_key = st.secrets.get("OPENAI_API_KEY", None)
st.sidebar.markdown("---")
st.sidebar.caption("Built by AI | [About](#)")

# --- Fetch Company Name Utility ---
def get_company_name_from_ticker(ticker):
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info
        return info.get("longName", ticker)
    except Exception:
        return ticker

company_name = get_company_name_from_ticker(ticker)

# --- Chief Analyst Grand Outlook (using agent1_core) ---
with st.spinner("Chief Analyst is analyzing overall outlook..."):
    try:
        chief_result = run_full_technical_analysis(
            ticker,
            company_name=company_name,
            horizon=horizon,
            lookback_days=lookback_days,
            api_key=openai_api_key
        )
        chief_outlook = chief_result.get("llm_summary", "No summary.")
        composite_risk_score = chief_result.get("composite_risk_score", 50)
        composite_risk_level = chief_result.get("risk_level", "Moderate")
    except Exception as e:
        chief_outlook = f"(Error: {e})"
        composite_risk_score = 50
        composite_risk_level = "Moderate"

# --- Agent Analyzer Calls ---
AGENT_CONFIG = [
    ("Stock", agent1_stock),
    ("Sector", agent1_sector),
    ("Market", agent1_market),
    ("Commodities", agent1_commodities),
    ("Globals", agent1_globals),
]

agent_reports = {}
for agent_name, agent_module in AGENT_CONFIG:
    with st.spinner(f"Analyzing with {agent_name} agent..."):
        try:
            res = agent_module.analyze(
                ticker,
                company_name=company_name,
                horizon=horizon,
                lookback_days=lookback_days,
                api_key=openai_api_key
            )
            agent_reports[agent_name] = {
                "summary": res.get("llm_summary", "No summary."),
                "risk": res.get("risk_level", "N/A"),
                "plot": res.get("chart", go.Figure()),
                "raw": res
            }
        except Exception as e:
            agent_reports[agent_name] = {
                "summary": f"(Agent failed: {e})",
                "risk": "N/A",
                "plot": go.Figure(),
                "raw": {}
            }

# --- Header Section ---
st.markdown(f"# {company_name} ({ticker.upper()})")
st.markdown(f"### Forecast Horizon: **{horizon}**")

# --- Chief Analyst Grand Outlook (Top Section) ---
with st.container():
    st.markdown("## 🦾 Chief Analyst Grand Outlook")
    st.markdown(f"**Summary:** {chief_outlook}")
    st.metric("Composite Risk Score", f"{composite_risk_score}/100")
    st.progress(composite_risk_score)
    emoji = (
        "🔴" if composite_risk_level.lower() == "high"
        else "🟠" if composite_risk_level.lower() == "moderate"
        else "🟢"
    )
    st.markdown(f"**Risk Level:** {emoji} {composite_risk_level}")

st.divider()

# --- Agent Tabs ---
tab_names = list(agent_reports.keys())
tabs = st.tabs(tab_names)
for i, agent in enumerate(tab_names):
    with tabs[i]:
        st.markdown(f"### {agent} Analyst Report")
        st.plotly_chart(agent_reports[agent]["plot"], use_container_width=True)
        st.markdown(f"**AI Summary:** {agent_reports[agent]['summary']}")
        st.markdown(f"**Risk Level:** {agent_reports[agent]['risk']}")
        with st.expander("Show technical details / raw data"):
            st.write(agent_reports[agent]["raw"])
        st.download_button(
            "Download Agent Report",
            agent_reports[agent]["summary"],
            file_name=f"{ticker}_{agent}_report.md"
        )

# --- Footer ---
st.markdown("---")
st.caption("For educational use only. AI Multi-Agent Analyst © 2025 | v1.0")






