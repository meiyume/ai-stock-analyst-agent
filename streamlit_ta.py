import streamlit as st
import json
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from agents.ta_global import ta_global
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

# ---- S&P 500 Chart Robust Block ----
with st.container():
    with st.spinner("Loading S&P 500 historical data..."):
        try:
            end = datetime.today()
            start = end - timedelta(days=180)
            sp500_hist = yf.download("^GSPC", start=start, end=end, interval="1d", auto_adjust=True, progress=False)
            if sp500_hist.empty or "Close" not in sp500_hist.columns:
                st.info("S&P 500 data unavailable or missing 'Close' column.")
            else:
                # Try to find the date column after reset_index()
                sp500_hist = sp500_hist.reset_index()
                date_col = None
                for col in sp500_hist.columns:
                    if col.lower() in ["date", "datetime", "index"]:
                        date_col = col
                        break
                if date_col is None:
                    st.info("No date-like column found in S&P 500 data.")
                else:
                    # Drop rows with NaN in date/close
                    sp500_hist = sp500_hist.dropna(subset=[date_col, "Close"])
                    if sp500_hist.shape[0] < 5:
                        st.info("Not enough data to plot S&P 500 chart.")
                    else:
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=sp500_hist[date_col],
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
        except Exception as e:
            st.info(f"S&P 500 chart failed to load: {e}")


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



