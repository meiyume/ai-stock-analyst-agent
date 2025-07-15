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

# ----------- S&P500 Chart with 3 SMAs + Window Stats -----------
st.subheader("S&P 500 Index (Multi-Window Analysis)")

with st.container():
    with st.spinner("Loading S&P 500 historical data..."):
        try:
            end = datetime.today()
            start = end - timedelta(days=250)  # 250 trading days ~ 1 year
            sp500_hist = yf.download("^GSPC", start=start, end=end, interval="1d", auto_adjust=True, progress=False)
            if isinstance(sp500_hist.columns, pd.MultiIndex):
                sp500_hist.columns = ['_'.join([str(i) for i in col if i]) for i, col in enumerate(sp500_hist.columns.values)]
            sp500_hist = sp500_hist.reset_index()
            date_col, close_col = None, None
            for col in sp500_hist.columns:
                if isinstance(col, str) and col.lower() in ["date", "datetime", "index"]:
                    date_col = col
                if isinstance(col, str) and "close" in col.lower():
                    close_col = col

            if not date_col or not close_col:
                st.info(f"S&P 500 chart failed to load: columns found: {list(sp500_hist.columns)}")
            else:
                # Drop NaNs
                sp500_hist = sp500_hist.dropna(subset=[date_col, close_col])
                if len(sp500_hist) < 30:
                    st.info("Not enough S&P 500 data to plot.")
                else:
                    # Compute 30/90/200d SMA
                    sp500_hist['SMA_30'] = sp500_hist[close_col].rolling(30).mean()
                    sp500_hist['SMA_90'] = sp500_hist[close_col].rolling(90).mean()
                    sp500_hist['SMA_200'] = sp500_hist[close_col].rolling(200).mean()

                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=sp500_hist[date_col], y=sp500_hist[close_col],
                        mode='lines', name='S&P 500', line=dict(width=2)
                    ))
                    fig.add_trace(go.Scatter(
                        x=sp500_hist[date_col], y=sp500_hist['SMA_30'],
                        mode='lines', name='SMA 30d'
                    ))
                    fig.add_trace(go.Scatter(
                        x=sp500_hist[date_col], y=sp500_hist['SMA_90'],
                        mode='lines', name='SMA 90d'
                    ))
                    fig.add_trace(go.Scatter(
                        x=sp500_hist[date_col], y=sp500_hist['SMA_200'],
                        mode='lines', name='SMA 200d'
                    ))
                    fig.update_layout(
                        title="S&P 500 Index (Price + 30/90/200d SMA)",
                        xaxis_title="Date", yaxis_title="Price",
                        template="plotly_white", height=350
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    # --- Show window stats table from summary
                    spx = summary.get('s&p500', {})
                    stats = []
                    for window in [30, 90, 200]:
                        stats.append({
                            "Window": f"{window}d",
                            "% Change": f"{spx.get(f'change_{window}d_pct', float('nan')):.2f}%" if f'change_{window}d_pct' in spx else "-",
                            "Volatility": f"{spx.get(f'vol_{window}d', float('nan')):.2%}" if f'vol_{window}d' in spx else "-",
                            "Trend": spx.get(f'trend_{window}d', "-")
                        })
                    df_stats = pd.DataFrame(stats)
                    st.dataframe(df_stats, use_container_width=True, hide_index=True)
        except Exception as e:
            st.info(f"S&P 500 chart failed to load: {e}")

# ----------- LLM Summaries -----------
st.subheader("LLM-Generated Summaries")
if st.button("Generate LLM Global Summaries", type="primary"):
    import json
    from llm_utils import call_llm
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






