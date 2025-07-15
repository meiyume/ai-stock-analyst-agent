import streamlit as st
import json
import plotly.graph_objects as go
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
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

# ----------- CHART SECTION ----------- #
def plot_yfinance_chart(ticker, title):
    with st.container():
        with st.spinner(f"Loading {title} historical data..."):
            try:
                end = datetime.today()
                start = end - timedelta(days=180)
                data = yf.download(ticker, start=start, end=end, interval="1d", auto_adjust=True, progress=False)

                # Flatten MultiIndex if needed
                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = ['_'.join([str(i) for i in col if i]) for col in data.columns.values]
                data = data.reset_index()

                # Identify Date and Close columns
                date_col = None
                close_col = None
                for col in data.columns:
                    # Date column detection
                    if isinstance(col, str) and col.lower() in ["date", "datetime", "index"]:
                        date_col = col
                    # Close price detection (may be "Close" or e.g., "Close_^GSPC")
                    if isinstance(col, str) and "close" in col.lower():
                        close_col = col

                if not date_col or not close_col:
                    st.info(f"{title} chart failed to load: {list(data.columns)}")
                else:
                    data = data.dropna(subset=[date_col, close_col])
                    if len(data) < 5:
                        st.info(f"Not enough {title} data to plot.")
                    else:
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=data[date_col],
                            y=data[close_col],
                            mode='lines',
                            name=title
                        ))
                        fig.update_layout(
                            title=f"{title} (Last 6 Months)",
                            xaxis_title="Date",
                            yaxis_title="Price" if "vix" not in title.lower() else "VIX Level",
                            template="plotly_white",
                            height=350
                        )
                        st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.info(f"{title} chart failed to load: {e}")

# ----------- DISPLAY CHARTS ----------- #
plot_yfinance_chart("^GSPC", "S&P 500 Index")
plot_yfinance_chart("^VIX", "VIX (Volatility Index)")
plot_yfinance_chart("^IXIC", "Nasdaq Index")

# ------------- RAW DATA ------------- #
st.subheader("Raw Global Technical Data")
with st.expander("Show raw summary dict", expanded=False):
    st.json(summary)

# ------------- LLM SUMMARIES ------------- #
st.subheader("LLM-Generated Summaries")
if st.button("Generate LLM Global Summaries", type="primary"):
    with st.spinner("Querying LLM..."):
        try:
            json_summary = json.dumps(summary, indent=2)
            llm_output = call_llm("global", json_summary)
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




