import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import plotly.graph_objects as go
from ta_global import ta_global
from llm_utils import call_llm

st.set_page_config(page_title="AI Global Technical Macro Analyst", page_icon="🌍")

st.title("🌍 AI Global Macro Technical Analyst Demo")
st.markdown(
    """
    This demo fetches global market data, computes technical metrics (multi-horizon), and asks the LLM to summarize
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

st.subheader("Raw Global Technical Data")
with st.expander("Show raw summary dict", expanded=False):
    st.json(summary)

# ----------- CHART GENERATION FUNCTION -----------
def plot_chart(ticker, label, summary_key):
    with st.container():
        with st.spinner(f"Loading {label} historical data..."):
            try:
                end = datetime.today()
                start = end - timedelta(days=250)
                df = yf.download(ticker, start=start, end=end, interval="1d", auto_adjust=True, progress=False)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = ['_'.join([str(i) for i in col if i]) for i, col in enumerate(df.columns.values)]
                df = df.reset_index()
                date_col, close_col = None, None
                for col in df.columns:
                    if isinstance(col, str) and col.lower() in ["date", "datetime", "index"]:
                        date_col = col
                    if isinstance(col, str) and "close" in col.lower():
                        close_col = col
                if not date_col or not close_col:
                    st.info(f"{label} chart failed to load: columns found: {list(df.columns)}")
                else:
                    df = df.dropna(subset=[date_col, close_col])
                    if len(df) < 30:
                        st.info(f"Not enough {label} data to plot.")
                    else:
                        # Compute 30/90/200d SMA
                        df['SMA_30'] = df[close_col].rolling(30).mean()
                        df['SMA_90'] = df[close_col].rolling(90).mean()
                        df['SMA_200'] = df[close_col].rolling(200).mean()
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=df[date_col], y=df[close_col],
                            mode='lines', name=label, line=dict(width=2)
                        ))
                        fig.add_trace(go.Scatter(
                            x=df[date_col], y=df['SMA_30'],
                            mode='lines', name='SMA 30d'
                        ))
                        fig.add_trace(go.Scatter(
                            x=df[date_col], y=df['SMA_90'],
                            mode='lines', name='SMA 90d'
                        ))
                        fig.add_trace(go.Scatter(
                            x=df[date_col], y=df['SMA_200'],
                            mode='lines', name='SMA 200d'
                        ))
                        fig.update_layout(
                            title=f"{label} (Price + 30/90/200d SMA)",
                            xaxis_title="Date", yaxis_title="Price",
                            template="plotly_white", height=350
                        )
                        st.markdown(f"**{label} (Last 6 Months)**")
                        st.plotly_chart(fig, use_container_width=True)

                        # --- Show window stats table from summary
                        stats_data = summary.get(summary_key, {})
                        stats = []
                        for window in [30, 90, 200]:
                            pct = stats_data.get(f'change_{window}d_pct', float('nan'))
                            vol = stats_data.get(f'vol_{window}d', float('nan'))
                            trend = stats_data.get(f'trend_{window}d', "-")
                            stats.append({
                                "Window": f"{window}d",
                                "% Change": f"{pct:.2f}%" if pct == pct else "-",
                                "Volatility": f"{vol:.2%}" if vol == vol else "-",
                                "Trend": trend
                            })
                        df_stats = pd.DataFrame(stats)
                        st.dataframe(df_stats, use_container_width=True, hide_index=True)
            except Exception as e:
                st.info(f"{label} chart failed to load: {e}")

# ----------- S&P 500 CHART -----------
st.subheader("S&P 500 Index (Multi-Window Analysis)")
plot_chart("^GSPC", "S&P 500", "s&p500")

# ----------- VIX CHART -----------
st.subheader("VIX (Volatility Index)")
plot_chart("^VIX", "VIX", "vix")

# ----------- DXY CHART -----------
st.subheader("US Dollar Index (DXY)")
plot_chart("DX-Y.NYB", "US Dollar Index", "dxy")

# ----------- LLM Summaries -----------
st.subheader("LLM-Generated Summaries")
if st.button("Generate LLM Global Summaries", type="primary"):
    import json
    json_summary = json.dumps(summary, indent=2)
    with st.spinner("Querying LLM..."):
        try:
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





