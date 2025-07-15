import streamlit as st
import plotly.graph_objs as go
import sys
import os

# --- Adjust import paths for agent module ---
AGENT_DIR = os.path.join(os.path.dirname(__file__), 'agents')
if AGENT_DIR not in sys.path:
    sys.path.append(AGENT_DIR)

from agents.ta_global import ta_global  # <-- adjust if needed
from llm_utils import call_llm  # assuming llm_utils.py is in project root

st.set_page_config(
    page_title="AI Global Technical Macro Analyst",
    layout="wide"
)

st.title("Raw Global Technical Data")

# --- Run global agent to get data and summaries ---
with st.spinner("Running global agent..."):
    global_result = ta_global()

# Display dropdown for raw dict if you want to inspect/debug
if st.button("Show raw summary dict"):
    st.write(global_result)

# === Plot S&P 500 Closing Prices ===
sp500_df = global_result.get("data", {}).get("sp500")
if sp500_df is not None and not sp500_df.empty:
    # If not already, make sure Date is index or column
    if "Date" in sp500_df.columns:
        sp500_df = sp500_df.set_index("Date")
    # Use only the last 90 rows
    sp500_df = sp500_df.sort_index().iloc[-90:]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=sp500_df.index, y=sp500_df['Close'],
        mode='lines', name='S&P 500'
    ))
    fig.update_layout(
        title='S&P 500 Closing Prices - Last 90 Days',
        xaxis_title='Date',
        yaxis_title='Close',
        height=400
    )
    st.subheader("S&P 500 Chart")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No S&P 500 data found from agent.")

# === LLM Summaries ===
st.markdown("## LLM-Generated Summaries")

# --- Technical Summary ---
llm_tech = global_result.get("llm_technical_summary")
if llm_tech and not llm_tech.startswith("LLM error"):
    st.markdown("**Technical Summary**")
    st.info(llm_tech)
else:
    st.warning("Technical summary could not be generated due to an LLM error.")

# --- Plain-English Summary ---
llm_plain = global_result.get("llm_plain_summary")
if llm_plain and not llm_plain.startswith("LLM error"):
    st.markdown("**Plain-English Summary**")
    st.success(llm_plain)
else:
    st.warning("Plain-English summary could not be generated due to an LLM error.")

# Optional: Add a button to force regenerate LLM summaries
if st.button("Generate LLM Global Summaries"):
    # Example: Re-run LLM summarization on current data (pseudocode)
    global_result = ta_global()  # or you could just rerun LLM portion if agent supports
    st.experimental_rerun()



