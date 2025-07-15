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

# ---- S&P500 Chart ----
spx_hist = summary.get('s&p500_hist')
if spx_hist is not None and len(spx_hist) > 0:
    import pandas as pd
    df = pd.DataFrame(spx_hist)
    # Handle column name cases and index issues
    for c in df.columns:
        if isinstance(c, tuple):
            # MultiIndex, collapse
            df[c[0]] = df[c]
    if "Date" not in df.columns:
        df["Date"] = df.index
    df = df.dropna(subset=["Close"])
    st.markdown("**S&P 500 Index (Last 6 Months)**")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pd.to_datetime(df["Date"]), y=df["Close"],
        mode='lines', name='S&P 500'
    ))
    fig.update_layout(height=300, xaxis_title="Date", yaxis_title="Price")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("S&P 500 chart not available in current summary.")

# ---- VIX Chart ----
vix_hist = summary.get('vix_hist')
if vix_hist is not None and len(vix_hist) > 0:
    df = pd.DataFrame(vix_hist)
    for c in df.columns:
        if isinstance(c, tuple):
            df[c[0]] = df[c]
    if "Date" not in df.columns:
        df["Date"] = df.index
    df = df.dropna(subset=["Close"])
    st.markdown("**VIX (Volatility Index) (Last 6 Months)**")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pd.to_datetime(df["Date"]), y=df["Close"],
        mode='lines', name='VIX'
    ))
    fig.update_layout(height=300, xaxis_title="Date", yaxis_title="VIX Level")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("VIX chart not available in current summary.")

# ---- Nasdaq Chart ----
nasdaq_hist = summary.get('nasdaq_hist')
if nasdaq_hist is not None and len(nasdaq_hist) > 0:
    df = pd.DataFrame(nasdaq_hist)
    for c in df.columns:
        if isinstance(c, tuple):
            df[c[0]] = df[c]
    if "Date" not in df.columns:
        df["Date"] = df.index
    df = df.dropna(subset=["Close"])
    st.markdown("**Nasdaq Index (Last 6 Months)**")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pd.to_datetime(df["Date"]), y=df["Close"],
        mode='lines', name='Nasdaq'
    ))
    fig.update_layout(height=300, xaxis_title="Date", yaxis_title="Price")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Nasdaq chart not available in current summary.")


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



