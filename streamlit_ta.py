import streamlit as st
import plotly.graph_objs as go
import pandas as pd
import sys
import os

# -- Make sure agents can be imported even if script is in project root
AGENT_DIR = os.path.join(os.path.dirname(__file__), "agents")
if AGENT_DIR not in sys.path:
    sys.path.append(AGENT_DIR)

from agents.ta_global import ta_global
from llm_utils import call_llm

st.set_page_config(page_title="AI Global Technical Macro Analyst")

st.title("Raw Global Technical Data")

# -- Dropdown to show/hide raw data
show_option = st.selectbox(
    "Show",
    [
        "Show raw summary dict",
        "Show raw agent data only"
    ],
)

global_result = st.session_state.get("global_result")
if global_result is None:
    with st.spinner("Running global agent..."):
        global_result = ta_global()
        st.session_state["global_result"] = global_result

if show_option == "Show raw summary dict":
    st.write(global_result)
elif show_option == "Show raw agent data only":
    st.write(global_result.get("data"))

# -- NEW: S&P 500 Chart (under raw data, before LLM summaries) --
sp500_df = global_result.get("data", {}).get("sp500")
if isinstance(sp500_df, pd.DataFrame) and not sp500_df.empty:
    # Prefer Date as index for Plotly
    if "Date" in sp500_df.columns:
        sp500_df = sp500_df.set_index("Date")
    sp500_df = sp500_df.sort_index().iloc[-90:]  # last 90 days
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=sp500_df.index,
        y=sp500_df['Close'],
        mode='lines',
        name='S&P 500'
    ))
    fig.update_layout(
        title='S&P 500 Closing Prices (Last 90 Days)',
        xaxis_title='Date',
        yaxis_title='Close',
        height=400
    )
    st.markdown("#### S&P 500 Chart")
    st.plotly_chart(fig, use_container_width=True)

# -- LLM Summaries Section --
st.markdown("## LLM-Generated Summaries")
if st.button("Generate LLM Global Summaries", type="primary"):
    with st.spinner("Generating summaries with LLM..."):
        # Optionally you could force rerun the agent or just the LLM summarization part
        global_result = ta_global()
        st.session_state["global_result"] = global_result
        st.experimental_rerun()

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

# Optional note
st.caption(
    "If you do not see the summaries, check the console logs for LLM errors or ensure your OpenAI API key is correctly set."
)




