import streamlit as st
import json
import plotly.graph_objs as go
import pandas as pd
from ta_global import ta_global
from llm_utils import call_llm

st.set_page_config(page_title="AI Global Technical Macro Analyst", page_icon="🌍")

st.title("🌍 AI Global Macro Technical Analyst Demo")
st.markdown(
    """
    This demo fetches global market data, computes technical metrics, and asks the LLM to summarize the global technical outlook
    in both a professional (analyst) and plain-English (executive) format.
    """
)

# --- Get latest global technical summary
with st.spinner("Loading global technical summary..."):
    try:
        summary = ta_global()
        st.success("Fetched and computed global technical metrics.")
    except Exception as e:
        st.error(f"Error in ta_global(): {e}")
        st.stop()

# === [NEW] S&P 500 Chart Section ===
sp500_df = None
# Try common keys for S&P 500 data in summary
for key in ['sp500', 's&p500', 'S&P500', 'S&P_500']:
    if key in summary.get('data', {}):
        sp500_df = summary['data'][key]
        break

if isinstance(sp500_df, pd.DataFrame) and not sp500_df.empty:
    if "Date" in sp500_df.columns:
        sp500_df = sp500_df.set_index("Date")
    sp500_df = sp500_df.sort_index().iloc[-90:]  # Show last 90 rows
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
else:
    st.info("S&P 500 chart not available in current summary.")

# === END Chart Section ===

st.subheader("Raw Global Technical Data")
with st.expander("Show raw summary dict", expanded=False):
    st.json(summary)

# --- Prepare prompt for LLM
json_summary = json.dumps(summary, indent=2)

# --- Run LLM agent for summary (global)
st.subheader("LLM-Generated Summaries")
if st.button("Generate LLM Global Summaries", type="primary"):
    with st.spinner("Querying LLM..."):
        try:
            llm_output = call_llm("global", json_summary)
            # Expecting: "Technical Summary\n...\nPlain-English Summary\n..."
            if "Technical Summary" in llm_output and "Plain-English Summary" in llm_output:
                tech = llm_output.split("Plain-English Summary")[0].replace("Technical Summary", "").strip()
                plain = llm_output.split("Plain-English Summary")[1].strip()
                st.markdown("**Technical Summary**")
                st.info(tech)
                st.markdown("**Plain-English Summary**")
                st.success(plain)
            else:
                st.warning("LLM output did not match expected template. Full output below:")
                st.code(llm_output)
        except Exception as e:
            st.error(f"LLM error: {e}")

st.caption("If you do not see the summaries, check the console logs for LLM errors or ensure your OpenAI API key is correctly set.")


