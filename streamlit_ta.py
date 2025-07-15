import streamlit as st
import json
from agents.ta_global import ta_global      # Adjusted path
from llm_utils import call_llm
import yfinance as yf
import plotly.graph_objects as go

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

# ==== 1. S&P 500 Chart (added here, below green box) ====
with st.spinner("Loading S&P 500 historical data..."):
    try:
        sp500_hist = yf.download("^GSPC", period="6mo", interval="1d", auto_adjust=True, progress=False)
        if not sp500_hist.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=sp500_hist.index,
                y=sp500_hist["Close"],
                mode='lines',
                name='S&P 500'
            ))
            fig.update_layout(
                title="S&P 500 Index (Last 6 Months)",
                xaxis_title="Date",
                yaxis_title="Price",
                template="plotly_white",
                height=350
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("S&P 500 chart not available in current summary.")
    except Exception as e:
        st.info(f"S&P 500 chart failed to load: {e}")

# --- Raw summary dict
st.subheader("Raw Global Technical Data")
with st.expander("Show raw summary dict", expanded=False):
    st.json(summary)

# --- Prepare prompt for LLM
json_summary = json.dumps(summary, indent=2)

# --- LLM Summaries (your original UI below)
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


